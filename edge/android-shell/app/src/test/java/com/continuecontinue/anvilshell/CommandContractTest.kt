package com.continuecontinue.anvilshell

import org.junit.Assert.assertEquals
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
    fun explicitShellIsInteractionPlane() {
        val spec = CommandRegistry.resolve(request("shell.exec", listOf("git status")))
        assertEquals(CommandPlane.PHONE_INTERACTION, spec.plane)
        assertEquals(CommandRoute.TERMUX_COMPAT, spec.route)
    }
}
