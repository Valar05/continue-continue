import { readFileSync, existsSync } from "node:fs";

const failures = [];
const requireFile = (path) => {
  if (!existsSync(path)) failures.push(`missing required file: ${path}`);
};

const requiredFiles = [
  "AGENTS.md",
  ".continue/rules/fortress-mission-boundary.md",
  ".continue/rules/fortress-evidence.md",
  ".continue/rules/local-first.md",
  ".continue/rules/judgment-jars.md",
  ".continue/checks/mission-boundary.md",
  ".continue/checks/evidence-receipt.md",
  ".continue/checks/ravenholm.md",
  ".continue/checks/local-first.md",
  ".github/workflows/docs-gh-pages.yml",
  ".github/workflows/main.yaml",
  ".github/workflows/jetbrains-release.yaml",
  "extensions/cli/src/automation/AutomationTypes.ts",
  "extensions/cli/src/automation/AutomationValidation.ts",
  "extensions/cli/src/automation/AutomationRuntime.ts",
  "extensions/cli/src/automation/AutomationRuntime.test.ts",
  "extensions/cli/src/automation/AutomationTaskStore.ts",
  "extensions/cli/src/automation/AutomationHttpService.ts",
  "extensions/cli/src/automation/AutomationServeAdapter.ts",
  "extensions/cli/src/commands/serve.ts",
  "extensions/cli/src/commands/serve.helpers.ts",
  "extensions/cli/src/stream/messageQueue.ts",
  "edge/termux/vlad_edge.py",
  "edge/termux/test_vlad_edge.py",
  "edge/termux/vlad_router.py",
  "edge/termux/test_vlad_router.py",
  "edge/termux/vlad_doctor.py",
  "edge/termux/test_vlad_doctor.py",
  "edge/termux/vlad_cli.py",
  "edge/termux/test_vlad_cli.py",
  "edge/termux/adam_cli.py",
  "edge/termux/test_adam_cli.py",
  "edge/termux/adam_doctor.py",
  "edge/termux/test_adam_doctor.py",
  "edge/termux/routes.csv",
  "edge/termux/install.sh",
  "docs/continue-continue/AUTOMATION_LAYER.md",
  "docs/continue-continue/VLAD_TERMUX_EDGE.md",
  "docs/continue-continue/VLAD_ROUTING_SHEET.md",
  "docs/continue-continue/VLAD_CLI.md",
  "docs/continue-continue/JUDGMENT_JARS.md",
  "docs/continue-continue/MODERNIZATION.md",
];
requiredFiles.forEach(requireFile);

const read = (path) => (existsSync(path) ? readFileSync(path, "utf8") : "");
const constitution = read("AGENTS.md");
for (const phrase of [
  "Beautiful substitution",
  "Receiptless victory",
  "Ravenholm",
  "Local-first baseline",
  "Status vocabulary",
  "Machine automation law",
]) {
  if (!constitution.includes(phrase))
    failures.push(`AGENTS.md lost required doctrine: ${phrase}`);
}

const starter = read("core/config/createNewAssistantFile.ts");
if (!starter.includes("provider: ollama"))
  failures.push("new assistant starter must include an Ollama local model");
for (const forbidden of [
  "YOUR_OPENAI_API_KEY",
  "ANTHROPIC_API_KEY",
  "provider: openai",
  "provider: anthropic",
]) {
  if (starter.includes(forbidden))
    failures.push(
      `new assistant starter contains cloud-first token/provider marker: ${forbidden}`,
    );
}

for (const path of requiredFiles.filter((p) => p.startsWith(".continue/checks/"))) {
  const content = read(path);
  if (
    !content.startsWith("---\n") ||
    !content.includes("\nname:") ||
    !content.includes("\ndescription:")
  ) {
    failures.push(`Continue check is missing expected frontmatter: ${path}`);
  }
}

const automationTypes = read("extensions/cli/src/automation/AutomationTypes.ts");
const automationRuntime = read(
  "extensions/cli/src/automation/AutomationRuntime.ts",
);
const automationContract = `${automationTypes}\n${automationRuntime}`;
for (const phrase of [
  "continue-continue-machine-task",
  "continue-continue-receipt",
  "automation/orchestration layer",
  "Existing tool permission policy still controls execution",
  "awaiting_verification",
  "delegated",
  "toolEvents",
  "acceptanceCriteria",
]) {
  if (!automationContract.includes(phrase))
    failures.push(`automation contract lost required invariant: ${phrase}`);
}
if (automationContract.includes('type AutomationDomain = "audio"')) {
  failures.push("automation domains must remain open-ended routing metadata");
}

const automationHttp = read(
  "extensions/cli/src/automation/AutomationHttpService.ts",
);
for (const route of [
  'app.post("/automation/tasks"',
  'app.get("/automation/tasks"',
  'app.get("/automation/capabilities"',
  '"/automation/tasks/:taskId/receipt"',
  '"/automation/tasks/:taskId/cancel"',
]) {
  if (!automationHttp.includes(route))
    failures.push(`automation HTTP service lost route: ${route}`);
}

const serveAdapter = read(
  "extensions/cli/src/automation/AutomationServeAdapter.ts",
);
for (const phrase of [
  "registerAutomationRoutes",
  "removeAutomationTask",
  "BUILT_IN_TOOL_NAMES",
]) {
  if (!serveAdapter.includes(phrase))
    failures.push(`serve automation adapter lost integration: ${phrase}`);
}

const serve = read("extensions/cli/src/commands/serve.ts");
for (const phrase of [
  "registerServeAutomationRoutes",
  "AutomationTaskStore",
  "activeAutomationTaskId",
  "beginAutomationTurn",
  "completeAutomationTurn",
]) {
  if (!serve.includes(phrase))
    failures.push(`cn serve lost automation integration: ${phrase}`);
}

const serveHelpers = read("extensions/cli/src/commands/serve.helpers.ts");
for (const lifecycleHook of [
  "markToolStart",
  "markToolResult",
  "markToolError",
  "markPermissionBlocked",
  "applyAgentResponse",
]) {
  if (!serveHelpers.includes(lifecycleHook))
    failures.push(`automation receipt lost lifecycle hook: ${lifecycleHook}`);
}

const queue = read("extensions/cli/src/stream/messageQueue.ts");
for (const phrase of ["automationTaskId", "removeAutomationTask"]) {
  if (!queue.includes(phrase))
    failures.push(`message queue lost automation identity: ${phrase}`);
}

const vlad = read("edge/termux/vlad_edge.py");
for (const phrase of [
  "VLAD_ALLOW_PHONE_HANDS",
  "VLAD_ALLOW_LOCAL_EXEC",
  "CONTINUE_CONTINUE_UPSTREAM_URL",
  "QWEN_BASE_URL",
  '"delegated"',
  '"route": "blocked"',
]) {
  if (!vlad.includes(phrase))
    failures.push(`Vlad edge lost authority/routing contract: ${phrase}`);
}

const vladRouter = read("edge/termux/vlad_router.py");
for (const phrase of [
  "csv-first-match",
  "/routing/preview",
  "VLAD_ROUTING_SHEET",
  "VLAD_EDGE_INTERNAL",
  "caller supplied explicit edge action; routing sheet did not override it",
  '"route": "passthrough"',
]) {
  if (!vladRouter.includes(phrase))
    failures.push(`Vlad ingress router lost invariant: ${phrase}`);
}

const routingSheet = read("edge/termux/routes.csv");
if (
  !routingSheet.startsWith(
    "priority,enabled,name,domain,contains_any,contains_all,route,target_domain,command,phone_prompt,reason",
  )
) {
  failures.push("Vlad routing sheet lost its spreadsheet contract header");
}
for (const rule of ["deny-destructive-phone", "android-ui", "audio-work", "video-work"]) {
  if (!routingSheet.includes(rule))
    failures.push(`Vlad routing sheet lost foundational rule: ${rule}`);
}

const vladCli = read("edge/termux/vlad_cli.py");
for (const phrase of [
  "continue-continue.vlad-cli.v1",
  "explicit_phone_task",
  "continue_task",
  '"cn", "-p"',
  '"--readonly"',
  '"--auto"',
  "Vlad edge gate still applies",
]) {
  if (!vladCli.includes(phrase))
    failures.push(`Vlad human CLI lost survival/authority invariant: ${phrase}`);
}

const adamCli = read("edge/termux/adam_cli.py");
for (const phrase of [
  'input("adam> ")',
  'text.startswith("!")',
  'text.startswith("/code ")',
  'text.startswith("/review ")',
  "no model fallback is permitted",
]) {
  if (!adamCli.includes(phrase))
    failures.push(`Adam human ingress lost deterministic invariant: ${phrase}`);
}

const vladInstaller = read("edge/termux/install.sh");
for (const phrase of [
  "continue-continue-vlad-router",
  "continue-continue-vlad-edge",
  "routes.csv",
  "if [ ! -f",
  "Stable machine entrypoint",
  "Adam is the human-facing phone daemon",
  '"$SOURCE_DIR/vlad_cli.py" "$BIN_DIR/continue-continue-vlad-cli"',
  '"$SOURCE_DIR/adam_cli.py" "$BIN_DIR/continue-continue-adam-cli"',
  'exec "$BIN_DIR/continue-continue-adam-cli"',
]) {
  if (!vladInstaller.includes(phrase))
    failures.push(`Adam/Vlad installer lost routed/human ingress invariant: ${phrase}`);
}

const vladDoctor = read("edge/termux/vlad_doctor.py");
for (const phrase of [
  "routing_sheet",
  "DEFAULT_ROUTING_SHEET",
  "internal_edge_binary",
  "routing sheet has no enabled rows",
]) {
  if (!vladDoctor.includes(phrase))
    failures.push(`Vlad doctor lost routing readiness invariant: ${phrase}`);
}

const docsPublish = read(".github/workflows/docs-gh-pages.yml");
if (docsPublish.includes("on:\n  push:"))
  failures.push("docs publication must not auto-trigger on push");
if (!docsPublish.includes("workflow_dispatch:"))
  failures.push("docs publication must retain an explicit manual trigger");

const vscodePublish = read(".github/workflows/main.yaml");
if (vscodePublish.includes("on:\n  release:"))
  failures.push("VS Code publication must not auto-trigger from GitHub release events");
if (vscodePublish.includes("repository: continuedev/continue"))
  failures.push("VS Code publication must never target the upstream repository");
if (!vscodePublish.includes("github.event.inputs.publish_build == 'true'"))
  failures.push(
    "VS Code publication must require explicit publish_build=true authorization",
  );

const jetbrainsPublish = read(".github/workflows/jetbrains-release.yaml");
if (jetbrainsPublish.includes("on:\n  release:"))
  failures.push("JetBrains publication must not auto-trigger from prerelease events");
if (!jetbrainsPublish.includes("workflow_dispatch:"))
  failures.push("JetBrains release workflow must retain an explicit manual trigger");

if (failures.length) {
  console.error(
    "Continue Continue standards check failed:\n" +
      failures.map((f) => `- ${f}`).join("\n"),
  );
  process.exit(1);
}

console.log("Continue Continue standards check passed.");
