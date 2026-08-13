package com.continuecontinue.anvilshell

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import org.json.JSONArray
import java.util.UUID

enum class JobState {
    QUEUED,
    CLAIMED,
    RUNNING,
    DISPATCHED,
    RECOVERABLE,
    CHECKPOINTED,
    SUCCEEDED,
    FAILED,
    BLOCKED,
    CANCELLED
}

internal val AUTO_CLAIMABLE_STATES = setOf(JobState.QUEUED)

data class StoredJob(
    val jobId: String,
    val requestHash: String,
    val request: CommandRequest,
    val state: JobState,
    val createdAt: Long
)

class JobStore(context: Context) : SQLiteOpenHelper(
    context.createDeviceProtectedStorageContext(),
    "anvil-shell.db",
    null,
    1
) {
    override fun onConfigure(db: SQLiteDatabase) {
        db.enableWriteAheadLogging()
        db.setForeignKeyConstraintsEnabled(true)
    }

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(
            """CREATE TABLE jobs (
                job_id TEXT PRIMARY KEY,
                idempotency_key TEXT NOT NULL UNIQUE,
                request_hash TEXT NOT NULL,
                command_id TEXT NOT NULL,
                verb TEXT NOT NULL,
                args_json TEXT NOT NULL,
                anvil TEXT NOT NULL,
                owner TEXT NOT NULL,
                team TEXT,
                cwd TEXT,
                state TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                terminal_detail TEXT
            )""".trimIndent()
        )
        db.execSQL(
            """CREATE TABLE events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                state TEXT NOT NULL,
                detail TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(job_id)
            )""".trimIndent()
        )
        db.execSQL("CREATE INDEX jobs_state_created ON jobs(state, created_at)")
        db.execSQL("CREATE INDEX events_job_created ON events(job_id, created_at)")
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        error("No destructive database migration is permitted")
    }

    fun enqueue(request: CommandRequest): String {
        CommandRegistry.resolve(request)
        val hash = request.sha256()
        writableDatabase.beginTransaction()
        try {
            readableDatabase.query(
                "jobs",
                arrayOf("job_id", "request_hash"),
                "idempotency_key = ?",
                arrayOf(request.idempotencyKey),
                null,
                null,
                null
            ).use { cursor ->
                if (cursor.moveToFirst()) {
                    require(cursor.getString(1) == hash) {
                        "idempotency key already belongs to a different request"
                    }
                    writableDatabase.setTransactionSuccessful()
                    return cursor.getString(0)
                }
            }

            val now = System.currentTimeMillis()
            val jobId = UUID.randomUUID().toString()
            val values = ContentValues().apply {
                put("job_id", jobId)
                put("idempotency_key", request.idempotencyKey)
                put("request_hash", hash)
                put("command_id", request.commandId)
                put("verb", request.verb)
                put("args_json", JSONArray(request.args).toString())
                put("anvil", request.anvil)
                put("owner", request.owner)
                put("team", request.team)
                put("cwd", request.cwd)
                put("state", JobState.QUEUED.name)
                put("created_at", now)
                put("updated_at", now)
            }
            check(writableDatabase.insertOrThrow("jobs", null, values) > 0)
            appendEventLocked(jobId, JobState.QUEUED, "requestHash=$hash", now)
            writableDatabase.setTransactionSuccessful()
            return jobId
        } finally {
            writableDatabase.endTransaction()
        }
    }

    fun claimNext(): StoredJob? {
        // RECOVERABLE is intentionally excluded. A dispatched external command may
        // already have side effects, so only an explicit reconciliation operation
        // may decide whether it is safe to retry.
        val claimableNames = AUTO_CLAIMABLE_STATES.map(JobState::name)
        check(claimableNames.isNotEmpty())
        val placeholders = claimableNames.joinToString(",") { "?" }
        writableDatabase.beginTransaction()
        try {
            val job = readableDatabase.query(
                "jobs",
                null,
                "state IN ($placeholders)",
                claimableNames.toTypedArray(),
                null,
                null,
                "created_at ASC",
                "1"
            ).use { cursor -> if (cursor.moveToFirst()) fromCursor(cursor) else null }
                ?: return null

            val changed = writableDatabase.update(
                "jobs",
                ContentValues().apply {
                    put("state", JobState.CLAIMED.name)
                    put("updated_at", System.currentTimeMillis())
                },
                "job_id = ? AND state IN ($placeholders)",
                arrayOf(job.jobId, *claimableNames.toTypedArray())
            )
            if (changed != 1) return null
            appendEventLocked(job.jobId, JobState.CLAIMED, "claimed by :engine")
            writableDatabase.setTransactionSuccessful()
            return job.copy(state = JobState.CLAIMED)
        } finally {
            writableDatabase.endTransaction()
        }
    }

    fun transition(jobId: String, state: JobState, detail: String) {
        writableDatabase.beginTransaction()
        try {
            val values = ContentValues().apply {
                put("state", state.name)
                put("updated_at", System.currentTimeMillis())
                if (state in terminalStates) put("terminal_detail", detail)
            }
            check(writableDatabase.update("jobs", values, "job_id = ?", arrayOf(jobId)) == 1)
            appendEventLocked(jobId, state, detail.take(16_384))
            writableDatabase.setTransactionSuccessful()
        } finally {
            writableDatabase.endTransaction()
        }
    }

    fun recoverInterrupted(): Int {
        val now = System.currentTimeMillis()
        writableDatabase.beginTransaction()
        try {
            val count = writableDatabase.update(
                "jobs",
                ContentValues().apply {
                    put("state", JobState.RECOVERABLE.name)
                    put("updated_at", now)
                },
                "state IN (?, ?, ?)",
                arrayOf(JobState.CLAIMED.name, JobState.RUNNING.name, JobState.DISPATCHED.name)
            )
            if (count > 0) {
                writableDatabase.execSQL(
                    """INSERT INTO events(job_id, state, detail, created_at)
                       SELECT job_id, ?, 'engine restarted; prior execution requires reconciliation', ?
                       FROM jobs WHERE state = ? AND updated_at = ?""",
                    arrayOf(JobState.RECOVERABLE.name, now, JobState.RECOVERABLE.name, now)
                )
            }
            writableDatabase.setTransactionSuccessful()
            return count
        } finally {
            writableDatabase.endTransaction()
        }
    }

    fun latestSummary(): String {
        return readableDatabase.query(
            "jobs",
            arrayOf("anvil", "owner", "team", "verb", "state", "updated_at"),
            null,
            null,
            null,
            null,
            "updated_at DESC",
            "1"
        ).use { cursor ->
            if (!cursor.moveToFirst()) return@use "[shell][drew][-][IDLE] no jobs"
            val team = cursor.getString(2) ?: "-"
            "[${cursor.getString(0)}][${cursor.getString(1)}][$team][${cursor.getString(4)}] ${cursor.getString(3)}"
        }
    }

    private fun appendEventLocked(
        jobId: String,
        state: JobState,
        detail: String,
        now: Long = System.currentTimeMillis()
    ) {
        writableDatabase.insertOrThrow(
            "events",
            null,
            ContentValues().apply {
                put("job_id", jobId)
                put("state", state.name)
                put("detail", detail)
                put("created_at", now)
            }
        )
    }

    private fun fromCursor(cursor: android.database.Cursor): StoredJob {
        fun text(name: String): String = cursor.getString(cursor.getColumnIndexOrThrow(name))
        fun nullable(name: String): String? {
            val index = cursor.getColumnIndexOrThrow(name)
            return if (cursor.isNull(index)) null else cursor.getString(index)
        }
        val argsJson = JSONArray(text("args_json"))
        val args = buildList { for (index in 0 until argsJson.length()) add(argsJson.getString(index)) }
        val request = CommandRequest(
            commandId = text("command_id"),
            idempotencyKey = text("idempotency_key"),
            verb = text("verb"),
            args = args,
            anvil = text("anvil"),
            owner = text("owner"),
            team = nullable("team"),
            cwd = nullable("cwd")
        )
        return StoredJob(
            jobId = text("job_id"),
            requestHash = text("request_hash"),
            request = request,
            state = JobState.valueOf(text("state")),
            createdAt = cursor.getLong(cursor.getColumnIndexOrThrow("created_at"))
        )
    }

    companion object {
        private val terminalStates = setOf(
            JobState.SUCCEEDED,
            JobState.FAILED,
            JobState.BLOCKED,
            JobState.CANCELLED
        )
    }
}
