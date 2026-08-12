import { randomUUID } from "node:crypto";

import {
  AUTOMATION_RECEIPT_MARKER,
  AUTOMATION_TASK_MARKER,
  AutomationInputError,
  type AutomationAgentReceipt,
  type AutomationReceipt,
  type AutomationReceiptStatus,
  type AutomationSnapshot,
  type AutomationTaskInput,
  type AutomationTaskRecord,
  type AutomationToolEvent,
} from "./AutomationTypes.js";
import {
  clone,
  DOMAIN_RE,
  lastEventSlice,
  optionalText,
  parseAgentReceipt,
  safeContext,
  stringList,
  TASK_ID_RE,
  taskIdFromMessage,
  text,
} from "./AutomationValidation.js";

export {
  AUTOMATION_RECEIPT_MARKER,
  AUTOMATION_TASK_MARKER,
  AutomationInputError,
} from "./AutomationTypes.js";
export type {
  AutomationAgentReceipt,
  AutomationReceipt,
  AutomationReceiptStatus,
  AutomationSnapshot,
  AutomationTaskInput,
  AutomationTaskRecord,
  AutomationTaskStatus,
  AutomationToolEvent,
} from "./AutomationTypes.js";

export class AutomationRuntime {
  private tasks = new Map<string, AutomationTaskRecord>();

  constructor(
    initialTasks: AutomationTaskRecord[] = [],
    private readonly onChange?: (tasks: AutomationTaskRecord[]) => void,
  ) {
    for (const candidate of initialTasks) {
      if (candidate?.taskId && TASK_ID_RE.test(candidate.taskId)) {
        const restored = clone(candidate);
        restored.evidence ??= [];
        restored.toolEvents ??= [];
        this.tasks.set(candidate.taskId, restored);
      }
    }
  }

  createTask(input: AutomationTaskInput): AutomationTaskRecord {
    const taskId = input.taskId?.trim() || randomUUID();
    if (!TASK_ID_RE.test(taskId)) {
      throw new AutomationInputError(
        "taskId must be 3-160 safe identifier characters",
      );
    }
    if (this.tasks.has(taskId)) {
      throw new AutomationInputError(`task ${taskId} already exists`);
    }

    const domain = text(input.domain, "domain", 64).toLowerCase();
    if (!DOMAIN_RE.test(domain)) {
      throw new AutomationInputError(
        "domain must be a lowercase routing slug such as audio, image, video, game, code, or system",
      );
    }

    const goal = text(input.goal, "goal");
    const actor = optionalText(input.actor, "actor", 120) ?? "venice";
    const requestedOutcome =
      optionalText(input.requestedOutcome, "requestedOutcome") ?? goal;
    const acceptanceCriteria = stringList(
      input.acceptanceCriteria,
      "acceptanceCriteria",
      32,
      1200,
    );
    if (!acceptanceCriteria.length) {
      acceptanceCriteria.push(
        "Return a truthful receipt naming the delivered artifact/result or the exact blocking boundary.",
      );
    }

    const priority = input.priority ?? "normal";
    if (!["low", "normal", "high"].includes(priority)) {
      throw new AutomationInputError("priority must be low, normal, or high");
    }

    const now = Date.now();
    const record: AutomationTaskRecord = {
      taskId,
      actor,
      domain,
      goal,
      requestedOutcome,
      acceptanceCriteria,
      constraints: stringList(input.constraints, "constraints", 32, 1200),
      preferredTools: stringList(
        input.preferredTools,
        "preferredTools",
        32,
        240,
      ),
      lane: optionalText(input.lane, "lane", 160),
      priority,
      context: safeContext(input.context),
      status: "queued",
      cancelRequested: false,
      createdAt: now,
      updatedAt: now,
      evidence: [],
      toolEvents: [],
    };

    this.tasks.set(taskId, record);
    this.changed();
    return clone(record);
  }

  listTasks(): AutomationTaskRecord[] {
    return [...this.tasks.values()]
      .sort((a, b) => a.createdAt - b.createdAt)
      .map(clone);
  }

  getTask(taskId: string): AutomationTaskRecord | undefined {
    const task = this.tasks.get(taskId);
    return task ? clone(task) : undefined;
  }

  getReceipt(taskId: string): AutomationReceipt | undefined {
    const receipt = this.tasks.get(taskId)?.receipt;
    return receipt ? clone(receipt) : undefined;
  }

  renderTaskPrompt(taskId: string): string {
    const task = this.requireTask(taskId);
    const payload = {
      taskId: task.taskId,
      actor: task.actor,
      domain: task.domain,
      lane: task.lane,
      priority: task.priority,
      goal: task.goal,
      requestedOutcome: task.requestedOutcome,
      acceptanceCriteria: task.acceptanceCriteria,
      constraints: task.constraints,
      preferredTools: task.preferredTools,
      context: task.context,
    };

    return `<${AUTOMATION_TASK_MARKER} id="${task.taskId}">
${JSON.stringify(payload, null, 2)}

EXECUTION CONTRACT
- This is a machine task. Preserve the requested outcome, actor, lane, constraints, evidence standard, and delivery surface.
- Continue Continue is the automation/orchestration layer. Connected MCP tools, terminal commands, media systems, game engines, renderers, phone hands, and other executors are specialized organs underneath it.
- The domain is routing metadata, not a wall. A game task may legitimately use code, image, audio, video, build, test, and system tools in one plan.
- Prefer the named tools when they fit, but never substitute an adjacent tool or artifact merely because it is easier.
- Existing tool permission policy still controls execution. This task envelope does not grant new authority.
- If a required executor or capability is unavailable, stop at that boundary. Do not counterfeit completion.
- Completion requires the requested result plus observable evidence.
- End the machine turn with exactly one machine-readable receipt marker:
<${AUTOMATION_RECEIPT_MARKER}>{"status":"completed|blocked|delegated|failed","summary":"...","evidence":["artifact id/path/url/hash/runtime observation/tool receipt"],"error":"optional","delegateTarget":"optional"}</${AUTOMATION_RECEIPT_MARKER}>
- status=completed requires at least one evidence item. If evidence is not yet sufficient, do not claim completed.
- status=delegated means responsibility moved to another executor; it is not completion of the requested outcome.
</${AUTOMATION_TASK_MARKER}>`;
  }

  extractTaskId(message: string): string | null {
    return taskIdFromMessage(message);
  }

  shouldSkip(taskId: string): boolean {
    const task = this.tasks.get(taskId);
    return (
      !task ||
      task.cancelRequested ||
      ["completed", "blocked", "failed", "cancelled", "delegated"].includes(
        task.status,
      )
    );
  }

  markRunning(taskId: string): void {
    this.mutate(taskId, (task) => {
      if (task.status === "cancelled") return;
      task.status = "running";
      task.startedAt ??= Date.now();
      task.pendingPermissionRequestId = undefined;
    });
  }

  markToolStart(taskId: string, toolName: string): void {
    this.mutate(taskId, (task) => {
      task.currentTool = toolName;
      this.pushEvent(task, {
        at: Date.now(),
        kind: "tool_start",
        toolName,
      });
    });
  }

  markToolResult(taskId: string, toolName: string, status: string): void {
    this.mutate(taskId, (task) => {
      task.currentTool = undefined;
      this.pushEvent(task, {
        at: Date.now(),
        kind: "tool_result",
        toolName,
        status,
      });
    });
  }

  markToolError(
    taskId: string,
    toolName: string | undefined,
    detail: string,
  ): void {
    this.mutate(taskId, (task) => {
      task.currentTool = undefined;
      this.pushEvent(task, {
        at: Date.now(),
        kind: "tool_error",
        toolName,
        detail: detail.slice(0, 1200),
      });
    });
  }

  markPermissionBlocked(
    taskId: string,
    toolName: string,
    requestId: string,
  ): void {
    this.mutate(taskId, (task) => {
      task.status = "blocked_permission";
      task.currentTool = toolName;
      task.pendingPermissionRequestId = requestId;
      this.pushEvent(task, {
        at: Date.now(),
        kind: "permission_required",
        toolName,
        requestId,
      });
    });
  }

  markPermissionResolved(
    taskId: string,
    requestId: string,
    approved: boolean,
  ): void {
    this.mutate(taskId, (task) => {
      task.pendingPermissionRequestId = undefined;
      this.pushEvent(task, {
        at: Date.now(),
        kind: "permission_resolved",
        requestId,
        status: approved ? "approved" : "rejected",
      });
      if (approved) {
        task.status = "running";
      } else {
        task.error = "Required tool permission was rejected.";
        this.finish(task, "blocked");
      }
    });
  }

  markPaused(taskId: string): void {
    this.mutate(taskId, (task) => {
      if (task.status !== "cancelled") {
        task.status = "awaiting_verification";
      }
    });
  }

  markAwaitingVerification(
    taskId: string,
    resultSummary?: string,
    evidence: string[] = [],
  ): void {
    this.mutate(taskId, (task) => {
      task.status = "awaiting_verification";
      task.resultSummary = resultSummary?.trim().slice(0, 12000);
      task.evidence = stringList(evidence, "evidence", 32, 2000);
    });
  }

  requestCancel(taskId: string): AutomationTaskRecord {
    this.mutate(taskId, (task) => {
      task.cancelRequested = true;
      if (task.status !== "running" && task.status !== "blocked_permission") {
        this.finish(task, "cancelled");
      }
    });
    return this.getTask(taskId)!;
  }

  markCancelled(taskId: string): void {
    this.mutate(taskId, (task) => this.finish(task, "cancelled"));
  }

  applyAgentResponse(taskId: string, response: string): AutomationTaskRecord {
    let receipt: AutomationAgentReceipt | null = null;
    try {
      receipt = parseAgentReceipt(response);
    } catch (error) {
      this.markAwaitingVerification(
        taskId,
        `Agent returned an invalid machine receipt: ${error instanceof Error ? error.message : String(error)}`,
      );
      return this.getTask(taskId)!;
    }

    if (!receipt) {
      this.markAwaitingVerification(
        taskId,
        response.trim().slice(0, 12000) ||
          "Agent turn ended without a machine receipt.",
      );
      return this.getTask(taskId)!;
    }

    if (receipt.status === "completed" && !receipt.evidence?.length) {
      this.markAwaitingVerification(taskId, receipt.summary, []);
      return this.getTask(taskId)!;
    }

    this.mutate(taskId, (task) => {
      task.resultSummary = receipt.summary;
      task.evidence = receipt.evidence ?? [];
      task.error = receipt.error;
      task.delegateTarget = receipt.delegateTarget;

      if (receipt.status === "delegated") {
        this.pushEvent(task, {
          at: Date.now(),
          kind: "delegated",
          detail: receipt.delegateTarget ?? receipt.summary,
        });
      }

      this.finish(task, receipt.status);
    });
    return this.getTask(taskId)!;
  }

  markFailed(taskId: string, error: string): void {
    this.mutate(taskId, (task) => {
      task.error = error.slice(0, 4000);
      this.finish(task, "failed");
    });
  }

  snapshot(activeTaskId: string | null = null): AutomationSnapshot {
    return {
      activeTaskId,
      tasks: this.listTasks(),
    };
  }

  private requireTask(taskId: string): AutomationTaskRecord {
    const task = this.tasks.get(taskId);
    if (!task) {
      throw new AutomationInputError(`task ${taskId} was not found`);
    }
    return task;
  }

  private mutate(
    taskId: string,
    fn: (task: AutomationTaskRecord) => void,
  ): void {
    const task = this.requireTask(taskId);
    fn(task);
    task.updatedAt = Date.now();
    this.changed();
  }

  private pushEvent(
    task: AutomationTaskRecord,
    event: AutomationToolEvent,
  ): void {
    task.toolEvents = lastEventSlice([...task.toolEvents, event]);
  }

  private finish(
    task: AutomationTaskRecord,
    status: AutomationReceiptStatus,
  ): void {
    const completedAt = Date.now();
    task.status = status;
    task.cancelRequested = status === "cancelled";
    task.currentTool = undefined;
    task.pendingPermissionRequestId = undefined;
    task.completedAt = completedAt;
    task.receipt = {
      taskId: task.taskId,
      actor: task.actor,
      domain: task.domain,
      status,
      requestedOutcome: task.requestedOutcome,
      acceptanceCriteria: [...task.acceptanceCriteria],
      resultSummary: task.resultSummary,
      evidence: [...task.evidence],
      error: task.error,
      delegateTarget: task.delegateTarget,
      toolEvents: clone(task.toolEvents),
      createdAt: task.createdAt,
      startedAt: task.startedAt,
      completedAt,
    };
  }

  private changed(): void {
    this.onChange?.(this.listTasks());
  }
}
