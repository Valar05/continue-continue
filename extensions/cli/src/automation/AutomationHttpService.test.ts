import express from "express";
import request from "supertest";
import { describe, expect, it, vi } from "vitest";

import { registerAutomationRoutes } from "./AutomationHttpService.js";
import { AutomationRuntime } from "./AutomationRuntime.js";

describe("AutomationHttpService", () => {
  function harness() {
    const app = express();
    app.use(express.json());
    const runtime = new AutomationRuntime();
    const enqueue = vi.fn(async () => {});
    const cancelQueued = vi.fn(() => 1);
    const abortActive = vi.fn(() => false);
    registerAutomationRoutes(app, runtime, {
      enqueue,
      cancelQueued,
      abortActive,
      activeTaskId: () => null,
      capabilities: () => ({
        runtime: "full",
        domains: "open",
        builtInTools: ["Bash"],
      }),
    });
    return { app, runtime, enqueue, cancelQueued };
  }

  it("queues a typed machine task without granting tool permission", async () => {
    const { app, enqueue } = harness();
    const response = await request(app).post("/automation/tasks").send({
      taskId: "venice-http-001",
      domain: "audio",
      goal: "Render ambience.",
      preferredTools: ["media.create"],
    });

    expect(response.status).toBe(202);
    expect(response.body.task.status).toBe("queued");
    expect(enqueue).toHaveBeenCalledOnce();
    expect(enqueue.mock.calls[0][1]).toContain(
      "Existing tool permission policy still controls execution",
    );
  });

  it("returns 409 until a terminal evidence receipt exists", async () => {
    const { app, runtime } = harness();
    const task = runtime.createTask({
      taskId: "venice-http-002",
      domain: "video",
      goal: "Render clip.",
    });

    let response = await request(app).get(
      `/automation/tasks/${task.taskId}/receipt`,
    );
    expect(response.status).toBe(409);

    runtime.markRunning(task.taskId);
    runtime.applyAgentResponse(
      task.taskId,
      '<continue-continue-receipt>{"status":"completed","summary":"Rendered","evidence":["artifact:clip.mp4"]}</continue-continue-receipt>',
    );
    response = await request(app).get(
      `/automation/tasks/${task.taskId}/receipt`,
    );
    expect(response.status).toBe(200);
    expect(response.body.evidence).toEqual(["artifact:clip.mp4"]);
  });

  it("cancels queued work by automation task identity", async () => {
    const { app, runtime, cancelQueued } = harness();
    const task = runtime.createTask({
      taskId: "venice-http-003",
      domain: "game",
      goal: "Build prototype.",
    });

    const response = await request(app).post(
      `/automation/tasks/${task.taskId}/cancel`,
    );
    expect(response.status).toBe(200);
    expect(cancelQueued).toHaveBeenCalledWith(task.taskId);
    expect(response.body.task.status).toBe("cancelled");
  });
});
