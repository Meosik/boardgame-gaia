import { create } from 'zustand';
import { api } from '../api/rest';
import type { GameSetup, LobbyPlayer, PlayerId } from '../types/game';

export type RoomState = 'lobby' | 'faction_selection' | 'in_game' | 'ended';

interface RoomStore {
  roomCode: string | null;
  playerId: PlayerId | null;
  sessionToken: string | null;
  playerCount: number;
  roomState: RoomState;
  gameSetup: GameSetup | null;
  nickname: string;
  lobbyPlayers: LobbyPlayer[];
  hostPlayerId: PlayerId | null;
  /** The room's revision, as last observed from `room_joined`,
   * `command_accepted`, or `snapshot` — the value the next command sends as
   * `expected_revision`. */
  revision: number;
  paused: boolean;
  missingSeats: PlayerId[];
  /** The most recent `command_rejected` reply, if any — cleared on the next
   * accepted command or explicitly by the UI once shown. */
  lastError: { code: string; message: string } | null;

  actions: {
    createRoom: (nickname: string, seed?: string) => Promise<void>;
    joinRoom: (code: string, nickname: string, sessionToken?: string) => Promise<void>;
    regenerateSetup: (seed?: string) => Promise<void>;
    setRoomInfo: (info: Partial<Omit<RoomStore, 'actions'>>) => void;
    setRevision: (revision: number) => void;
    setError: (error: { code: string; message: string } | null) => void;
    reset: () => void;
  };
}

const initialState = {
  roomCode: null,
  playerId: null,
  sessionToken: null,
  playerCount: 0,
  roomState: 'lobby' as RoomState,
  gameSetup: null,
  nickname: '',
  lobbyPlayers: [],
  hostPlayerId: null,
  revision: 0,
  paused: false,
  missingSeats: [] as PlayerId[],
  lastError: null as { code: string; message: string } | null,
};

export const useRoomStore = create<RoomStore>((set, get) => ({
  ...initialState,

  actions: {
    async createRoom(nickname, seed) {
      const res = await api.createRoom(nickname, seed);
      set({
        roomCode: res.room_code ?? res.code,
        playerId: res.player_id,
        sessionToken: res.session_token,
        gameSetup: res.game_setup,
        playerCount: res.players.length,
        nickname,
        lobbyPlayers: res.players,
        hostPlayerId: res.host_player_id,
        roomState: 'lobby',
      });
    },

    async joinRoom(code, nickname, sessionToken) {
      const res = await api.joinRoom(code, nickname, sessionToken);
      set({
        roomCode: res.room_code ?? code,
        playerId: res.player_id,
        sessionToken: res.session_token,
        gameSetup: res.game_setup,
        playerCount: res.players.length,
        nickname,
        lobbyPlayers: res.players,
        hostPlayerId: res.host_player_id,
        roomState: 'lobby',
      });
    },

    async regenerateSetup(seed) {
      const { roomCode, sessionToken } = get();
      if (!roomCode || !sessionToken) return;
      const setup = await api.regenerateSetup(roomCode, sessionToken, seed);
      set({ gameSetup: setup });
    },

    setRoomInfo(info) {
      set(info);
    },

    setRevision(revision) {
      set({ revision });
    },

    setError(error) {
      set({ lastError: error });
    },

    reset() {
      set(initialState);
    },
  },
}));
