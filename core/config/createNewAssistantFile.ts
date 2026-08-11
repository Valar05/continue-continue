import { IDE } from "..";
import { joinPathsToUri } from "../util/uri";

const DEFAULT_ASSISTANT_FILE = `# Local-first starter configuration.
# To learn more, see the full config.yaml reference: https://docs.continue.dev/reference
# Remote providers are supported, but add them explicitly when you want them.

name: Local Coding
version: 1.0.0
schema: v1

models:
  - name: qwen2.5-coder 7b local
    provider: ollama
    model: qwen2.5-coder:7b
    roles:
      - apply
      - autocomplete
      - chat
      - edit
`;

export async function createNewAssistantFile(
  ide: IDE,
  assistantPath: string | undefined,
): Promise<void> {
  const workspaceDirs = await ide.getWorkspaceDirs();
  if (workspaceDirs.length === 0) {
    throw new Error(
      "No workspace directories found. Make sure you've opened a folder in your IDE.",
    );
  }

  const baseDirUri = joinPathsToUri(
    workspaceDirs[0],
    assistantPath ?? ".continue/agents",
  );

  // Find the first available filename
  let counter = 0;
  let assistantFileUri: string;
  do {
    const suffix = counter === 0 ? "" : `-${counter}`;
    assistantFileUri = joinPathsToUri(baseDirUri, `new-config${suffix}.yaml`);
    counter++;
  } while (await ide.fileExists(assistantFileUri));

  await ide.writeFile(assistantFileUri, DEFAULT_ASSISTANT_FILE);
  await ide.openFile(assistantFileUri);
}
