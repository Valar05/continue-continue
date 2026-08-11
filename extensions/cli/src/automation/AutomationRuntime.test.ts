import { describe, expect, it, vi } from "vitest";

import {
  AutomationInputError,
  AutomationRuntime,
} from "./AutomationRuntime.js";

describe("AutomationRuntime", () => {
  it("creates domain-open Venice machine tasks and compiles the execution contract", () => {
    const runtime = new AutomationRuntime();
    const task = runtime.createTask({
      taskId: "venice-audio-001",
      domain: "audio",
      goal: "Render rain ambience and play it in the background.",
      requestedOutcome: "Audible background rain with a playback receipt.",
      preferredTools: ["media.create", "media.play"],
    });

    const prompt = runtime.renderTaskPrompt(task.taskId);

    expect(task.actor).toBe("venice");
    expect(task.status).toBe("queued");
    expect(prompt).toContain(
      '<continue-continue-machine-task id="venice-audio-001">',
    );
    expect(prompt).toContain("automation/orchestration layer");
    expect(prompt).toContain("Existing tool permission policy still controls");
    expect(prompt).toContain("BLOCKED");
  });

  it("accepts new routing domains instead of hard-coding media types", () => {
    const runtime = new AutomationRuntime();
    const task = runtime.createTask({
      domain: "shader_bake",
      goal: "Bake a material variant.",
    });

    expect(task.domain).toBe("shader_bake");
  });

  it("produces a bounded receipt from tool lifecycle evidence", () => {
    const changed = vi.fn();
    const runtime = new AutomationRuntime([], changed);
    const task = runtime.createTask({
      taskId: "venice-game-001",
      domain: "game",
      goal: "Build and smoke-test the prototype.",
      acceptanceCriteria: ["Build succeeds", "Smoke test receipt exists"],
    });

    runtime.markRunning(task.taskId);
    runtime.markToolStart(task.taskId, "run_terminal_command");
    runtime.markToolResult(task.taskId, "run_terminal_command", "completed");
    runtime.markCompleted(task.taskId, "Build and smoke test passed.");

    const receipt = runtime.getReceipt(task.taskId);

    expect(receipt?.status).toBe("completed");
    expect(receipt?.resultSummary).toContain("smoke test passed");
    expect(receipt?.toolEvents).toHaveLength(2);
    expect(changed).toHaveBeenCalled();
  });

  it("keeps permission blocking distinct from failure", () => {
    const runtime = new AutomationRuntime();
    const task = runtime.createTask({
      taskId: "venice-video-001",
      domain: "video",
      goal: "Render the current cut.",
    });

    runtime.markRunning(task.taskId);
    runtime.markBlocked(task.taskId, "render.video", "permission-123");

    expect(runtime.getTask(task.taskId)?.status).toBe("blocked");

    runtime.markPermissionResolved(task.taskId, "permission-123", true);
    expect(runtime.getTask(task.taskId)?.status).toBe("running");
  });

  it("rejects malformed task boundaries", () => {
    const runtime = new AutomationRuntime();

    expect(() =>
      runtime.createTask({
        domain: "Video Render",
        goal: "Render it",
      }),
    ).toThrow(AutomationInputError);

    expect(() =>
      runtime.createTask({
        domain: "video",
        goal: "   ",
      }),
    ).toThrow(AutomationInputError);
  });

  it("restores task records for long-lived serve sessions", () => {
    const first = new AutomationRuntime();
    const task = first.createTask({
      taskId: "venice-image-001",
      domain: "image",
      goal: "Generate a contact sheet.",
    });
    first.markRunning(task.taskId);

    const restored = new AutomationRuntime(first.listTasks());

    expect(restored.getTask(task.taskId)?.status).toBe("running");
    expect(restored.renderTaskPrompt(task.taskId)).toContain("contact sheet");
  });
});
