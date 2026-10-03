import type {
  CreateRoomResponse,
  DevGameResponse,
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
  /** A game against three AI seats ('hard' searches twice as much and thinks longer); (server needs the AI pool); random map and factions. */
  createAiGame(nickname: string, level: AiLevel = 'normal'): Promise<DevGameResponse> {
    return request(`${BASE}/dev-games`, {
      method: 'POST',
      body: JSON.stringify({ nickname, ai_opponents: true, ai_level: level }),
    });
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
