import { randomUUID } from "node:crypto";

export const AUTOMATION_TASK_MARKER = "continue-continue-machine-task";

export type AutomationTaskStatus =
  | "queued"
  | "running"
  | "blocked"
  | "paused"
  | "completed"
  | "failed"
  | "cancelled";

export interface AutomationTaskInput {
  taskId?: string;
  actor?: string;
  domain: string;
  goal: string;
  requestedOutcome?: string;
  acceptanceCriteria?: string[];
  constraints?: string[];
  preferredTools?: string[];
  lane?: string;
  priority?: "low" | "normal" | "high";
  context?: Record<string, unknown>;
}

export interface AutomationToolEvent {
  at: number;
  kind:
    | "tool_start"
    | "tool_result"
    | "tool_error"
    | "permission_required"
    | "permission_resolved";
  toolName?: string;
  status?: string;
  detail?: string;
  requestId?: string;
}

export interface AutomationReceipt {
  taskId: string;
  actor: string;
  domain: string;
  status: Extract<
    AutomationTaskStatus,
    "completed" | "failed" | "cancelled"
  >;
  requestedOutcome: string;
  acceptanceCriteria: string[];
  resultSummary?: string;
  error?: string;
  toolEvents: AutomationToolEvent[];
  createdAt: number;
  startedAt?: number;
  completedAt: number;
}

export interface AutomationTaskRecord {
  taskId: string;
  actor: string;
  domain: string;
  goal: string;
  requestedOutcome: string;
  acceptanceCriteria: string[];
  constraints: string[];
  preferredTools: string[];
  lane?: string;
  priority: "low" | "normal" | "high";
  context?: Record<string, unknown>;
  status: AutomationTaskStatus;
  cancelRequested: boolean;
  createdAt: number;
  updatedAt: number;
  startedAt?: number;
  completedAt?: number;
  currentTool?: string;
  pendingPermissionRequestId?: string;
  resultSummary?: string;
  error?: string;
  toolEvents: AutomationToolEvent[];
  receipt?: AutomationReceipt;
}

export interface AutomationSnapshot {
  activeTaskId: string | null;
  tasks: AutomationTaskRecord[];
}

export class AutomationInputError extends Error {}

const TASK_ID_RE = /^[A-Za-z0-9_.:-]{3,160}$/;
const DOMAIN_RE = /^[a-z][a-z0-9_-]{1,63}$/;
const MAX_EVENTS = 64;
const MAX_CONTEXT_BYTES = 32 * 1024;

function text(value: unknown, label: string, max = 8000): string {
  if (typeof value !== "string") {
    throw new AutomationInputError(`${label} must be a string`);
  }
  const cleaned = value.trim();
  if (!cleaned) {
    throw new AutomationInputError(`${label} is required`);
  }
  if (cleaned.length > max) {
    throw new AutomationInputError(`${label} exceeds ${max} characters`);
  }
  return cleaned;
}

function optionalText(
  value: unknown,
  label: string,
  max = 8000,
): string | undefined {
  if (value === undefined || value === null || value === "") {
    return undefined;
  }
  return text(value, label, max);
}

function stringList(
  value: unknown,
  label: string,
  maxItems = 32,
  maxItemLength = 1000,
): string[] {
  if (value === undefined || value === null) {
    return [];
  }
  if (!Array.isArray(value)) {
    throw new AutomationInputError(`${label} must be an array of strings`);
  }
  if (value.length > maxItems) {
    throw new AutomationInputError(`${label} exceeds ${maxItems} items`);
  }
  return value.map((item, index) =>
    text(item, `${label}[${index}]`, maxItemLength),
  );
}

function safeContext(
  value: unknown,
): Record<string, unknown> | undefined {
  if (value === undefined || value === null) {
    return undefined;
  }
  if (typeof value !== "object" || Array.isArray(value)) {
    throw new AutomationInputError("context must be an object");
  }
  const encoded = JSON.stringify(value);
  if (Buffer.byteLength(encoded, "utf8") > MAX_CONTEXT_BYTES) {
    throw new AutomationInputError(
      `context exceeds ${MAX_CONTEXT_BYTES} bytes`,
    );
  }
  return JSON.parse(encoded);
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value));
}

function taskIdFromMessage(message: string): string | null {
  const marker = new RegExp(
    `<${AUTOMATION_TASK_MARKER}\\s+id="([A-Za-z0-9_.:-]{3,160})">`,
  );
  return message.match(marker)?.[1] ?? null;
}

function lastEventSlice(
  events: AutomationToolEvent[],
): AutomationToolEvent[] {
  return events.slice(Math.max(0, events.length - MAX_EVENTS));
}

export class AutomationRuntime {
  private tasks = new Map<string, AutomationTaskRecord>();

  constructor(
    initialTasks: AutomationTaskRecord[] = [],
    private readonly onChange?: (tasks: AutomationTaskRecord[]) => void,
  ) {
    for (const candidate of initialTasks) {
      if (candidate?.taskId && TASK_ID_RE.test(candidate.taskId)) {
        this.tasks.set(candidate.taskId, clone(candidate));
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
- Continue Continue is the automation/orchestration layer. Connected MCP tools, terminal commands, media systems, game engines, renderers, and other executors are specialized organs underneath it.
- The domain is routing metadata, not a wall. A game task may legitimately use code, image, audio, video, build, test, and system tools in one plan.
- Prefer the named tools when they fit, but never substitute an adjacent tool or artifact merely because it is easier.
- Existing tool permission policy still controls execution. This task envelope does not grant new authority.
- If a required executor or capability is unavailable, stop at that boundary and report BLOCKED with the missing capability. Do not counterfeit completion.
- Completion requires the requested result plus observable evidence. Return enough artifact identifiers, paths/URLs, hashes, runtime observations, or tool receipts for another agent or human to challenge the claim.
</${AUTOMATION_TASK_MARKER}>`;
  }

  extractTaskId(message: string): string | null {
    return taskIdFromMessage(message);
  }

  shouldSkip(taskId: string): boolean {
    const task = this.tasks.get(taskId);
    return !task || task.cancelRequested || task.status === "cancelled";
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

  markToolResult(
    taskId: string,
    toolName: string,
    status: string,
  ): void {
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

  markBlocked(
    taskId: string,
    toolName: string,
    requestId: string,
  ): void {
    this.mutate(taskId, (task) => {
      task.status = "blocked";
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
      task.status = "running";
      task.pendingPermissionRequestId = undefined;
      this.pushEvent(task, {
        at: Date.now(),
        kind: "permission_resolved",
        requestId,
        status: approved ? "approved" : "rejected",
      });
    });
  }

  markPaused(taskId: string): void {
    this.mutate(taskId, (task) => {
      if (task.status !== "cancelled") {
        task.status = "paused";
      }
    });
  }

  requestCancel(taskId: string): AutomationTaskRecord {
    this.mutate(taskId, (task) => {
      task.cancelRequested = true;
      if (task.status !== "running") {
        this.finish(task, "cancelled");
      }
    });
    return this.getTask(taskId)!;
  }

  markCancelled(taskId: string): void {
    this.mutate(taskId, (task) => this.finish(task, "cancelled"));
  }

  markCompleted(taskId: string, resultSummary?: string): void {
    this.mutate(taskId, (task) => {
      task.resultSummary = resultSummary?.trim().slice(0, 12000);
      this.finish(task, "completed");
    });
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
    status: "completed" | "failed" | "cancelled",
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
      error: task.error,
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
