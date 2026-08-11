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
  "docs/continue-continue/JUDGMENT_JARS.md",
  "docs/continue-continue/MODERNIZATION.md",
];
requiredFiles.forEach(requireFile);

const read = (path) => (existsSync(path) ? readFileSync(path, "utf8") : "");
const constitution = read("AGENTS.md");
for (const phrase of ["Beautiful substitution", "Receiptless victory", "Ravenholm", "Local-first baseline", "Status vocabulary"]) {
  if (!constitution.includes(phrase)) failures.push(`AGENTS.md lost required doctrine: ${phrase}`);
}

const starter = read("core/config/createNewAssistantFile.ts");
if (!starter.includes("provider: ollama")) failures.push("new assistant starter must include an Ollama local model");
for (const forbidden of ["YOUR_OPENAI_API_KEY", "ANTHROPIC_API_KEY", "provider: openai", "provider: anthropic"]) {
  if (starter.includes(forbidden)) failures.push(`new assistant starter contains cloud-first token/provider marker: ${forbidden}`);
}

for (const path of requiredFiles.filter((p) => p.startsWith(".continue/checks/"))) {
  const content = read(path);
  if (!content.startsWith("---\n") || !content.includes("\nname:") || !content.includes("\ndescription:")) {
    failures.push(`Continue check is missing expected frontmatter: ${path}`);
  }
}

const docsPublish = read(".github/workflows/docs-gh-pages.yml");
if (docsPublish.includes("on:\n  push:")) failures.push("docs publication must not auto-trigger on push");
if (!docsPublish.includes("workflow_dispatch:")) failures.push("docs publication must retain an explicit manual trigger");

const vscodePublish = read(".github/workflows/main.yaml");
if (vscodePublish.includes("on:\n  release:")) failures.push("VS Code publication must not auto-trigger from GitHub release events");
if (vscodePublish.includes("repository: continuedev/continue")) failures.push("VS Code publication must never target the upstream repository");
if (!vscodePublish.includes("github.event.inputs.publish_build == 'true'")) failures.push("VS Code publication must require explicit publish_build=true authorization");

const jetbrainsPublish = read(".github/workflows/jetbrains-release.yaml");
if (jetbrainsPublish.includes("on:\n  release:")) failures.push("JetBrains publication must not auto-trigger from prerelease events");
if (!jetbrainsPublish.includes("workflow_dispatch:")) failures.push("JetBrains release workflow must retain an explicit manual trigger");

if (failures.length) {
  console.error("Continue Continue standards check failed:\n" + failures.map((f) => `- ${f}`).join("\n"));
  process.exit(1);
}

console.log("Continue Continue standards check passed.");
