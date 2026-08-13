package com.continuecontinue.anvilshell

import android.app.PendingIntent
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build

data class DispatchOutcome(val state: JobState, val detail: String)

class TermuxCompatibilityAdapter(private val context: Context) {
    fun isAvailable(): Boolean = try {
        context.packageManager.getPackageInfo(TERMUX_PACKAGE, 0)
        true
    } catch (_: Exception) {
        false
    }

    fun dispatch(job: StoredJob, spec: CommandSpec): DispatchOutcome {
        if (!isAvailable()) {
            return DispatchOutcome(JobState.BLOCKED, "Termux compatibility body is not installed")
        }
        val path = requireNotNull(spec.executable) { "compat command missing executable" }
        val args = when (job.request.verb) {
            "adam.doctor" -> arrayOf("doctor")
            "adam.status" -> arrayOf("status")
            "adam.quote" -> arrayOf("quote", *job.request.args.toTypedArray())
            "vlad.notes.status" -> arrayOf("status")
            "vlad.notes.compile" -> arrayOf("compile", *job.request.args.toTypedArray())
            "vlad.notes.query" -> arrayOf("query", *job.request.args.toTypedArray())
            "vlad.notes.next" -> arrayOf("next", *job.request.args.toTypedArray())
            "vlad.notes.receipt" -> arrayOf("receipt", *job.request.args.toTypedArray())
            "shell.exec" -> arrayOf("-lc", job.request.args.single())
            else -> return DispatchOutcome(JobState.BLOCKED, "unsupported compatibility verb")
        }
        val intent = Intent(ACTION_RUN_COMMAND).apply {
            component = ComponentName(TERMUX_PACKAGE, RUN_COMMAND_SERVICE)
            putExtra(EXTRA_COMMAND_PATH, path)
            putExtra(EXTRA_ARGUMENTS, args)
            putExtra(EXTRA_WORKDIR, job.request.cwd ?: TERMUX_HOME)
            putExtra(EXTRA_BACKGROUND, true)
            putExtra(EXTRA_PENDING_INTENT, resultPendingIntent(job.jobId))
            putExtra(EXTRA_COMMAND_LABEL, "[${job.request.anvil}][${job.request.owner}][${job.request.team ?: "-"}] ${job.request.verb}")
            putExtra(EXTRA_COMMAND_DESCRIPTION, "Anvil Shell job ${job.jobId}; receipt remains pending.")
        }
        return try {
            context.startService(intent)
            DispatchOutcome(
                JobState.DISPATCHED,
                "dispatched to Termux compatibility body; terminal result pending"
            )
        } catch (error: SecurityException) {
            DispatchOutcome(JobState.BLOCKED, "Termux RUN_COMMAND permission or allow-external-apps is missing")
        } catch (error: Exception) {
            DispatchOutcome(JobState.FAILED, "Termux dispatch failed: ${error.javaClass.simpleName}")
        }
    }

    private fun resultPendingIntent(jobId: String): PendingIntent {
        val callback = Intent(context, TermuxResultService::class.java).apply {
            data = Uri.parse("anvil://termux-result/" + Uri.encode(jobId))
            putExtra(TermuxResultService.EXTRA_JOB_ID, jobId)
        }
        return PendingIntent.getService(
            context,
            0,
            callback,
            PendingIntent.FLAG_ONE_SHOT or
                (if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) PendingIntent.FLAG_MUTABLE else 0)
        )
    }

    companion object {
        private const val TERMUX_PACKAGE = "com.termux"
        private const val RUN_COMMAND_SERVICE = "com.termux.app.RunCommandService"
        private const val ACTION_RUN_COMMAND = "com.termux.RUN_COMMAND"
        private const val EXTRA_COMMAND_PATH = "com.termux.RUN_COMMAND_PATH"
        private const val EXTRA_ARGUMENTS = "com.termux.RUN_COMMAND_ARGUMENTS"
        private const val EXTRA_WORKDIR = "com.termux.RUN_COMMAND_WORKDIR"
        private const val EXTRA_BACKGROUND = "com.termux.RUN_COMMAND_BACKGROUND"
        private const val EXTRA_PENDING_INTENT = "com.termux.RUN_COMMAND_PENDING_INTENT"
        private const val EXTRA_COMMAND_LABEL = "com.termux.RUN_COMMAND_LABEL"
        private const val EXTRA_COMMAND_DESCRIPTION = "com.termux.RUN_COMMAND_DESCRIPTION"
        private const val TERMUX_HOME = "/data/data/com.termux/files/home"
    }
}
