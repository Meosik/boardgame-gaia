import type {
  CreateRoomResponse,
  JoinRoomResponse,
  RoomInfo,
  GameSetup,
} from '../types/game';

const BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  createRoom(nickname: string, seed?: string): Promise<CreateRoomResponse> {
    return request(`${BASE}/rooms`, {
      method: 'POST',
      body: JSON.stringify({ nickname, seed }),
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

  async health(): Promise<void> {
    await fetch('/health');
  },
};
