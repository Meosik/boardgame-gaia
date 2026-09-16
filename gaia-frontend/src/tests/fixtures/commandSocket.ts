import type { ClientFrame } from '../../types/game';

export class CommandSocket {
  static OPEN = 1;
  static instances: CommandSocket[] = [];
  readyState = 0;
  sent: ClientFrame[] = [];
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  constructor(readonly url: string) { CommandSocket.instances.push(this); }
  send(data: string) { this.sent.push(JSON.parse(data) as ClientFrame); }
  open() { this.readyState = 1; this.onopen?.(); }
  close() { this.readyState = 3; this.onclose?.(); }
  receive(message: unknown) { this.onmessage?.({ data: JSON.stringify(message) } as MessageEvent); }
  snapshot(revision = 4) { this.receive({ type: 'snapshot', revision, state: { room_code: 'TEST' } }); }
}
export const joinFrame: ClientFrame = {
  type: 'join_room', room_code: 'TEST', nickname: 'fixture', session_token: 'synthetic-session',
};
