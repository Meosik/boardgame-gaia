import type {
  CreateRoomResponse,
  DevGameResponse,
  FactionId,
  JoinRoomResponse,
  RoomInfo,
  RoomSummary,
  GameSetup,
  PreviewBoard,
  SetupMode,
} from '../types/game';
import { decodeHexCoordinates } from './websocket';
import { apiError } from './errors';

/** AI difficulty for games against AI seats (server: crate::ai::LEVELS). */
export type AiLevel = 'easy' | 'normal' | 'hard';

/** A fixed table for an AI game, so the same map and factions can be played again (the lab
 * replays it with the teacher in every seat). Anything left out is drawn from the seed. */
export interface AiGameTable {
  seed?: string;
  /** The human seat's faction. */
  faction?: FactionId;
  /** The three AI seats' factions: all three or none. */
  aiFactions?: FactionId[];
  /** The human's place in the turn order, 1 (first) to 4; left out = first. */
  seat?: number;
}

/** The teacher's move for one position: `decision` is `{ phase, action }` as the engine names it. */
export interface AiHintReply {
  revision: number;
  decision: unknown;
}

const BASE = '/api';

// Same "q,r" string <-> { q, r } object boundary conversion the WebSocket
// path applies (see `decodeHexCoordinates`'s own doc comment) — REST
// responses carry the same `HexCoord`-bearing types (e.g. `preview_board`'s
// board/sectors, `game_setup`'s sector layouts) and need the identical fix,
// or every `origin.q`/`hex.coord.q` reader downstream sees `undefined` and
// silently produces NaN pixel coordinates.
async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw apiError(res.status, body);
  }
  return decodeHexCoordinates(await res.json()) as T;
}

export const api = {
  devTool(code: string, sessionToken: string, revision: number, tool: 'refill' | 'delete'): Promise<unknown> {
    return request(`${BASE}/rooms/${code}/dev-${tool}`, {
      method: 'POST',
      body: JSON.stringify({
        session_token: sessionToken,
        command_id: crypto.randomUUID(),
        expected_revision: revision,
      }),
    });
  },
  createDevRoom(nickname: string, seed?: string, setupMode: SetupMode = 'bidding'): Promise<CreateRoomResponse> {
    return request(`${BASE}/dev-games`, {
      method: 'POST',
      body: JSON.stringify({ nickname, seed, setup_mode: setupMode, full_setup: true }),
    });
  },
  /** A game against three AI seats ('hard' searches twice as much and thinks longer); (server needs the AI pool); random map and factions.
   * With `table` the game skips the setup auction: the map comes from `table.seed` and the seats
   * get the named factions (the rest are drawn from the seed). `setup_mode` is always sent with
   * it — the server's default is the auction, which has no fixed factions. */
  createAiGame(
    nickname: string,
    level: AiLevel = 'normal',
    table?: AiGameTable,
    /** `true` = the AI seats wait after each of their turns (`aiContinue` / `aiReject`). */
    review = false,
  ): Promise<DevGameResponse> {
    return request(`${BASE}/dev-games`, {
      method: 'POST',
      body: JSON.stringify({
        nickname,
        ai_opponents: true,
        ai_level: level,
        ...(review ? { ai_review: true } : {}),
        ...(table
          ? {
              setup_mode: 'sequential',
              seed: table.seed,
              faction: table.faction,
              ai_factions: table.aiFactions,
              human_seat: table.seat,
            }
          : {}),
      }),
    });
  },
  createTutorialGame(): Promise<DevGameResponse> {
    return request(`${BASE}/tutorial-games`, { method: 'POST' });
  },
  createDevGame(faction = 'Terrans', seed = 'gaia-ui-dev'): Promise<DevGameResponse> {
    return request(`${BASE}/dev-games`, {
      method: 'POST',
      body: JSON.stringify({ faction, seed }),
    });
  },

  createRoom(
    nickname: string,
    seed?: string,
    setupMode: SetupMode = 'sequential',
    name?: string,
    password?: string,
  ): Promise<CreateRoomResponse> {
    return request(`${BASE}/rooms`, {
      method: 'POST',
      body: JSON.stringify({ nickname, seed, setup_mode: setupMode, name, password }),
    });
  },

  joinRoom(
    code: string,
    nickname: string,
    sessionToken?: string,
    password?: string,
  ): Promise<JoinRoomResponse> {
    return request(`${BASE}/rooms/${code}/join`, {
      method: 'POST',
      body: JSON.stringify({ nickname, session_token: sessionToken, password }),
    });
  },

  getRoom(code: string): Promise<RoomInfo> {
    return request(`${BASE}/rooms/${code}`);
  },

  /** Whether the room's other seats are played by the AI — the game screen then offers hints. */
  async aiGame(code: string): Promise<boolean> {
    const room = await request<{ ai_game?: boolean }>(`${BASE}/rooms/${code}`);
    return room.ai_game === true;
  },

  /** What the teacher would play for the human seat at `revision` (nothing is applied). The
   * teacher searches before it answers, so this can take a minute; the reply repeats the
   * revision it belongs to. */
  aiHint(code: string, sessionToken: string, revision: number): Promise<AiHintReply> {
    return request(`${BASE}/rooms/${code}/ai-hint`, {
      method: 'POST',
      body: JSON.stringify({ session_token: sessionToken, expected_revision: revision }),
    });
  },

  /** Asks the teacher again after the AI seats of an AI game stopped (`GameState.ai_stalled`).
   * The move, if the teacher has one now, arrives as an ordinary snapshot. */
  aiRetry(code: string, sessionToken: string): Promise<{ ok: boolean }> {
    return request(`${BASE}/rooms/${code}/ai-retry`, {
      method: 'POST',
      body: JSON.stringify({ session_token: sessionToken }),
    });
  },

  /** Turns the wait after every AI turn on or off (`GameState.ai_review`). The server keeps the
   * setting in memory only: after a server restart it is off again. */
  aiReview(code: string, sessionToken: string, enabled: boolean): Promise<{ ok: boolean }> {
    return request(`${BASE}/rooms/${code}/ai-review`, {
      method: 'POST',
      body: JSON.stringify({ session_token: sessionToken, enabled }),
    });
  },

  /** Lets the AI seats play on from the finished AI turn they wait at (`GameState.ai_hold`). */
  aiContinue(code: string, sessionToken: string): Promise<{ ok: boolean }> {
    return request(`${BASE}/rooms/${code}/ai-continue`, {
      method: 'POST',
      body: JSON.stringify({ session_token: sessionToken }),
    });
  },

  /** Rejects the finished AI turn the AI seats wait at: the room goes back to that turn's first
   * position and the seat plays it again without the move that ended it. `revision` is the
   * hold's (`GameState.ai_hold.revision`); the new position arrives as snapshots. */
  aiReject(code: string, sessionToken: string, revision: number): Promise<{ ok: boolean }> {
    return request(`${BASE}/rooms/${code}/ai-reject`, {
      method: 'POST',
      body: JSON.stringify({ session_token: sessionToken, expected_revision: revision }),
    });
  },

  /** Takes back the player's latest setup choice in an AI game (`GameState.setup_redo`): the
   * room goes back to the position of that choice; it arrives as a snapshot. `revision` is the
   * one the player is looking at. */
  setupRedo(code: string, sessionToken: string, revision: number): Promise<{ ok: boolean }> {
    return request(`${BASE}/rooms/${code}/setup-redo`, {
      method: 'POST',
      body: JSON.stringify({ session_token: sessionToken, expected_revision: revision }),
    });
  },

  listRooms(): Promise<RoomSummary[]> {
    return request(`${BASE}/rooms`);
  },

  regenerateSetup(
    code: string,
    sessionToken: string,
    seed?: string,
  ): Promise<GameSetup> {
    return request(`${BASE}/rooms/${code}/regenerate`, {
      method: 'POST',
      body: JSON.stringify({ session_token: sessionToken, seed }),
    });
  },

  getPreviewBoard(code: string): Promise<PreviewBoard> {
    return request(`${BASE}/rooms/${code}/preview_board`);
  },

  async health(): Promise<void> {
    await fetch('/health');
  },
};
