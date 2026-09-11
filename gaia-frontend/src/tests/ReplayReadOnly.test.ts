import { afterEach, describe, expect, it, vi } from 'vitest';
import { useGameStore } from '../store/gameStore';
import type { GaiaWebSocket } from '../api/websocket';

afterEach(() => useGameStore.getState().actions.reset());
describe('replay network isolation', () => {
  it('disconnects an existing client and blocks all commands and new clients', () => {
    const sendCommand = vi.fn(); const disconnect = vi.fn();
    const client = { sendCommand, disconnect } as unknown as GaiaWebSocket;
    const actions = useGameStore.getState().actions;
    actions.setWsClient(client); actions.setReadOnly(true);
    expect(disconnect).toHaveBeenCalledOnce();
    actions.sendAction({ type: 'Pass', booster_id: null });
    actions.triggerDevPowerCharge({ q: 0, r: 0 });
    actions.undoFreeAction(); actions.requestTurnUndo(); actions.respondTurnUndo(true);
    actions.selectAction('Build'); actions.selectPowerAction(1); actions.setWsClient(client);
    expect(sendCommand).not.toHaveBeenCalled();
    expect(useGameStore.getState().wsClient).toBeNull();
    expect(useGameStore.getState().selectedAction).toBeNull();
  });
  it('does not change live-game command behavior after reset', () => {
    const actions = useGameStore.getState().actions;
    actions.setReadOnly(true); actions.reset();
    const sendCommand = vi.fn().mockReturnValue('cmd');
    actions.setWsClient({ sendCommand } as unknown as GaiaWebSocket);
    expect(actions.sendAction({ type: 'Pass', booster_id: null })).toBe('cmd');
    expect(sendCommand).toHaveBeenCalledOnce();
  });
});
