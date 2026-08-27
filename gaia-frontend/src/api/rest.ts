import type {
  CreateRoomResponse,
  JoinRoomResponse,
  RoomInfo,
  GameSetup,
  PreviewBoard,
  SetupMode,
} from '../types/game';
import { decodeHexCoordinates } from './websocket';

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
    throw new Error(`HTTP ${res.status}: ${body}`);
  }
  return decodeHexCoordinates(await res.json()) as T;
}

export const api = {
  createRoom(
    nickname: string,
    seed?: string,
    setupMode: SetupMode = 'sequential',
  ): Promise<CreateRoomResponse> {
    return request(`${BASE}/rooms`, {
      method: 'POST',
      body: JSON.stringify({ nickname, seed, setup_mode: setupMode }),
    });
  },

  joinRoom(
    code: string,
    nickname: string,
    sessionToken?: string,
  ): Promise<JoinRoomResponse> {
    return request(`${BASE}/rooms/${code}/join`, {
      method: 'POST',
      body: JSON.stringify({ nickname, session_token: sessionToken }),
    });
  },

  getRoom(code: string): Promise<RoomInfo> {
    return request(`${BASE}/rooms/${code}`);
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
