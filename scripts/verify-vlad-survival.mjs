import { existsSync, readFileSync } from "node:fs";

const failures = [];
const read = (path) => {
  if (!existsSync(path)) {
    failures.push(`missing required Vlad survival file: ${path}`);
    return "";
  }
  return readFileSync(path, "utf8");
};

const edge = read("edge/termux/vlad_edge.py");
for (const phrase of [
  "DEFAULT_ALLOWED_BINS",
  "_shell_allowed_bins",
  'action.get("allowedBins")',
  "policy & narrowed",
  "Per-task allowedBins can only narrow",
  "VLAD_ALLOW_LOCAL_EXEC",
  "VLAD_ALLOW_PHONE_HANDS",
]) {
  if (!edge.includes(phrase))
    failures.push(`Vlad edge lost survival authority invariant: ${phrase}`);
}

const cli = read("edge/termux/vlad_cli.py");
for (const phrase of [
  "continue-continue.vlad-cli.v1",
  "DOCTOR_REQUIREMENTS",
  "SESSION_ID_PATTERN",
  "new_continue_session_id",
  '"allowedBins"',
  "narrows shell authority",
  '"--readonly"',
  '"--auto"',
  '"--session-id"',
  "continueSessionId",
  'text == "/session"',
  'text == "/new"',
  "Independent verification is still required",
  "not that unverified code is accepted",
]) {
  if (!cli.includes(phrase))
    failures.push(`Vlad CLI lost survival/continuity invariant: ${phrase}`);
}

const bootstrap = read("edge/termux/vlad_continue_bootstrap.py");
for (const phrase of [
  "continue-continue.vlad-bootstrap.v1",
  '"/api/tags"',
  "Vlad will not download one implicitly",
  "provider: ollama",
  "roles:",
  "--force",
  "vlad doctor --require continue",
]) {
  if (!bootstrap.includes(phrase))
    failures.push(`Vlad local coder bootstrap lost minimum-machine invariant: ${phrase}`);
}

const cnSourceInstaller = read("edge/termux/install_cn_from_source.sh");
for (const phrase of [
  "Node >=18",
  "npm run build:local-deps",
  "npm run build",
  "continue-continue-cli",
  '"$BIN_DIR/cn" --version',
]) {
  if (!cnSourceInstaller.includes(phrase))
    failures.push(`Vlad exact-fork cn installer lost minimum-machine invariant: ${phrase}`);
}

const minimumBootstrap = read("edge/termux/bootstrap_minimum_vlad.sh");
for (const phrase of [
  "install_cn_from_source.sh",
  '"$SOURCE_DIR/install.sh"',
  "vlad bootstrap",
  "VLAD_ALLOW_LOCAL_EXEC=1 vlad doctor --require continue",
  "VLAD_CAN_CODE",
  "After that succeeds, stop using the outside coding path",
]) {
  if (!minimumBootstrap.includes(phrase))
    failures.push(`Vlad minimum bootstrap lost handoff invariant: ${phrase}`);
}

const continueIndex = read("extensions/cli/src/index.ts");
for (const phrase of [
  '"--session-id <sessionId>"',
  "CONTINUE_CLI_SESSION_ID",
  "parallel-safe alternative to --resume",
]) {
  if (!continueIndex.includes(phrase))
    failures.push(`Continue CLI lost exact-session surface: ${phrase}`);
}

const continueSession = read("extensions/cli/src/session.ts");
for (const phrase of [
  "getExplicitSessionId",
  "CONTINUE_CLI_SESSION_ID",
  "CONTINUE_CLI_TEST_SESSION_ID",
  "SESSION_ID_PATTERN",
  "loadSessionById(explicitSessionId)",
  "createSession([], explicitSessionId)",
  "Legacy --resume behavior",
]) {
  if (!continueSession.includes(phrase))
    failures.push(`Continue session core lost exact-session invariant: ${phrase}`);
}
read("extensions/cli/src/session.explicitId.test.ts");

const doctor = read("edge/termux/vlad_doctor.py");
for (const phrase of [
  '"continue"',
  '"continue_binary"',
  '"continue_permission"',
  '"continue_policy"',
  '"ollama"',
  '"continue_local_config"',
  "VLAD_CN_BIN",
  "VLAD_ALLOWED_BINS",
  "VLAD_OLLAMA_URL",
]) {
  if (!doctor.includes(phrase))
    failures.push(`Vlad doctor lost Continue readiness invariant: ${phrase}`);
}

const adamDoctor = read("edge/termux/adam_doctor.py");
for (const phrase of [
  "continue-continue.adam-doctor.v1",
  '"vlad", "--json", "doctor", "--require", "continue"',
  '"UNKNOWN"',
  '"optional adviser; never required for Adam readiness"',
  "Adam does not contact Ollama or perform inference",
]) {
  if (!adamDoctor.includes(phrase))
    failures.push(`Adam doctor lost deterministic ownership invariant: ${phrase}`);
}
for (const forbidden of ["/api/tags", "urllib.request", "QWEN_BASE_URL"]) {
  if (adamDoctor.includes(forbidden))
    failures.push(`Adam doctor illegally reached into model ownership: ${forbidden}`);
}

const adamCli = read("edge/termux/adam_cli.py");
for (const phrase of [
  'input("adam> ")',
  'text.startswith("!")',
  'text.startswith("/code ")',
  'text.startswith("/review ")',
  "unknown Adam command; no model fallback is permitted",
]) {
  if (!adamCli.includes(phrase))
    failures.push(`Adam command surface lost deterministic routing invariant: ${phrase}`);
}

const installer = read("edge/termux/install.sh");
for (const phrase of [
  "Stable machine entrypoint",
  '"$SOURCE_DIR/vlad_cli.py" "$BIN_DIR/continue-continue-vlad-cli"',
  '"$SOURCE_DIR/vlad_continue_bootstrap.py" "$BIN_DIR/continue-continue-vlad-bootstrap"',
  '"$SOURCE_DIR/adam_doctor.py" "$BIN_DIR/continue-continue-adam-doctor"',
  '"$SOURCE_DIR/adam_cli.py" "$BIN_DIR/continue-continue-adam-cli"',
  'if [ "\\${1:-}" = "bootstrap" ]',
  'exec "$BIN_DIR/continue-continue-vlad-cli"',
  "Adam is the human-facing phone daemon",
  'exec "$BIN_DIR/continue-continue-adam-cli"',
  "adam doctor",
]) {
  if (!installer.includes(phrase))
    failures.push(`Adam/Vlad installer lost ownership/survival invariant: ${phrase}`);
}

const docs = read("docs/continue-continue/VLAD_CLI.md");
for (const phrase of [
  "vlad doctor --require continue",
  "Per-task authority can only narrow global shell authority",
  "no ChatGPT",
  "no Continue",
]) {
  if (!docs.includes(phrase))
    failures.push(`Vlad survival documentation lost invariant: ${phrase}`);
}

if (failures.length) {
  console.error(
    "Adam/Vlad survival verification failed:\n" +
      failures.map((x) => `- ${x}`).join("\n"),
  );
  process.exit(1);
}

console.log("Adam/Vlad survival verification passed.");