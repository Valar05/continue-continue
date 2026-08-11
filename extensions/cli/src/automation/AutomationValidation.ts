import {
  AUTOMATION_RECEIPT_MARKER,
  AUTOMATION_TASK_MARKER,
  AutomationInputError,
  type AutomationAgentReceipt,
  type AutomationToolEvent,
} from "./AutomationTypes.js";

export const TASK_ID_RE = /^[A-Za-z0-9_.:-]{3,160}$/;
export const DOMAIN_RE = /^[a-z][a-z0-9_-]{1,63}$/;
const MAX_EVENTS = 64;
const MAX_CONTEXT_BYTES = 32 * 1024;

export function text(value: unknown, label: string, max = 8000): string {
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

export function optionalText(
  value: unknown,
  label: string,
  max = 8000,
): string | undefined {
  if (value === undefined || value === null || value === "") {
    return undefined;
  }
  return text(value, label, max);
}

export function stringList(
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

export function safeContext(
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

export function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value));
}

export function taskIdFromMessage(message: string): string | null {
  const marker = new RegExp(
    `<${AUTOMATION_TASK_MARKER}\\s+id="([A-Za-z0-9_.:-]{3,160})">`,
  );
  return message.match(marker)?.[1] ?? null;
}

export function lastEventSlice(
  events: AutomationToolEvent[],
): AutomationToolEvent[] {
  return events.slice(Math.max(0, events.length - MAX_EVENTS));
}

export function parseAgentReceipt(
  response: string,
): AutomationAgentReceipt | null {
  const marker = new RegExp(
    `<${AUTOMATION_RECEIPT_MARKER}>\\s*([\\s\\S]*?)\\s*</${AUTOMATION_RECEIPT_MARKER}>`,
  );
  const body = response.match(marker)?.[1];
  if (!body) return null;

  let parsed: unknown;
  try {
    parsed = JSON.parse(body);
  } catch {
    throw new AutomationInputError(
      "automation receipt marker contains invalid JSON",
    );
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new AutomationInputError("automation receipt must be an object");
  }
  const candidate = parsed as Record<string, unknown>;
  const status = candidate.status;
  if (
    !["completed", "blocked", "delegated", "failed"].includes(String(status))
  ) {
    throw new AutomationInputError("automation receipt has unsupported status");
  }
  return {
    status: status as AutomationAgentReceipt["status"],
    summary: text(candidate.summary, "receipt.summary", 12000),
    evidence: stringList(candidate.evidence, "receipt.evidence", 32, 2000),
    error: optionalText(candidate.error, "receipt.error", 4000),
    delegateTarget: optionalText(
      candidate.delegateTarget,
      "receipt.delegateTarget",
      500,
    ),
  };
}
