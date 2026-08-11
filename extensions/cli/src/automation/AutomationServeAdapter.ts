import type { Express } from "express";

import type { ServerState } from "../commands/serve.helpers.js";
import { messageQueue } from "../stream/messageQueue.js";
import { BUILT_IN_TOOL_NAMES } from "../tools/builtInToolNames.js";
import { registerAutomationRoutes } from "./AutomationHttpService.js";
import type { AutomationRuntime } from "./AutomationRuntime.js";

export function registerServeAutomationRoutes(
  app: Express,
  state: ServerState,
  runtime: AutomationRuntime,
  startProcessing: () => void,
): void {
  registerAutomationRoutes(app, runtime, {
    enqueue: async (taskId, taskPrompt) => {
      await messageQueue.enqueueMessage(
        taskPrompt,
        undefined,
        undefined,
        taskId,
      );
      if (!state.isProcessing) startProcessing();
    },
    cancelQueued: (taskId) => messageQueue.removeAutomationTask(taskId),
    activeTaskId: () => state.activeAutomationTaskId,
    abortActive: (taskId) => {
      if (state.activeAutomationTaskId !== taskId) return false;
      state.currentAbortController?.abort();
      return true;
    },
    capabilities: () => ({
      runtime: "full",
      domains: "open",
      builtInTools: [...BUILT_IN_TOOL_NAMES],
      notes: [
        "Configured MCP, Home Center, media, game, and other external tools remain explicit permission-gated executors.",
      ],
    }),
  });
}
