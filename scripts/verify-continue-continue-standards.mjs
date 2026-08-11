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

if (failures.length) {
  console.error("Continue Continue standards check failed:\n" + failures.map((f) => `- ${f}`).join("\n"));
  process.exit(1);
}

console.log("Continue Continue standards check passed.");
