import type { ClientCommand, ClientFrame, ServerMessage } from '../types/game';

type MessageListener = (msg: ServerMessage) => void;
type StateListener = (connected: boolean) => void;

const BACKOFF_INITIAL = 1000;
const BACKOFF_MAX = 30000;
const PROTOCOL_VERSION = 1;
// 32 zero bytes as lowercase hex — mirrors `gaia-server/src/protocol.rs::SCHEMA_HASH`
// (fixed for now; automatic schema-hash derivation is out of scope).
const SCHEMA_HASH = '0'.repeat(64);
const HEX_COORD_PATTERN = /^-?\d+,-?\d+$/;

/**
 * Rust serializes `HexCoord` as the canonical "q,r" string so it can also
 * serve as a JSON object key. The UI keeps coordinates as `{ q, r }` for
 * ergonomic rendering, so the WebSocket boundary converts both directions.
 */
export function encodeHexCoordinates(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(encodeHexCoordinates);
  if (value === null || typeof value !== 'object') return value;

  const record = value as Record<string, unknown>;
  const keys = Object.keys(record);
  if (
    keys.length === 2 &&
    keys.includes('q') &&
    keys.includes('r') &&
    typeof record.q === 'number' &&
    typeof record.r === 'number'
  ) {
    return `${record.q},${record.r}`;
  }

  return Object.fromEntries(
    Object.entries(record).map(([key, entry]) => [key, encodeHexCoordinates(entry)]),
  );
}

export function decodeHexCoordinates(value: unknown): unknown {
  if (typeof value === 'string' && HEX_COORD_PATTERN.test(value)) {
    const [q, r] = value.split(',').map(Number);
    return { q, r };
  }
  if (Array.isArray(value)) return value.map(decodeHexCoordinates);
  if (value === null || typeof value !== 'object') return value;

  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>).map(([key, entry]) => [
      key,
      decodeHexCoordinates(entry),
    ]),
  );
}

export class GaiaWebSocket {
  private ws: WebSocket | null = null;
  private roomCode: string;
  private listeners: Set<MessageListener> = new Set();
  private stateListeners: Set<StateListener> = new Set();
  private queue: ClientFrame[] = [];
  private retryDelay = BACKOFF_INITIAL;
  private stopped = false;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(roomCode: string) {
    this.roomCode = roomCode;
  }

  connect(): void {
    this.stopped = false;
    this.openSocket();
  }

  private openSocket(): void {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${protocol}://${window.location.host}/ws/${this.roomCode}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.retryDelay = BACKOFF_INITIAL;
      this.notifyState(true);
      this.flushQueue();
    };

    this.ws.onmessage = (ev: MessageEvent) => {
      try {
        const msg = decodeHexCoordinates(JSON.parse(ev.data as string)) as ServerMessage;
        this.listeners.forEach((l) => l(msg));
      } catch {
        // ignore malformed messages
      }
    };

    this.ws.onclose = () => {
      this.notifyState(false);
      if (!this.stopped) {
        this.scheduleRetry();
      }
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  private scheduleRetry(): void {
    this.retryTimer = setTimeout(() => {
      this.retryDelay = Math.min(this.retryDelay * 2, BACKOFF_MAX);
      this.openSocket();
    }, this.retryDelay);
  }

  private flushQueue(): void {
    while (this.queue.length > 0) {
      const msg = this.queue.shift();
      if (msg) this.doSend(msg);
    }
  }

  private doSend(msg: ClientFrame): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(encodeHexCoordinates(msg)));
    }
  }

  send(msg: ClientFrame): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.doSend(msg);
    } else {
      this.queue.push(msg);
    }
  }

  /**
   * Sends a revisioned command, wrapping it in the envelope the server
   * expects: a fresh `command_id` (for idempotent retry — resending the same
   * envelope after a dropped ack replays the recorded outcome instead of
   * reapplying it) and the caller-supplied `expectedRevision` (for
   * optimistic concurrency — a stale value comes back as `command_rejected`
   * with `REVISION_CONFLICT`, not applied).
   */
  sendCommand(command: ClientCommand, expectedRevision: number): string {
    const commandId = crypto.randomUUID();
    this.send({
      type: 'command',
      protocol_version: PROTOCOL_VERSION,
      schema_hash: SCHEMA_HASH,
      room_id: this.roomCode,
      command_id: commandId,
      expected_revision: expectedRevision,
      command,
    });
    return commandId;
  }

  on(listener: MessageListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  onStateChange(listener: StateListener): () => void {
    this.stateListeners.add(listener);
    return () => this.stateListeners.delete(listener);
  }

  private notifyState(connected: boolean): void {
    this.stateListeners.forEach((l) => l(connected));
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  disconnect(): void {
    this.stopped = true;
    if (this.retryTimer !== null) {
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }
}
