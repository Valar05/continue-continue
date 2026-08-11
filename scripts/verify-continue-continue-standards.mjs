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
  "edge/termux/install.sh",
  "docs/continue-continue/AUTOMATION_LAYER.md",
  "docs/continue-continue/VLAD_TERMUX_EDGE.md",
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
