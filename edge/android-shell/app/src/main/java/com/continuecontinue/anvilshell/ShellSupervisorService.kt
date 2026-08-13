package com.continuecontinue.anvilshell

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.IBinder
import java.util.UUID
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

class ShellSupervisorService : Service() {
    private val executor = Executors.newSingleThreadExecutor()
    private val draining = AtomicBoolean(false)
    private lateinit var store: JobStore

    override fun onCreate() {
        super.onCreate()
        store = JobStore(this)
        store.recoverInterrupted()
        ensureChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(NOTIFICATION_ID, notification("Anvil Shell is reconciling durable work"))
        if (intent?.action == ACTION_ENQUEUE_SELF_CHECK) {
            val token = intent.getStringExtra(EXTRA_TOKEN) ?: UUID.randomUUID().toString()
            store.enqueue(
                CommandRequest(
                    commandId = "self-check-$token",
                    idempotencyKey = "self-check-$token",
                    verb = "status",
                    anvil = intent.getStringExtra(EXTRA_ANVIL) ?: "shell",
                    owner = "drew",
                    team = "adam"
                )
            )
        }
        drain()
        return START_REDELIVER_INTENT
    }

    override fun onDestroy() {
        executor.shutdown()
        store.close()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun drain() {
        if (!draining.compareAndSet(false, true)) return
        executor.execute {
            try {
                while (true) {
                    val job = store.claimNext() ?: break
                    execute(job)
                }
            } finally {
                draining.set(false)
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
            }
        }
    }

    private fun execute(job: StoredJob) {
        val spec = try {
            CommandRegistry.resolve(job.request)
        } catch (error: Exception) {
            store.transition(job.jobId, JobState.BLOCKED, error.message ?: "invalid command")
            return
        }
        store.transition(job.jobId, JobState.RUNNING, "route=${spec.route};plane=${spec.plane}")
        when (spec.route) {
            CommandRoute.NATIVE -> executeNative(job)
            CommandRoute.TERMUX_COMPAT -> {
                // Persist ownership before crossing the process boundary. A fast
                // PendingIntent callback may otherwise be overwritten by a late
                // DISPATCHED write from this process.
                store.transition(
                    job.jobId,
                    JobState.DISPATCHED,
                    "prepared Termux compatibility dispatch; terminal result pending"
                )
                val outcome = TermuxCompatibilityAdapter(this).dispatch(job, spec)
                if (outcome.state != JobState.DISPATCHED) {
                    store.transition(job.jobId, outcome.state, outcome.detail)
                }
            }
            CommandRoute.HOME_CENTER -> store.transition(
                job.jobId,
                JobState.BLOCKED,
                "Home Center adapter is required for ${job.request.verb}; queued source is preserved"
            )
            CommandRoute.LOCAL_MODEL -> store.transition(
                job.jobId,
                JobState.BLOCKED,
                "No pinned local model body has passed phone economics and policy verification"
            )
        }
    }

    private fun executeNative(job: StoredJob) {
        val receipt = when (job.request.verb) {
            "status", "doctor" ->
                """{"schema":"anvil.shell.receipt.v1","jobId":"${job.jobId}","state":"SUCCEEDED","modelUsed":false,"engineProcess":":engine"}"""
            "session.list", "anvil.stream" ->
                """{"schema":"anvil.shell.receipt.v1","jobId":"${job.jobId}","state":"SUCCEEDED","summary":"${store.latestSummary()}"}"""
            "hf.status" ->
                """{"schema":"anvil.shell.receipt.v1","jobId":"${job.jobId}","state":"SUCCEEDED","policy":"pinned-revision+allowlist+sha256","installedAssets":0}"""
            else -> {
                store.transition(job.jobId, JobState.BLOCKED, "native verb is registered but not implemented in checkpoint 1")
                return
            }
        }
        store.transition(job.jobId, JobState.SUCCEEDED, receipt)
    }

    private fun ensureChannel() {
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL_ID, "Anvil Shell work", NotificationManager.IMPORTANCE_LOW)
        )
    }

    private fun notification(text: String): Notification =
        Notification.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .setContentTitle("[shell][drew][adam] Anvil Shell")
            .setContentText(text)
            .setOngoing(true)
            .build()

    companion object {
        const val ACTION_ENQUEUE_SELF_CHECK = "com.continuecontinue.anvilshell.ENQUEUE_SELF_CHECK"
        const val EXTRA_ANVIL = "anvil"
        const val EXTRA_TOKEN = "token"
        private const val CHANNEL_ID = "anvil-shell-work"
        private const val NOTIFICATION_ID = 7101
    }
}
