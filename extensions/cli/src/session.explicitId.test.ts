import fs from "fs";
import os from "os";
import path from "path";

import {
  createSession,
  getCurrentSession,
  loadSession,
  startNewSession,
  updateSessionHistory,
} from "./session.js";
import { validateFlags } from "./flags/flagValidator.js";

describe("explicit persistent session identity", () => {
  let tempRoot: string;
  const oldGlobalDir = process.env.CONTINUE_GLOBAL_DIR;
  const oldSessionId = process.env.CONTINUE_CLI_SESSION_ID;
  const oldLegacySessionId = process.env.CONTINUE_CLI_TEST_SESSION_ID;

  beforeEach(() => {
    tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "continue-session-id-"));
    process.env.CONTINUE_GLOBAL_DIR = tempRoot;
    delete process.env.CONTINUE_CLI_SESSION_ID;
    delete process.env.CONTINUE_CLI_TEST_SESSION_ID;
    startNewSession([]);
  });

  afterEach(() => {
    if (oldGlobalDir === undefined) delete process.env.CONTINUE_GLOBAL_DIR;
    else process.env.CONTINUE_GLOBAL_DIR = oldGlobalDir;
    if (oldSessionId === undefined) delete process.env.CONTINUE_CLI_SESSION_ID;
    else process.env.CONTINUE_CLI_SESSION_ID = oldSessionId;
    if (oldLegacySessionId === undefined)
      delete process.env.CONTINUE_CLI_TEST_SESSION_ID;
    else process.env.CONTINUE_CLI_TEST_SESSION_ID = oldLegacySessionId;
    fs.rmSync(tempRoot, { recursive: true, force: true });
  });

  it("creates the exact requested session instead of falling back to newest", () => {
    createSession([], "unrelated-newest");
    updateSessionHistory([
      { message: { role: "user", content: "unrelated" } } as any,
    ]);
    startNewSession([]);

    process.env.CONTINUE_CLI_SESSION_ID = "vlad-worker-a";
    const session = loadSession();

    expect(session?.sessionId).toBe("vlad-worker-a");
    expect(session?.history).toEqual([]);
    expect(getCurrentSession().sessionId).toBe("vlad-worker-a");
  });

  it("loads history from the exact requested persistent session", () => {
    createSession([], "vlad-worker-persisted");
    updateSessionHistory([
      { message: { role: "user", content: "first turn" } } as any,
    ]);
    startNewSession([]);

    process.env.CONTINUE_CLI_SESSION_ID = "vlad-worker-persisted";
    const session = loadSession();

    expect(session?.sessionId).toBe("vlad-worker-persisted");
    expect(session?.history).toHaveLength(1);
    expect(session?.history[0].message.content).toBe("first turn");
  });

  it("keeps the legacy cn ls selector exact as well", () => {
    process.env.CONTINUE_CLI_TEST_SESSION_ID = "selected-from-ls";
    const session = loadSession();
    expect(session?.sessionId).toBe("selected-from-ls");
  });

  it("rejects unsafe session identifiers", () => {
    process.env.CONTINUE_CLI_SESSION_ID = "../../escape";
    expect(loadSession()).toBeNull();
  });
});

describe("--session-id validation", () => {
  it("requires headless print mode", () => {
    const result = validateFlags({ sessionId: "vlad-worker-a", print: false });
    expect(result.isValid).toBe(false);
    expect(result.errors.some((x) => x.code === "SESSION_ID_REQUIRES_PRINT")).toBe(true);
  });

  it("conflicts with legacy resume", () => {
    const result = validateFlags({
      sessionId: "vlad-worker-a",
      resume: true,
      print: true,
    });
    expect(result.isValid).toBe(false);
    expect(result.errors.some((x) => x.code === "CONFLICTING_SESSION_FLAGS")).toBe(true);
  });

  it("accepts an exact headless session id", () => {
    const result = validateFlags({ sessionId: "vlad-worker-a", print: true });
    expect(result.isValid).toBe(true);
  });
});
