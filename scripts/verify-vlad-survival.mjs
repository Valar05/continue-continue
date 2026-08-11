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
  if (!edge.includes(phrase)) failures.push(`Vlad edge lost survival authority invariant: ${phrase}`);
}

const cli = read("edge/termux/vlad_cli.py");
for (const phrase of [
  "continue-continue.vlad-cli.v1",
  "DOCTOR_REQUIREMENTS",
  '"allowedBins"',
  "narrows shell authority",
  '"--readonly"',
  '"--auto"',
  '"--resume"',
  "continue_session_started",
  'text == "/new"',
]) {
  if (!cli.includes(phrase)) failures.push(`Vlad CLI lost survival/continuity invariant: ${phrase}`);
}

const doctor = read("edge/termux/vlad_doctor.py");
for (const phrase of [
  '"continue"',
  '"continue_binary"',
  '"continue_permission"',
  '"continue_policy"',
  "VLAD_CN_BIN",
  "VLAD_ALLOWED_BINS",
]) {
  if (!doctor.includes(phrase)) failures.push(`Vlad doctor lost Continue readiness invariant: ${phrase}`);
}

const installer = read("edge/termux/install.sh");
for (const phrase of [
  "Stable machine entrypoint",
  "First-class human survival surface",
  '"$SOURCE_DIR/vlad_cli.py" "$BIN_DIR/vlad"',
]) {
  if (!installer.includes(phrase)) failures.push(`Vlad installer lost two-door invariant: ${phrase}`);
}

const docs = read("docs/continue-continue/VLAD_CLI.md");
for (const phrase of [
  "vlad doctor --require continue",
  "Per-task authority can only narrow global shell authority",
  "Later `/code` and `/review` turns automatically add `--resume`",
  "no ChatGPT",
  "no Continue",
]) {
  if (!docs.includes(phrase)) failures.push(`Vlad survival documentation lost invariant: ${phrase}`);
}

if (failures.length) {
  console.error("Vlad survival verification failed:\n" + failures.map((x) => `- ${x}`).join("\n"));
  process.exit(1);
}

console.log("Vlad survival verification passed.");
