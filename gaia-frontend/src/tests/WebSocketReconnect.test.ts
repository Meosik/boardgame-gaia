import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GaiaWebSocket } from '../api/websocket';
import { CommandSocket, joinFrame } from './fixtures/commandSocket';

let client: GaiaWebSocket;
beforeEach(() => {
  vi.useFakeTimers();
  CommandSocket.instances = [];
  vi.stubGlobal('WebSocket', CommandSocket);
  client = new GaiaWebSocket('TEST');
  client.connect();
});
afterEach(() => { client.disconnect(); vi.useRealTimers(); vi.unstubAllGlobals(); });
const first = () => CommandSocket.instances[0];
function reconnect() {
  first().close(); vi.advanceTimersByTime(1000);
  const socket = CommandSocket.instances[CommandSocket.instances.length - 1]; socket.open(); return socket;
}

describe('room reconnect transport', () => {
  it('sends JoinRoom first and waits for snapshot before queued commands', () => {
    client.sendCommand({ type: 'player_ready', ready: true }, 4);
    client.send(joinFrame); first().open();
    expect(first().sent).toEqual([joinFrame]);
    expect(client.isReady).toBe(false);
    first().receive({ type: 'room_joined', session_token: 'returned-session' });
    expect(first().sent).toHaveLength(1);
    first().snapshot();
    expect(first().sent.map(frame => frame.type)).toEqual(['join_room', 'command']);
    expect(client.isReady).toBe(true);
  });
  it('rejoins with the returned session and deduplicates the lobby hook join', () => {
    client.onStateChange(connected => { if (connected) client.send(joinFrame); });
    first().open();
    first().receive({ type: 'room_joined', session_token: 'returned-session' });
    first().snapshot();
    const socket = reconnect();
    expect(socket.sent).toEqual([{ ...joinFrame, session_token: 'returned-session' }]);
    client.send(joinFrame);
    expect(socket.sent).toHaveLength(1);
    expect(client.isReady).toBe(false);
    socket.snapshot(); expect(client.isReady).toBe(true);
  });
  it('retries an uncertain command with its exact ID, revision and payload after snapshot', () => {
    client.send(joinFrame); first().open(); first().snapshot();
    const id = client.sendCommand({ type: 'undo_free_action' }, 4);
    const command = first().sent[1];
    const socket = reconnect();
    expect(socket.sent).toEqual([joinFrame]);
    expect(client.hasPendingCommands).toBe(true);
    socket.snapshot(8);
    expect(socket.sent[1]).toEqual(command);
    socket.receive({ type: 'command_accepted', command_id: id, revision: 5 });
    expect(client.hasPendingCommands).toBe(false);
    socket.close(); vi.advanceTimersByTime(1000);
    const third = CommandSocket.instances[2]; third.open(); third.snapshot(8);
    expect(third.sent).toEqual([joinFrame]);
  });
  it.each(['command_accepted', 'command_rejected'])('only releases a matching %s', type => {
    client.send(joinFrame); first().open(); first().snapshot();
    const id = client.sendCommand({ type: 'undo_free_action' }, 4);
    first().receive({ type, command_id: 'other', revision: 4 });
    expect(client.hasPendingCommands).toBe(true);
    first().receive({ type, command_id: id, revision: 4 });
    expect(client.hasPendingCommands).toBe(false);
  });
  it('applies snapshot listeners before enabling commands and never retries on later snapshots', () => {
    client.send(joinFrame); first().open();
    const ready = vi.fn(() => expect(client.isReady).toBe(false));
    const off = client.on(ready);
    client.sendCommand({ type: 'undo_free_action' }, 4);
    first().snapshot(); off(); first().snapshot(5);
    expect(ready).toHaveBeenCalledOnce();
    expect(first().sent).toHaveLength(2);
  });
  it('ignores stale sockets and cancels retries and pending work on intentional disconnect', () => {
    client.send(joinFrame); first().open(); first().snapshot();
    client.sendCommand({ type: 'undo_free_action' }, 4);
    const listener = vi.fn(); client.on(listener);
    const socket = reconnect();
    first().open(); first().snapshot(); first().onclose?.(); first().onerror?.();
    expect(listener).not.toHaveBeenCalled();
    expect(socket.readyState).toBe(1);
    socket.close(); client.disconnect(); vi.runAllTimers();
    expect(CommandSocket.instances).toHaveLength(2);
    expect(client.isReady).toBe(false);
    expect(client.hasPendingCommands).toBe(false);
  });
  it('ignores older snapshots broadcast while replaying an already committed command', () => {
    client.send(joinFrame); first().open(); first().snapshot(4);
    const id = client.sendCommand({ type: 'undo_free_action' }, 4);
    const socket = reconnect(); socket.snapshot(12);
    const listener = vi.fn(); client.on(listener);
    socket.snapshot(5);
    expect(listener).not.toHaveBeenCalled();
    socket.receive({ type: 'command_accepted', command_id: id, revision: 5 });
    expect(listener).toHaveBeenCalledOnce();
    expect(client.hasPendingCommands).toBe(false);
    socket.snapshot(12);
    expect(listener).toHaveBeenCalledTimes(2);
  });
});
