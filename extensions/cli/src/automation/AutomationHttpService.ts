import type { Express, Request, Response } from "express";

import {
  AutomationInputError,
  type AutomationRuntime,
  type AutomationTaskInput,
} from "./AutomationRuntime.js";

export interface AutomationHttpCapabilities {
  runtime: "full" | "vlad-edge";
  domains: "open";
  builtInTools?: string[];
  mcp?: Array<{ server: string; tools: string[] }>;
  notes?: string[];
}

export interface AutomationHttpHooks {
  enqueue(taskId: string, prompt: string): Promise<void>;
  cancelQueued(taskId: string): number;
  activeTaskId(): string | null;
  abortActive(taskId: string): boolean;
  capabilities(): AutomationHttpCapabilities;
}

function taskId(req: Request): string {
  return String(req.params.taskId || "");
}

export function registerAutomationRoutes(
  app: Express,
  runtime: AutomationRuntime,
  hooks: AutomationHttpHooks,
): void {
  app.get("/automation/capabilities", (_req: Request, res: Response) => {
    res.json(hooks.capabilities());
  });

  app.get("/automation/tasks", (_req: Request, res: Response) => {
    res.json(runtime.snapshot(hooks.activeTaskId()));
  });

  app.post("/automation/tasks", async (req: Request, res: Response) => {
    try {
      const task = runtime.createTask(req.body as AutomationTaskInput);
      await hooks.enqueue(task.taskId, runtime.renderTaskPrompt(task.taskId));
      res.status(202).json({ queued: true, task: runtime.getTask(task.taskId) });
    } catch (error) {
      const status = error instanceof AutomationInputError ? 400 : 500;
      res.status(status).json({
        error: error instanceof Error ? error.message : String(error),
      });
    }
  });

  app.get("/automation/tasks/:taskId", (req: Request, res: Response) => {
    const task = runtime.getTask(taskId(req));
    if (!task) return res.status(404).json({ error: "task not found" });
    res.json(task);
  });

  app.get(
    "/automation/tasks/:taskId/receipt",
    (req: Request, res: Response) => {
      const id = taskId(req);
      const task = runtime.getTask(id);
      if (!task) return res.status(404).json({ error: "task not found" });
      const receipt = runtime.getReceipt(id);
      if (!receipt) {
        return res.status(409).json({
          error: "task does not have a terminal receipt",
          status: task.status,
        });
      }
      res.json(receipt);
    },
  );

  app.post(
    "/automation/tasks/:taskId/cancel",
    (req: Request, res: Response) => {
      const id = taskId(req);
      if (!runtime.getTask(id)) {
        return res.status(404).json({ error: "task not found" });
      }
      const removed = hooks.cancelQueued(id);
      const aborted = hooks.abortActive(id);
      const task = runtime.requestCancel(id);
      if (aborted) runtime.markCancelled(id);
      res.json({ removedFromQueue: removed, aborted, task: runtime.getTask(id) ?? task });
    },
  );
}
