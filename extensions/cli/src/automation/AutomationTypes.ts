export const AUTOMATION_TASK_MARKER = "continue-continue-machine-task";
export const AUTOMATION_RECEIPT_MARKER = "continue-continue-receipt";

export type AutomationTaskStatus =
  | "queued"
  | "running"
  | "blocked_permission"
  | "awaiting_verification"
  | "delegated"
  | "completed"
  | "blocked"
  | "failed"
  | "cancelled";

export type AutomationReceiptStatus =
  | "completed"
  | "blocked"
  | "delegated"
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
    | "permission_resolved"
    | "delegated";
  toolName?: string;
  status?: string;
  detail?: string;
  requestId?: string;
}

export interface AutomationAgentReceipt {
  status: "completed" | "blocked" | "delegated" | "failed";
  summary: string;
  evidence?: string[];
  error?: string;
  delegateTarget?: string;
}

export interface AutomationReceipt {
  taskId: string;
  actor: string;
  domain: string;
  status: AutomationReceiptStatus;
  requestedOutcome: string;
  acceptanceCriteria: string[];
  resultSummary?: string;
  evidence: string[];
  error?: string;
  delegateTarget?: string;
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
  evidence: string[];
  error?: string;
  delegateTarget?: string;
  toolEvents: AutomationToolEvent[];
  receipt?: AutomationReceipt;
}

export interface AutomationSnapshot {
  activeTaskId: string | null;
  tasks: AutomationTaskRecord[];
}

export class AutomationInputError extends Error {}
