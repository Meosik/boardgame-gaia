import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import { api } from '../api/rest';
import { rememberRoom, type RecentRoom } from './recentRoom';
import type { GameSetup, LobbyPlayer, PlayerId, PreviewBoard, SetupMode } from '../types/game';

export type RoomState = 'lobby' | 'faction_selection' | 'in_game' | 'ended';

interface RoomStore {
  roomCode: string | null;
  manualControl: boolean;
  playerId: PlayerId | null;
  sessionToken: string | null;
  playerCount: number;
  roomState: RoomState;
  gameSetup: GameSetup | null;
  previewBoard: PreviewBoard | null;
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
    resumeRoom: (room: RecentRoom) => void;
    createRoom: (
      nickname: string,
      seed?: string,
      setupMode?: SetupMode,
      manualControl?: boolean,
      options?: { name?: string; password?: string },
    ) => Promise<void>;
    createAiGame: (nickname: string) => Promise<void>;
    joinRoom: (code: string, nickname: string, sessionToken?: string, password?: string) => Promise<void>;
    regenerateSetup: (seed?: string) => Promise<void>;
    fetchPreviewBoard: () => Promise<void>;
    setRoomInfo: (info: Partial<Omit<RoomStore, 'actions'>>) => void;
    setRevision: (revision: number) => void;
    setError: (error: { code: string; message: string } | null) => void;
    reset: () => void;
  };
}

const initialState = {
  roomCode: null,
  manualControl: false,
  playerId: null,
  sessionToken: null,
  playerCount: 0,
  roomState: 'lobby' as RoomState,
  gameSetup: null,
  previewBoard: null,
  nickname: '',
  lobbyPlayers: [],
  hostPlayerId: null,
  revision: 0,
  paused: false,
  missingSeats: [] as PlayerId[],
  lastError: null as { code: string; message: string } | null,
};

export const useRoomStore = create<RoomStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      actions: {
        resumeRoom(room) {
          set({ ...initialState, ...room });
        },
        async createRoom(nickname, seed, setupMode = 'sequential', manualControl = false, options = {}) {
          const res = manualControl
            ? await api.createDevRoom(nickname, seed, setupMode)
            : await api.createRoom(nickname, seed, setupMode, options.name, options.password);
          set({
            manualControl,
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
          const saved = get();
          if (saved.roomCode && saved.playerId !== null && saved.sessionToken) {
            rememberRoom({ roomCode: saved.roomCode, playerId: saved.playerId, sessionToken: saved.sessionToken, nickname: saved.nickname, manualControl: saved.manualControl });
          }
        },

        async createAiGame(nickname) {
          const res = await api.createAiGame(nickname);
          set({
            manualControl: false,
            roomCode: res.room_code,
            playerId: res.player_id,
            sessionToken: res.session_token,
            gameSetup: res.game_setup,
            playerCount: res.players.length,
            nickname,
            lobbyPlayers: res.players,
            hostPlayerId: res.host_player_id,
            roomState: 'faction_selection',
          });
          rememberRoom({ roomCode: res.room_code, playerId: res.player_id, sessionToken: res.session_token,
            nickname, manualControl: false });
        },

        async joinRoom(code, nickname, sessionToken, password) {
          const res = await api.joinRoom(code, nickname, sessionToken, password);
          set({
            manualControl: false,
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
          const saved = get();
          if (saved.roomCode && saved.playerId !== null && saved.sessionToken) {
            rememberRoom({ roomCode: saved.roomCode, playerId: saved.playerId, sessionToken: saved.sessionToken, nickname: saved.nickname, manualControl: saved.manualControl });
          }
        },

        async regenerateSetup(seed) {
          const { roomCode, sessionToken } = get();
          if (!roomCode || !sessionToken) return;
          const setup = await api.regenerateSetup(roomCode, sessionToken, seed);
          set((state) => ({
            gameSetup: setup,
            lobbyPlayers: state.lobbyPlayers.map((player) => ({ ...player, ready: false })),
          }));
        },

        async fetchPreviewBoard() {
          const { roomCode, gameSetup } = get();
          if (!roomCode) return;
          const expectedSeed = gameSetup?.seed;
          const previewBoard = await api.getPreviewBoard(roomCode);
          if (get().gameSetup?.seed === expectedSeed && previewBoard.seed === expectedSeed) {
            set({ previewBoard });
          }
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
    }),
    {
      name: 'gaia-room-session',
      // `sessionStorage`, not `localStorage`: this must survive a reload of
      // *this tab*, but must NOT leak across tabs — `localStorage` is
      // shared by every tab of the same origin, so testing 4 seats via 4
      // tabs in one browser would have every tab's `createRoom`/`joinRoom`
      // overwrite the same stored session, and a refreshed tab could
      // rehydrate as a completely different player's seat.
      storage: createJSONStorage(() => sessionStorage),
      // Only the fields needed to reconnect are persisted — a `join_room`
      // carrying a valid `session_token` resumes the same seat server-side
      // (see the `reconnected` branch in
      // `gaia-server/src/handlers/websocket.rs`), bypassing the
      // room-must-still-be-in-lobby check a *fresh* join would hit. Without
      // this, a page refresh wiped `sessionToken` from memory entirely —
      // the player's seat stayed reserved server-side (seats are never
      // removed on disconnect) but nothing could ever reconnect to it,
      // permanently stranding that seat and, with it, `all_ready()` for the
      // whole room. Everything else (lobby roster, setup preview, revision,
      // ...) is re-fetched from the server on reconnect, so persisting it
      // too would just risk rendering stale data before the first snapshot
      // arrives.
      partialize: (state) => ({
        roomCode: state.roomCode,
        manualControl: state.manualControl,
        playerId: state.playerId,
        sessionToken: state.sessionToken,
        nickname: state.nickname,
      }),
    },
  ),
);
