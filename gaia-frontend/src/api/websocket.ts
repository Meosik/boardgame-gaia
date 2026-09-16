import type { ClientCommand, ClientFrame, ServerMessage } from '../types/game';

type MessageListener = (msg: ServerMessage) => void;
type StateListener = (connected: boolean) => void;
export interface CommandState { ready: boolean; pending: boolean }
type CommandStateListener = (state: CommandState) => void;

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
  private joinFrame: Extract<ClientFrame, { type: 'join_room' }> | null = null;
  private joinSent = false;
  private ready = false;
  private latestSnapshotRevision = -1;
  private pendingCommands = new Map<string, Extract<ClientFrame, { type: 'command' }>>();
  private commandStateListeners = new Set<CommandStateListener>();
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
    const socket = new WebSocket(url);
    this.ws = socket;
    this.joinSent = false;
    this.ready = false;

    socket.onopen = () => {
      if (this.ws !== socket || this.stopped) return;
      this.retryDelay = BACKOFF_INITIAL;
      this.sendJoin();
      this.notifyState(true);
    };

    socket.onmessage = (ev: MessageEvent) => {
      if (this.ws !== socket || this.stopped) return;
      try {
        const msg = decodeHexCoordinates(JSON.parse(ev.data as string)) as ServerMessage;
        if (msg.type === 'snapshot') {
          // Replaying a recorded outcome can broadcast a snapshot tagged with its old revision.
          if (msg.revision < this.latestSnapshotRevision) return;
          this.latestSnapshotRevision = msg.revision;
        }
        if (msg.type === 'room_joined' && this.joinFrame) {
          this.joinFrame = { ...this.joinFrame, session_token: msg.session_token };
        }
        if (msg.type === 'command_accepted' || msg.type === 'command_rejected') {
          if (msg.command_id !== null) this.pendingCommands.delete(msg.command_id);
        }
        this.listeners.forEach((l) => l(msg));
        if (this.ws !== socket || this.stopped) return;
        // Apply the catch-up snapshot before enabling input or retrying uncertain commands.
        if (msg.type === 'snapshot' && this.joinSent && !this.ready) {
          this.ready = true;
          this.flushPendingCommands();
        }
        this.notifyCommandState();
      } catch {
        // ignore malformed messages
      }
    };

    socket.onclose = () => {
      if (this.ws !== socket || this.stopped) return;
      this.ready = false;
      this.notifyCommandState();
      this.notifyState(false);
      if (!this.stopped) {
        this.scheduleRetry();
      }
    };

    socket.onerror = () => {
      if (this.ws === socket) socket.close();
    };
  }

  private scheduleRetry(): void {
    this.retryTimer = setTimeout(() => {
      this.retryTimer = null;
      if (this.stopped) return;
      this.retryDelay = Math.min(this.retryDelay * 2, BACKOFF_MAX);
      this.openSocket();
    }, this.retryDelay);
  }

  private flushPendingCommands(): void {
    // The server remembers outcomes by command_id. Never mint a new ID or revision for a
    // lost acknowledgement: it may already have applied the original action.
    this.pendingCommands.forEach((command) => this.doSend(command));
  }

  private doSend(msg: ClientFrame): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(encodeHexCoordinates(msg)));
    }
  }

  send(msg: ClientFrame): void {
    if (this.stopped) return;
    if (msg.type === 'join_room') {
      // Lobby hooks also send JoinRoom on onStateChange(true); deduplicate that send.
      if (!this.joinSent) this.joinFrame = msg;
      this.sendJoin();
      return;
    }
    this.pendingCommands.set(msg.command_id, msg);
    if (this.isReady) this.doSend(msg);
    this.notifyCommandState();
  }

  private sendJoin(): void {
    if (!this.joinSent && this.joinFrame && this.isConnected) {
      this.joinSent = true;
      this.doSend(this.joinFrame);
    }
  }

  get isReady(): boolean { return this.ready && this.isConnected; }
  get hasPendingCommands(): boolean { return this.pendingCommands.size > 0; }

  onCommandStateChange(listener: CommandStateListener): () => void {
    this.commandStateListeners.add(listener);
    return () => this.commandStateListeners.delete(listener);
  }

  private notifyCommandState(): void {
    const state = { ready: this.isReady, pending: this.hasPendingCommands };
    this.commandStateListeners.forEach((listener) => listener(state));
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
    const socket = this.ws;
    this.ws = null;
    this.ready = false;
    this.joinSent = false;
    this.joinFrame = null;
    this.latestSnapshotRevision = -1;
    this.pendingCommands.clear();
    socket?.close();
    this.notifyState(false);
    this.notifyCommandState();
  }
}
