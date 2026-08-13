package com.continuecontinue.anvilshell

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CommandContractTest {
    private fun request(
        verb: String = "status",
        args: List<String> = emptyList(),
        key: String = "anvil-test-001"
    ) = CommandRequest(
        commandId = "cmd-test-001",
        idempotencyKey = key,
        verb = verb,
        args = args,
        anvil = "shell",
        owner = "drew",
        team = "adam"
    )

    @Test
    fun deterministicRegistryContainsCommissionedOrgans() {
        val verbs = CommandRegistry.verbs()
        assertTrue("hunger.invoke" in verbs)
        assertTrue("hyperbolic.invoke" in verbs)
        assertTrue("hf.import" in verbs)
        assertTrue("vlad.notes.receipt" in verbs)
        assertTrue("anvil.stream" in verbs)
    }

    @Test
    fun sameRequestHasStableHash() {
        assertEquals(request().sha256(), request().sha256())
        assertNotEquals(request().sha256(), request(key = "anvil-test-002").sha256())
    }

    @Test(expected = IllegalArgumentException::class)
    fun newlineInArgumentFailsClosed() {
        CommandRegistry.resolve(request("shell.exec", listOf("safe\nnot-safe")))
    }

    @Test(expected = IllegalStateException::class)
    fun unknownFreeTextNeverFallsThrough() {
        CommandRegistry.resolve(request("please.just.figure.it.out"))
    }

    @Test
    fun deterministicQuoteUsesTheTermuxCompatibilityRoute() {
        val spec = CommandRegistry.resolve(
            request("adam.quote", listOf("--seed", "receipt-42", "--category", "bible"))
        )
        assertEquals(CommandRoute.TERMUX_COMPAT, spec.route)
        assertEquals("/data/data/com.termux/files/usr/local/bin/adam", spec.executable)
    }

    @Test
    fun everyCompatibilityExecutableIsAbsoluteAndUnexpanded() {
        val compatibilityRequests = listOf(
            request("adam.doctor"),
            request("adam.status"),
            request("adam.quote"),
            request("vlad.notes.status"),
            request("vlad.notes.compile"),
            request("vlad.notes.query", listOf("gate")),
            request("vlad.notes.next"),
            request("vlad.notes.receipt", listOf("ROUTE")),
            request("shell.exec", listOf("git status"))
        )
        compatibilityRequests.map(CommandRegistry::resolve).forEach { spec ->
            assertTrue(spec.executable?.startsWith("/") == true)
            assertFalse(spec.executable.orEmpty().contains("$"))
        }
    }

    @Test
    fun recoverableExternalWorkNeverAutoClaims() {
        assertEquals(setOf(JobState.QUEUED), AUTO_CLAIMABLE_STATES)
        assertFalse(JobState.DISPATCHED in AUTO_CLAIMABLE_STATES)
        assertFalse(JobState.RECOVERABLE in AUTO_CLAIMABLE_STATES)
    }

    @Test
    fun explicitShellIsInteractionPlane() {
        val spec = CommandRegistry.resolve(request("shell.exec", listOf("git status")))
        assertEquals(CommandPlane.PHONE_INTERACTION, spec.plane)
        assertEquals(CommandRoute.TERMUX_COMPAT, spec.route)
    }
    @Test
    fun termuxSuccessReceiptIsDeterministicAndSourceCarrying() {
        val input = TermuxTerminalInput(
            jobId = "job-42",
            stdout = "load-bearing output",
            stderr = "",
            stdoutOriginalLength = 19,
            stderrOriginalLength = 0,
            exitCode = 0,
            errCode = TermuxResultContract.NO_INTERNAL_ERROR,
            errorMessage = ""
        )
        val first = TermuxResultContract.evaluate(input)
        val second = TermuxResultContract.evaluate(input)
        assertEquals(JobState.SUCCEEDED, first.state)
        assertEquals(first, second)
        assertTrue(first.receipt.contains("\"schema\":\"anvil.shell.termux-result.v1\""))
        assertTrue(first.receipt.contains("\"stdoutSha256\""))
        assertTrue(first.receipt.contains("\"stdoutTruncated\":false"))
    }

    @Test
    fun termuxNonZeroOrInternalErrorFailsClosed() {
        val nonZero = TermuxResultContract.evaluate(
            TermuxTerminalInput("job-exit", "", "bad", 0, 3, 7, -1, "")
        )
        val internal = TermuxResultContract.evaluate(
            TermuxTerminalInput("job-err", "", "", 0, 0, 0, 5, "Termux error")
        )
        assertEquals(JobState.FAILED, nonZero.state)
        assertEquals(JobState.FAILED, internal.state)
    }

    @Test
    fun termuxReceiptMarksProviderTruncationAndBoundsItsTail() {
        val captured = "x".repeat(12_000)
        val outcome = TermuxResultContract.evaluate(
            TermuxTerminalInput("job-large", captured, "", 20_000, 0, 0, -1, "")
        )
        assertTrue(outcome.receipt.contains("\"stdoutCapturedLength\":12000"))
        assertTrue(outcome.receipt.contains("\"stdoutOriginalLength\":20000"))
        assertTrue(outcome.receipt.contains("\"stdoutTruncated\":true"))
        assertFalse(outcome.receipt.contains(captured))
    }

}
