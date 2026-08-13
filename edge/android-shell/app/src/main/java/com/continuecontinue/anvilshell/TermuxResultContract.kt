package com.continuecontinue.anvilshell

import java.security.MessageDigest
import java.util.Locale

data class TermuxTerminalInput(
    val jobId: String,
    val stdout: String,
    val stderr: String,
    val stdoutOriginalLength: Long,
    val stderrOriginalLength: Long,
    val exitCode: Int,
    val errCode: Int,
    val errorMessage: String
)

data class TermuxTerminalOutcome(
    val state: JobState,
    val receipt: String
)

object TermuxResultContract {
    const val NO_INTERNAL_ERROR = -1
    private const val OUTPUT_TAIL_LIMIT = 8_192
    private const val ERROR_TAIL_LIMIT = 4_096

    fun evaluate(input: TermuxTerminalInput): TermuxTerminalOutcome {
        require(input.jobId.isNotBlank()) { "jobId is required" }
        require(input.stdoutOriginalLength >= input.stdout.length) { "stdout original length is inconsistent" }
        require(input.stderrOriginalLength >= input.stderr.length) { "stderr original length is inconsistent" }
        val state = if (input.errCode == NO_INTERNAL_ERROR && input.exitCode == 0) {
            JobState.SUCCEEDED
        } else {
            JobState.FAILED
        }
        val fields = listOf(
            "schema" to json("anvil.shell.termux-result.v1"),
            "jobId" to json(input.jobId),
            "state" to json(state.name),
            "route" to json(CommandRoute.TERMUX_COMPAT.name),
            "modelUsed" to "false",
            "exitCode" to input.exitCode.toString(),
            "errCode" to input.errCode.toString(),
            "stdoutCapturedLength" to input.stdout.length.toString(),
            "stdoutOriginalLength" to input.stdoutOriginalLength.toString(),
            "stdoutTruncated" to (input.stdoutOriginalLength > input.stdout.length).toString(),
            "stdoutSha256" to json(sha256(input.stdout)),
            "stdoutTail" to json(input.stdout.takeLast(OUTPUT_TAIL_LIMIT)),
            "stderrCapturedLength" to input.stderr.length.toString(),
            "stderrOriginalLength" to input.stderrOriginalLength.toString(),
            "stderrTruncated" to (input.stderrOriginalLength > input.stderr.length).toString(),
            "stderrSha256" to json(sha256(input.stderr)),
            "stderrTail" to json(input.stderr.takeLast(OUTPUT_TAIL_LIMIT)),
            "errorMessageTail" to json(input.errorMessage.takeLast(ERROR_TAIL_LIMIT))
        )
        return TermuxTerminalOutcome(state, fields.joinToString(prefix = "{", postfix = "}") { (key, value) ->
            json(key) + ":" + value
        })
    }

    private fun sha256(value: String): String = MessageDigest.getInstance("SHA-256")
        .digest(value.toByteArray(Charsets.UTF_8))
        .joinToString("") { "%02x".format(Locale.ROOT, it) }

    private fun json(value: String): String = buildString(value.length + 2) {
        append('"')
        value.forEach { character ->
            when (character) {
                '"' -> append("\\\"")
                '\\' -> append("\\\\")
                '\b' -> append("\\b")
                '\u000c' -> append("\\f")
                '\n' -> append("\\n")
                '\r' -> append("\\r")
                '\t' -> append("\\t")
                else -> if (character.code < 0x20) {
                    append("\\u")
                    append(character.code.toString(16).padStart(4, '0'))
                } else {
                    append(character)
                }
            }
        }
        append('"')
    }
}
