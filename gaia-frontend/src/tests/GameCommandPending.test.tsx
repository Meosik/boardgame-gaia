import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { GaiaWebSocket } from '../api/websocket';
import { useGameStore } from '../store/gameStore';
import { GameCommandControls, GameCommandStatus } from '../components/GameCommandControls';
import { CommandSocket, joinFrame } from './fixtures/commandSocket';

let client: GaiaWebSocket;
let socket: CommandSocket;
const actions = useGameStore.getState().actions;
beforeEach(() => {
  actions.reset();
  CommandSocket.instances = [];
  vi.stubGlobal('WebSocket', CommandSocket);
  client = new GaiaWebSocket('TEST');
  actions.setWsClient(client);
  client.on(msg => {
    if (msg.type === 'command_accepted') actions.acceptActionCommand(msg.command_id);
    if (msg.type === 'command_rejected') actions.rejectActionCommand(msg.command_id);
  });
  client.connect(); client.send(joinFrame);
  socket = CommandSocket.instances[0]; socket.open(); socket.snapshot();
});
afterEach(() => { client.disconnect(); actions.reset(); vi.unstubAllGlobals(); });
function ack(id: string | null, accepted = true) {
  socket.receive({ type: accepted ? 'command_accepted' : 'command_rejected', command_id: id });
}
describe('game command admission', () => {
  it('blocks same-tick repeated actions, free actions and every undo path until acknowledgement', () => {
    actions.selectAction('Build'); actions.selectPlanet({ q: 1, r: 0 });
    const id = actions.sendAction({ type: 'Build', coord: { q: 1, r: 0 } });
    expect(id).not.toBeNull();
    expect(actions.sendAction({ type: 'Build', coord: { q: 1, r: 0 } })).toBeNull();
    expect(actions.sendAction({ type: 'FreeAction', kind: 'BurnPower', count: 1 })).toBeNull();
    actions.undoFreeAction(); actions.requestTurnUndo(); actions.respondTurnUndo(true);
    actions.triggerDevPowerCharge({ q: 1, r: 0 });
    expect(socket.sent).toHaveLength(2);
    expect(useGameStore.getState().commandPending).toBe(true);
    ack('unrelated'); expect(useGameStore.getState().selectedAction).toBe('Build');
    ack(id);
    expect(useGameStore.getState().commandPending).toBe(false);
    expect(useGameStore.getState().selectedAction).toBeNull();
    actions.undoFreeAction(); expect(socket.sent).toHaveLength(3);
  });
  it('preserves rejected selection and supports a deliberate corrected retry', () => {
    actions.selectAction('Build'); actions.selectPlanet({ q: 1, r: 0 });
    const id = actions.sendAction({ type: 'Build', coord: { q: 1, r: 0 } });
    ack(id, false);
    expect(useGameStore.getState().selectedAction).toBe('Build');
    expect(useGameStore.getState().activePlanet).toEqual({ q: 1, r: 0 });
    expect(useGameStore.getState().pendingActionCommandId).toBeNull();
    expect(actions.sendAction({ type: 'Build', coord: { q: 2, r: 0 } })).not.toBe(id);
  });
  it('serializes free actions without clearing the selected main action', () => {
    actions.selectAction('Build');
    const action = { type: 'FreeAction', kind: 'BurnPower', count: 1 } as const;
    const id = actions.sendAction(action);
    expect(actions.sendAction(action)).toBeNull();
    ack(id);
    expect(useGameStore.getState().selectedAction).toBe('Build');
    expect(actions.sendAction(action)).not.toBeNull();
  });
  it('does not queue a new game action offline and keeps pending selection on connection loss', () => {
    actions.selectAction('Build');
    const id = actions.sendAction({ type: 'Build', coord: { q: 1, r: 0 } });
    socket.close();
    expect(useGameStore.getState().connectionReady).toBe(false);
    expect(useGameStore.getState().pendingActionCommandId).toBe(id);
    expect(actions.sendAction({ type: 'Build', coord: { q: 2, r: 0 } })).toBeNull();
  });
  it('detaches old client status and preserves read-only replay', () => {
    actions.setWsClient(null); socket.close();
    expect(useGameStore.getState().commandPending).toBe(false);
    actions.setReadOnly(true);
    actions.setWsClient(client);
    expect(useGameStore.getState().wsClient).toBeNull();
    expect(actions.sendAction({ type: 'Build', coord: { q: 1, r: 0 } })).toBeNull();
  });
});
describe('processing feedback', () => {
  it('shows connection/processing status and disables controls until ready', () => {
    const click = vi.fn();
    const view = (ready: boolean, pending: boolean) => <>
      <GameCommandStatus ready={ready} pending={pending} />
      <GameCommandControls blocked={!ready || pending}>
        <button onClick={click}>확정</button>
        <div role="button" tabIndex={0} onClick={click}>보드 선택</div>
      </GameCommandControls>
      <button onClick={click}>로그</button>
    </>;
    const { rerender } = render(view(false, false));
    expect(screen.getByRole('status')).toHaveTextContent('서버 연결·방 복구 중');
    expect(screen.getByText('확정')).toBeDisabled();
    fireEvent.click(screen.getByText('확정')); fireEvent.click(screen.getByText('보드 선택'));
    expect(click).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText('로그')); expect(click).toHaveBeenCalledOnce();
    rerender(view(true, true)); expect(screen.getByRole('status')).toHaveTextContent('명령 처리 중');
    rerender(view(true, false)); expect(screen.queryByRole('status')).toBeNull();
    expect(screen.getByText('확정')).toBeEnabled();
    fireEvent.click(screen.getByText('확정')); expect(click).toHaveBeenCalledTimes(2);
  });
});
