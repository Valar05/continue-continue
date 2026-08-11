import type { ChatHistoryItem, Session, ToolStatus } from "core/index.js";

import type { AutomationRuntime } from "../automation/AutomationRuntime.js";
import { services } from "../services/index.js";
import type { QueuedMessage } from "../stream/messageQueue.js";
import { streamChatResponse } from "../stream/streamChatResponse.js";
import { StreamCallbacks } from "../stream/streamChatResponse.types.js";
import { logger } from "../util/logger.js";

export function shouldQueueInitialPrompt(
  history: ChatHistoryItem[],
  prompt?: string | null,
): boolean {
  if (!prompt) return false;
  return !history.some((item) => item.message.role !== "system");
}

export function removePartialAssistantMessage(
  sessionHistory: ChatHistoryItem[],
): void {
  try {
    const svcHistory = services.chatHistory.getHistory();
    const last = svcHistory[svcHistory.length - 1];
    if (last && last.message.role === "assistant" && !last.message.content) {
      services.chatHistory.setHistory(svcHistory.slice(0, -1));
    }
  } catch {
    const lastMessage = sessionHistory[sessionHistory.length - 1];
    if (
      lastMessage &&
      lastMessage.message.role === "assistant" &&
      !lastMessage.message.content
    ) {
      sessionHistory.pop();
    }
  }
}

export interface AutomationTurnContext {
  runtime: AutomationRuntime;
  taskId: string;
}

export interface BeginAutomationTurnResult {
  taskId: string | null;
  skip: boolean;
}

export function beginAutomationTurn(
  state: ServerState,
  runtime: AutomationRuntime,
  queuedMessage: Pick<QueuedMessage, "message" | "automationTaskId">,
): BeginAutomationTurnResult {
  const taskId =
    queuedMessage.automationTaskId ?? runtime.extractTaskId(queuedMessage.message);
  if (taskId && runtime.shouldSkip(taskId)) {
    return { taskId, skip: true };
  }
  state.activeAutomationTaskId = taskId;
  if (taskId) runtime.markRunning(taskId);
  return { taskId, skip: false };
}

export function completeAutomationTurn(
  runtime: AutomationRuntime,
  taskId: string | null,
  response: string,
): void {
  if (!taskId) return;
  const task = runtime.getTask(taskId);
  if (task?.cancelRequested) {
    runtime.markCancelled(taskId);
  } else if (
    task &&
    !["blocked", "cancelled", "failed"].includes(task.status)
  ) {
    runtime.applyAgentResponse(taskId, response);
  }
}

export function handleAutomationAbort(
  runtime: AutomationRuntime,
  taskId: string | null,
): void {
  if (!taskId) return;
  const task = runtime.getTask(taskId);
  if (task?.cancelRequested) {
    runtime.markCancelled(taskId);
  } else if (
    task &&
    !["blocked", "blocked_permission", "cancelled"].includes(task.status)
  ) {
    runtime.markPaused(taskId);
  }
}

export function handleAutomationFailure(
  runtime: AutomationRuntime,
  taskId: string | null,
  error: string,
): void {
  if (taskId) runtime.markFailed(taskId, error);
}

export async function streamChatResponseWithInterruption(
  state: ServerState,
  llmApi: any,
  abortController: AbortController,
  shouldInterrupt: () => boolean,
  automation?: AutomationTurnContext,
): Promise<string> {
  const originalSignal = abortController.signal;
  const checkInterruption = () => {
    if (shouldInterrupt() && !originalSignal.aborted) {
      abortController.abort();
    }
  };

  const interruptionChecker = setInterval(checkInterruption, 100);

  const callbacks: StreamCallbacks = {
    onContent: (_: string) => {},
    onContentComplete: (_: string) => {},
    onToolStart: (toolName: string, _?: any) => {
      if (automation) {
        automation.runtime.markToolStart(automation.taskId, toolName);
      }
    },
    onToolResult: (_result: string, toolName: string, status: ToolStatus) => {
      if (automation) {
        automation.runtime.markToolResult(
          automation.taskId,
          toolName,
          String(status),
        );
      }
    },
    onToolError: (error: string, toolName?: string) => {
      if (automation) {
        automation.runtime.markToolError(
          automation.taskId,
          toolName,
          error,
        );
      }
    },
    onToolPermissionRequest: (
      toolName: string,
      toolArgs: any,
      requestId: string,
      toolCallPreview?: any[],
    ) => {
      state.pendingPermission = {
        toolName,
        toolArgs,
        requestId,
        timestamp: Date.now(),
        toolCallPreview,
      };
      if (automation) {
        automation.runtime.markPermissionBlocked(
          automation.taskId,
          toolName,
          requestId,
        );
      }

      try {
        services.chatHistory.addSystemMessage(
          `WARNING: Tool ${toolName} requires permission`,
        );
      } catch (err) {
        logger.error(
          "Failed to add system message via ChatHistoryService",
          err,
          { context: "onToolPermissionRequest", toolName, requestId },
        );
      }
    },
    onSystemMessage: (message: string) => {
      try {
        services.chatHistory.addSystemMessage(message);
      } catch (err) {
        logger.error(
          "Failed to add system message via ChatHistoryService",
          err,
          { context: "onSystemMessage" },
        );
      }
    },
  };

  try {
    const response = await streamChatResponse(
      state.session.history,
      state.model,
      llmApi,
      abortController,
      callbacks,
    );
    return response || "";
  } finally {
    clearInterval(interruptionChecker);
  }
}

export interface PendingPermission {
  toolName: string;
  toolArgs: any;
  requestId: string;
  timestamp: number;
  toolCallPreview?: any[];
}

export interface ServerState {
  session: Session;
  config: any;
  model: any;
  isProcessing: boolean;
  lastActivity: number;
  currentAbortController: AbortController | null;
  serverRunning: boolean;
  pendingPermission: PendingPermission | null;
  activeAutomationTaskId: string | null;
  systemMessage?: string;
}

export function checkAgentComplete(
  history: { message: { role: string; tool_calls?: any[] } }[] | undefined,
): boolean {
  if (!history || history.length === 0) {
    return false;
  }
  const lastItem = history[history.length - 1];
  if (lastItem?.message?.role !== "assistant") {
    return false;
  }
  const toolCalls = (lastItem.message as any).tool_calls;
  return !toolCalls || toolCalls.length === 0;
}
