package com.continuecontinue.anvilshell

import java.security.MessageDigest
import java.util.Locale

enum class CommandPlane {
    PHONE_DIAGNOSTICS_READONLY,
    PHONE_MAINTENANCE,
    PHONE_INTERACTION,
    JUDGMENT
}

enum class CommandRoute {
    NATIVE,
    TERMUX_COMPAT,
    HOME_CENTER,
    LOCAL_MODEL
}

data class CommandSpec(
    val verb: String,
    val plane: CommandPlane,
    val route: CommandRoute,
    val executable: String? = null,
    val minArgs: Int = 0,
    val maxArgs: Int = 32,
    val networkOptional: Boolean = true
)

data class CommandRequest(
    val commandId: String,
    val idempotencyKey: String,
    val verb: String,
    val args: List<String> = emptyList(),
    val anvil: String,
    val owner: String,
    val team: String? = null,
    val cwd: String? = null
) {
    fun canonical(): String = listOf(
        commandId,
        idempotencyKey,
        verb,
        args.joinToString("\u001f"),
        anvil,
        owner,
        team.orEmpty(),
        cwd.orEmpty()
    ).joinToString("\u001e")

    fun sha256(): String = MessageDigest.getInstance("SHA-256")
        .digest(canonical().toByteArray(Charsets.UTF_8))
        .joinToString("") { "%02x".format(Locale.ROOT, it) }
}

object CommandRegistry {
    private val safeId = Regex("[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
    private val forbiddenText = Regex("[\\u0000\\r\\n]")

    private val specs = listOf(
        CommandSpec("status", CommandPlane.PHONE_DIAGNOSTICS_READONLY, CommandRoute.NATIVE),
        CommandSpec("doctor", CommandPlane.PHONE_DIAGNOSTICS_READONLY, CommandRoute.NATIVE),
        CommandSpec("session.list", CommandPlane.PHONE_DIAGNOSTICS_READONLY, CommandRoute.NATIVE),
        CommandSpec("session.open", CommandPlane.PHONE_INTERACTION, CommandRoute.NATIVE, minArgs = 1, maxArgs = 3),
        CommandSpec("session.checkpoint", CommandPlane.PHONE_MAINTENANCE, CommandRoute.NATIVE, minArgs = 1, maxArgs = 2),
        CommandSpec("session.resume", CommandPlane.PHONE_INTERACTION, CommandRoute.NATIVE, minArgs = 1, maxArgs = 2),
        CommandSpec("session.stop", CommandPlane.PHONE_INTERACTION, CommandRoute.NATIVE, minArgs = 1, maxArgs = 2),
        CommandSpec("anvil.select", CommandPlane.PHONE_INTERACTION, CommandRoute.NATIVE, minArgs = 1, maxArgs = 1),
        CommandSpec("anvil.stream", CommandPlane.PHONE_DIAGNOSTICS_READONLY, CommandRoute.NATIVE, minArgs = 0, maxArgs = 1),
        CommandSpec("adam.doctor", CommandPlane.PHONE_DIAGNOSTICS_READONLY, CommandRoute.TERMUX_COMPAT, executable = "\$PREFIX/local/bin/adam", maxArgs = 0),
        CommandSpec("adam.status", CommandPlane.PHONE_DIAGNOSTICS_READONLY, CommandRoute.TERMUX_COMPAT, executable = "\$PREFIX/local/bin/adam", maxArgs = 0),
        CommandSpec("adam.quote", CommandPlane.PHONE_DIAGNOSTICS_READONLY, CommandRoute.TERMUX_COMPAT, executable = "\$PREFIX/local/bin/adam", maxArgs = 4),
        CommandSpec("vlad.notes.status", CommandPlane.PHONE_DIAGNOSTICS_READONLY, CommandRoute.TERMUX_COMPAT, executable = "\$PREFIX/local/bin/vlad-notes", maxArgs = 0),
        CommandSpec("vlad.notes.compile", CommandPlane.PHONE_MAINTENANCE, CommandRoute.TERMUX_COMPAT, executable = "\$PREFIX/local/bin/vlad-notes", maxArgs = 2),
        CommandSpec("vlad.notes.query", CommandPlane.PHONE_DIAGNOSTICS_READONLY, CommandRoute.TERMUX_COMPAT, executable = "\$PREFIX/local/bin/vlad-notes", minArgs = 1, maxArgs = 8),
        CommandSpec("vlad.notes.next", CommandPlane.PHONE_DIAGNOSTICS_READONLY, CommandRoute.TERMUX_COMPAT, executable = "\$PREFIX/local/bin/vlad-notes", maxArgs = 1),
        CommandSpec("vlad.notes.receipt", CommandPlane.PHONE_MAINTENANCE, CommandRoute.TERMUX_COMPAT, executable = "\$PREFIX/local/bin/vlad-notes", minArgs = 1, maxArgs = 8),
        CommandSpec("shell.exec", CommandPlane.PHONE_INTERACTION, CommandRoute.TERMUX_COMPAT, executable = "\$PREFIX/bin/sh", minArgs = 1, maxArgs = 1),
        CommandSpec("hunger.invoke", CommandPlane.JUDGMENT, CommandRoute.HOME_CENTER, minArgs = 1, maxArgs = 4, networkOptional = false),
        CommandSpec("hyperbolic.invoke", CommandPlane.JUDGMENT, CommandRoute.HOME_CENTER, minArgs = 1, maxArgs = 4, networkOptional = false),
        CommandSpec("hf.status", CommandPlane.PHONE_DIAGNOSTICS_READONLY, CommandRoute.NATIVE),
        CommandSpec("hf.import", CommandPlane.PHONE_MAINTENANCE, CommandRoute.NATIVE, minArgs = 3, maxArgs = 8, networkOptional = false),
        CommandSpec("hf.verify", CommandPlane.PHONE_DIAGNOSTICS_READONLY, CommandRoute.NATIVE, minArgs = 1, maxArgs = 2),
        CommandSpec("hf.bench", CommandPlane.PHONE_INTERACTION, CommandRoute.LOCAL_MODEL, minArgs = 1, maxArgs = 4)
    ).associateBy { it.verb }

    fun resolve(request: CommandRequest): CommandSpec {
        require(safeId.matches(request.commandId)) { "invalid commandId" }
        require(safeId.matches(request.idempotencyKey)) { "invalid idempotencyKey" }
        require(safeId.matches(request.anvil)) { "invalid anvil marker" }
        require(safeId.matches(request.owner)) { "invalid owner marker" }
        request.team?.let { require(safeId.matches(it)) { "invalid team marker" } }
        require(request.args.none { forbiddenText.containsMatchIn(it) }) { "arguments contain a forbidden control character" }
        request.cwd?.let { require(it.startsWith("/")) { "cwd must be absolute" } }

        val spec = specs[request.verb] ?: error("unknown deterministic verb: ${request.verb}")
        require(request.args.size in spec.minArgs..spec.maxArgs) {
            "${request.verb} requires ${spec.minArgs}..${spec.maxArgs} arguments"
        }
        return spec
    }

    fun verbs(): Set<String> = specs.keys
}
