import { create } from 'zustand';
import type { GameAction, GameState, HexCoord, PlayerId } from '../types/game';
import { GaiaWebSocket } from '../api/websocket';
import { useRoomStore } from './roomStore';
import { hexKey } from '../components/GameBoard/hex-utils';

type ActionType = GameAction['type'] | null;

/** Set once the server broadcasts `game_ended` (round 6 completes) — the game is over and the
 * board becomes read-only; `GameOverScreen` renders instead of the normal action flow. */
export interface FinalResult {
  finalScores: [PlayerId, number][];
  winner: PlayerId;
}

interface GameStore {
  gameState: GameState | null;
  myPlayerId: PlayerId | null;
  activePlanet: HexCoord | null;
  /** Accumulated hex picks for multi-hex actions (currently only
   * FormFederation) — `activePlanet` covers every single-hex action. */
  selectedHexes: HexCoord[];
  selectedAction: ActionType;
  wsClient: GaiaWebSocket | null;
  finalResult: FinalResult | null;

  actions: {
    setGameState: (state: GameState) => void;
    setMyPlayerId: (id: PlayerId) => void;
    selectPlanet: (coord: HexCoord | null) => void;
    toggleHex: (coord: HexCoord) => void;
    selectAction: (action: ActionType) => void;
    sendAction: (action: GameAction) => void;
    setWsClient: (client: GaiaWebSocket | null) => void;
    setFinalResult: (result: FinalResult) => void;
    reset: () => void;
  };
}

const initialState = {
  gameState: null,
  myPlayerId: null,
  activePlanet: null,
  selectedHexes: [] as HexCoord[],
  selectedAction: null as ActionType,
  wsClient: null,
  finalResult: null as FinalResult | null,
};

export const useGameStore = create<GameStore>((set, get) => ({
  ...initialState,

  actions: {
    setGameState(state) {
      set({ gameState: state });
    },

    setMyPlayerId(id) {
      set({ myPlayerId: id });
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
      set({ selectedAction: action, activePlanet: null, selectedHexes: [] });
    },

    sendAction(action) {
      const { wsClient } = get();
      const revision = useRoomStore.getState().revision;
      wsClient?.sendCommand({ type: 'place_game_action', action }, revision);
      set({ selectedAction: null, activePlanet: null, selectedHexes: [] });
    },

    setWsClient(client) {
      set({ wsClient: client });
    },

    setFinalResult(result) {
      set({ finalResult: result });
    },

    reset() {
      set(initialState);
    },
  },
}));
