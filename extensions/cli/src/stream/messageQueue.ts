import { EventEmitter } from "events";

import type { InputHistory } from "../util/inputHistory.js";
import { logger } from "../util/logger.js";

export interface QueuedMessage {
  message: string;
  imageMap?: Map<string, Buffer>;
  timestamp: number;
  history?: InputHistory;
  automationTaskId?: string;
}

export interface MessageProcessor {
  (message: string, imageMap?: Map<string, Buffer>): Promise<void>;
}

/**
 * A queue to store messages that need to be processed later.
 * Automation task identity is metadata, not text parsing state, so queued work
 * can be cancelled without disturbing ordinary chat messages.
 */
class MessageQueue extends EventEmitter {
  private queue: QueuedMessage[] = [];

  constructor() {
    super();
  }

  async enqueueMessage(
    message: string,
    imageMap?: Map<string, Buffer>,
    history?: InputHistory,
    automationTaskId?: string,
  ): Promise<boolean> {
    const queuedMessage: QueuedMessage = {
      message,
      imageMap,
      timestamp: Date.now(),
      history,
      automationTaskId,
    };

    this.queue.push(queuedMessage);
    logger.debug("MessageQueue: Message queued", {
      queueLength: this.queue.length,
      automationTaskId,
    });

    this.emit("messageQueued", queuedMessage);
    return true;
  }

  public getNextMessage(): QueuedMessage | undefined {
    return this.queue.shift();
  }

  removeAutomationTask(taskId: string): number {
    const before = this.queue.length;
    this.queue = this.queue.filter((item) => item.automationTaskId !== taskId);
    return before - this.queue.length;
  }

  getQueueLength(): number {
    return this.queue.length;
  }
}

export const messageQueue = new MessageQueue();
