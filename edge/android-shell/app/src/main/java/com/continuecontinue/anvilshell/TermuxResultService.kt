package com.continuecontinue.anvilshell

import android.app.Service
import android.content.Intent
import android.os.Bundle
import android.os.IBinder

class TermuxResultService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val jobId = intent?.getStringExtra(EXTRA_JOB_ID).orEmpty()
        JobStore(this).use { store ->
            if (jobId.isNotBlank()) {
                val result = intent?.getBundleExtra(EXTRA_PLUGIN_RESULT_BUNDLE)
                if (result == null || !result.containsKey(EXTRA_EXIT_CODE) || !result.containsKey(EXTRA_ERR)) {
                    store.resolveDispatched(
                        jobId,
                        JobState.RECOVERABLE,
                        "Termux result callback was missing the required result bundle; reconcile before retry"
                    )
                } else {
                    val stdout = result.getString(EXTRA_STDOUT).orEmpty()
                    val stderr = result.getString(EXTRA_STDERR).orEmpty()
                    val input = TermuxTerminalInput(
                        jobId = jobId,
                        stdout = stdout,
                        stderr = stderr,
                        stdoutOriginalLength = originalLength(result, EXTRA_STDOUT_ORIGINAL_LENGTH, stdout),
                        stderrOriginalLength = originalLength(result, EXTRA_STDERR_ORIGINAL_LENGTH, stderr),
                        exitCode = result.getInt(EXTRA_EXIT_CODE),
                        errCode = result.getInt(EXTRA_ERR),
                        errorMessage = result.getString(EXTRA_ERRMSG).orEmpty()
                    )
                    val outcome = try {
                        TermuxResultContract.evaluate(input)
                    } catch (error: IllegalArgumentException) {
                        TermuxTerminalOutcome(
                            JobState.RECOVERABLE,
                            "Termux result lengths were inconsistent; reconcile before retry"
                        )
                    }
                    store.resolveDispatched(jobId, outcome.state, outcome.receipt)
                }
            }
        }
        stopSelf(startId)
        return START_NOT_STICKY
    }

    private fun originalLength(bundle: Bundle, key: String, captured: String): Long {
        val value = bundle.get(key)
        val parsed = when (value) {
            is Number -> value.toLong()
            is String -> value.toLongOrNull()
            else -> null
        }
        return parsed ?: captured.length.toLong()
    }

    companion object {
        const val EXTRA_JOB_ID = "com.continuecontinue.anvilshell.TERMUX_JOB_ID"
        const val EXTRA_PLUGIN_RESULT_BUNDLE = "result"
        const val EXTRA_STDOUT = "stdout"
        const val EXTRA_STDOUT_ORIGINAL_LENGTH = "stdout_original_length"
        const val EXTRA_STDERR = "stderr"
        const val EXTRA_STDERR_ORIGINAL_LENGTH = "stderr_original_length"
        const val EXTRA_EXIT_CODE = "exitCode"
        const val EXTRA_ERR = "err"
        const val EXTRA_ERRMSG = "errmsg"
    }
}
