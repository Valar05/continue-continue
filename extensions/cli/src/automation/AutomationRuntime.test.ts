import { describe, expect, it, vi } from "vitest";

import {
  AUTOMATION_RECEIPT_MARKER,
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
    expect(prompt).toContain(AUTOMATION_RECEIPT_MARKER);
  });

  it("accepts future routing domains instead of hard-coding media types", () => {
    const runtime = new AutomationRuntime();
    const task = runtime.createTask({
      domain: "shader_bake",
      goal: "Bake a material variant.",
    });

    expect(task.domain).toBe("shader_bake");
  });

  it("only completes from an explicit receipt with evidence", () => {
    const changed = vi.fn();
    const runtime = new AutomationRuntime([], changed);
    const task = runtime.createTask({
      taskId: "venice-game-001",
      domain: "game",
      goal: "Build and smoke-test the prototype.",
      acceptanceCriteria: ["Build succeeds", "Smoke test receipt exists"],
    });

    runtime.markRunning(task.taskId);
    runtime.markToolStart(task.taskId, "Bash");
    runtime.markToolResult(task.taskId, "Bash", "completed");
    runtime.applyAgentResponse(
      task.taskId,
      `<${AUTOMATION_RECEIPT_MARKER}>{"status":"completed","summary":"Build and smoke test passed.","evidence":["build:exit=0","smoke:test=passed"]}</${AUTOMATION_RECEIPT_MARKER}>`,
    );

    const receipt = runtime.getReceipt(task.taskId);
    expect(receipt?.status).toBe("completed");
    expect(receipt?.evidence).toEqual(["build:exit=0", "smoke:test=passed"]);
    expect(receipt?.toolEvents).toHaveLength(2);
    expect(changed).toHaveBeenCalled();
  });

  it("refuses receiptless victory", () => {
    const runtime = new AutomationRuntime();
    const task = runtime.createTask({
      taskId: "venice-video-verify",
      domain: "video",
      goal: "Render a clip.",
    });

    runtime.markRunning(task.taskId);
    runtime.applyAgentResponse(task.taskId, "Done! Looks great.");
    expect(runtime.getTask(task.taskId)?.status).toBe("awaiting_verification");
    expect(runtime.getReceipt(task.taskId)).toBeUndefined();

    runtime.applyAgentResponse(
      task.taskId,
      `<${AUTOMATION_RECEIPT_MARKER}>{"status":"completed","summary":"Rendered.","evidence":[]}</${AUTOMATION_RECEIPT_MARKER}>`,
    );
    expect(runtime.getTask(task.taskId)?.status).toBe("awaiting_verification");
  });

  it("keeps permission blocking distinct from capability blocking", () => {
    const runtime = new AutomationRuntime();
    const task = runtime.createTask({
      taskId: "venice-video-001",
      domain: "video",
      goal: "Render the current cut.",
    });

    runtime.markRunning(task.taskId);
    runtime.markPermissionBlocked(
      task.taskId,
      "render.video",
      "permission-123",
    );
    expect(runtime.getTask(task.taskId)?.status).toBe("blocked_permission");

    runtime.markPermissionResolved(task.taskId, "permission-123", true);
    expect(runtime.getTask(task.taskId)?.status).toBe("running");
  });

  it("records delegation without laundering it into completion", () => {
    const runtime = new AutomationRuntime();
    const task = runtime.createTask({
      taskId: "vlad-render-001",
      actor: "vlad",
      domain: "video",
      goal: "Render the heavy scene.",
    });

    runtime.markRunning(task.taskId);
    runtime.applyAgentResponse(
      task.taskId,
      `<${AUTOMATION_RECEIPT_MARKER}>{"status":"delegated","summary":"Sent to the full runtime.","evidence":["upstream-task:vlad-render-001"],"delegateTarget":"continue-continue-full"}</${AUTOMATION_RECEIPT_MARKER}>`,
    );

    expect(runtime.getTask(task.taskId)?.status).toBe("delegated");
    expect(runtime.getReceipt(task.taskId)?.status).toBe("delegated");
    expect(runtime.getReceipt(task.taskId)?.delegateTarget).toBe(
      "continue-continue-full",
    );
  });

  it("rejects malformed task boundaries", () => {
    const runtime = new AutomationRuntime();

    expect(() =>
      runtime.createTask({ domain: "Video Render", goal: "Render it" }),
    ).toThrow(AutomationInputError);
    expect(() => runtime.createTask({ domain: "video", goal: "   " })).toThrow(
      AutomationInputError,
    );
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
