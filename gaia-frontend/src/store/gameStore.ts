import { matchesTutorialAction, tutorialNotice } from '../tutorial/round1';
import { controlledPlayer } from '../devControl';
import { create } from 'zustand';
import type { ClientCommand, GameAction, GameState, HexCoord, PlayerId } from '../types/game';
import { GaiaWebSocket } from '../api/websocket';
import { useRoomStore } from './roomStore';
import { hexKey } from '../components/GameBoard/hex-utils';

type ActionType = GameAction['type'] | null;

/** Set once the server broadcasts `game_ended` (round 6 completes) — the game is over and the
 * board becomes read-only; `GameOverScreen` renders instead of the normal action flow. Also
 * derivable straight from `gameState.phase`'s `Ended` variant (see `App.tsx`), so a client that
 * only loads a later snapshot still reconstructs the same result without having seen this
 * broadcast. `winners` lists every player tied for the top score — ties share the win. */
export interface FinalResult {
  finalScores: [PlayerId, number][];
  winners: PlayerId[];
}

interface GameStore {
  readOnly: boolean;
  gameState: GameState | null;
  myPlayerId: PlayerId | null;
  sessionPlayerId: PlayerId | null;
  activePlanet: HexCoord | null;
  /** Accumulated hex picks for multi-hex actions (currently only
   * FormFederation) — `activePlanet` covers every single-hex action. */
  selectedHexes: HexCoord[];
  selectedAction: ActionType;
  /** Exact shared power-action slot selected from the research board. */
  selectedPowerActionId: number | null;
  /** Command currently expected to finish the selected main-action flow. Selection is only
   * cleared after this command is accepted; a rejection leaves the action and target intact. */
  pendingActionCommandId: string | null;
  wsClient: GaiaWebSocket | null;
  connectionReady: boolean;
  commandPending: boolean;
  finalResult: FinalResult | null;

  actions: {
    setReadOnly: (value: boolean) => void;
    setGameState: (state: GameState) => void;
    setMyPlayerId: (id: PlayerId) => void;
    selectPlanet: (coord: HexCoord | null) => void;
    toggleHex: (coord: HexCoord) => void;
    selectAction: (action: ActionType) => void;
    selectPowerAction: (id: number | null) => void;
    sendAction: (action: GameAction) => string | null;
    acceptActionCommand: (commandId: string) => boolean;
    rejectActionCommand: (commandId: string | null) => boolean;
    triggerDevPowerCharge: (coord: HexCoord) => void;
    undoFreeAction: () => void;
    requestTurnUndo: () => void;
    respondTurnUndo: (approve: boolean) => void;
    setWsClient: (client: GaiaWebSocket | null) => void;
    setFinalResult: (result: FinalResult) => void;
    reset: () => void;
  };
}

const initialState = {
  readOnly: false,
  gameState: null,
  myPlayerId: null,
  sessionPlayerId: null,
  activePlanet: null,
  selectedHexes: [] as HexCoord[],
  selectedAction: null as ActionType,
  selectedPowerActionId: null as number | null,
  pendingActionCommandId: null as string | null,
  wsClient: null,
  connectionReady: false,
  commandPending: false,
  finalResult: null as FinalResult | null,
};

export const useGameStore = create<GameStore>((set, get) => {
  let stopCommandState: (() => void) | null = null;
  const sendCommand = (command: ClientCommand): string | null => {
    const { readOnly, wsClient } = get();
    // Check the transport synchronously, not just React's last rendered disabled state.
    if (readOnly || !wsClient?.isReady || wsClient.hasPendingCommands) return null;
    return wsClient.sendCommand(command, useRoomStore.getState().revision);
  };
  return ({
  ...initialState,

  actions: {
    setReadOnly(value) {
      if (value) {
        get().wsClient?.disconnect();
        get().actions.setWsClient(null);
      }
      set({ readOnly: value, ...(value ? { wsClient: null, selectedAction: null,
        selectedPowerActionId: null, activePlanet: null, selectedHexes: [], pendingActionCommandId: null } : {}) });
    },

    setGameState(state) {
      const myPlayerId = controlledPlayer(state, get().sessionPlayerId ?? get().myPlayerId);
      const changedSeat = myPlayerId !== get().myPlayerId;
      set({ gameState: state, myPlayerId, ...(changedSeat ? {
        selectedAction: null, selectedPowerActionId: null, activePlanet: null, selectedHexes: [],
      } : {}) });
    },

    setMyPlayerId(id) {
      set({ sessionPlayerId: id, myPlayerId: controlledPlayer(get().gameState, id) });
    },

    selectPlanet(coord) {
      set({ activePlanet: coord });
    },

    toggleHex(coord) {
      const { selectedHexes } = get();
      const key = hexKey(coord.q, coord.r);
      const exists = selectedHexes.some((h) => hexKey(h.q, h.r) === key);
      set({
        selectedHexes: exists
          ? selectedHexes.filter((h) => hexKey(h.q, h.r) !== key)
          : [...selectedHexes, coord],
      });
    },

    selectAction(action) {
      if (get().readOnly) return;
      set({
        selectedAction: action,
        selectedPowerActionId: action === 'PowerAction' ? get().selectedPowerActionId : null,
        activePlanet: null,
        selectedHexes: [],
      });
    },

    selectPowerAction(id) {
      if (get().readOnly) return;
      set({
        selectedAction: id === null ? null : 'PowerAction',
        selectedPowerActionId: id,
        activePlanet: null,
        selectedHexes: [],
      });
    },

    sendAction(action) {
      const tutorial = get().gameState?.tutorial;
      if (tutorial && !matchesTutorialAction(tutorial, action)) {
        useRoomStore.getState().actions.setError({ code: 'TutorialStepMismatch', message: tutorialNotice(tutorial) });
        return null;
      }
      const commandId = sendCommand({ type: 'place_game_action', action });
      if (commandId === null) return null;
      // Free actions are deliberately allowed in the middle of a selected main action and must
      // never become the command that clears that selection when their acknowledgement arrives.
      if (action.type !== 'FreeAction') set({ pendingActionCommandId: commandId });
      return commandId;
    },

    acceptActionCommand(commandId) {
      if (get().pendingActionCommandId !== commandId) return false;
      set({
        pendingActionCommandId: null,
        selectedAction: null,
        selectedPowerActionId: null,
        activePlanet: null,
        selectedHexes: [],
      });
      return true;
    },

    rejectActionCommand(commandId) {
      if (commandId === null || get().pendingActionCommandId !== commandId) return false;
      set({ pendingActionCommandId: null });
      return true;
    },

    triggerDevPowerCharge(coord) {
      if (sendCommand({ type: 'trigger_dev_power_charge', coord }) === null) return;
      set({
        selectedAction: null,
        selectedPowerActionId: null,
        pendingActionCommandId: null,
        activePlanet: null,
        selectedHexes: [],
      });
    },

    undoFreeAction() {
      sendCommand({ type: 'undo_free_action' });
    },

    requestTurnUndo() {
      sendCommand({ type: 'request_turn_undo' });
    },

    respondTurnUndo(approve) {
      sendCommand({ type: 'respond_turn_undo', approve });
    },

    setWsClient(client) {
      if (get().readOnly && client) { client.disconnect(); return; }
      stopCommandState?.();
      stopCommandState = client?.onCommandStateChange(({ ready, pending }) => {
        set({ connectionReady: ready, commandPending: pending });
      }) ?? null;
      set({ wsClient: client, connectionReady: client?.isReady ?? false,
        commandPending: client?.hasPendingCommands ?? false, pendingActionCommandId: null });
    },

    setFinalResult(result) {
      set({ finalResult: result });
    },

    reset() {
      stopCommandState?.();
      stopCommandState = null;
      set(initialState);
    },
  },
});
});
