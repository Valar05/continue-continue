import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import type { AutomationTaskRecord } from "./AutomationRuntime.js";

function automationDir(): string {
  const root =
    process.env.CONTINUE_GLOBAL_DIR || path.join(os.homedir(), ".continue");
  return path.join(root, "automation", "tasks");
}

function safeTaskFile(taskId: string): string {
  return path.join(automationDir(), `${taskId}.json`);
}

export class AutomationTaskStore {
  loadAll(): AutomationTaskRecord[] {
    const dir = automationDir();
    if (!fs.existsSync(dir)) return [];

    const tasks: AutomationTaskRecord[] = [];
    for (const name of fs.readdirSync(dir).filter((entry) => entry.endsWith(".json"))) {
      try {
        const parsed = JSON.parse(
          fs.readFileSync(path.join(dir, name), "utf8"),
        ) as AutomationTaskRecord;
        if (parsed?.taskId) tasks.push(parsed);
      } catch {
        // One corrupt task must not erase the rest of the automation ledger.
      }
    }
    return tasks.sort((a, b) => a.createdAt - b.createdAt);
  }

  saveAll(tasks: AutomationTaskRecord[]): void {
    const dir = automationDir();
    fs.mkdirSync(dir, { recursive: true });
    for (const task of tasks) {
      const target = safeTaskFile(task.taskId);
      const temp = `${target}.${process.pid}.tmp`;
      fs.writeFileSync(temp, `${JSON.stringify(task, null, 2)}\n`, "utf8");
      fs.renameSync(temp, target);
    }
  }
}
