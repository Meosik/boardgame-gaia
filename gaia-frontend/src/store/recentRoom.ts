import type { PlayerId } from '../types/game';

export interface RecentRoom {
  roomCode: string;
  playerId: PlayerId;
  sessionToken: string;
  nickname: string;
  manualControl: boolean;
}

const STORAGE_KEY = 'gaia-recent-room';

export function readRecentRoom(): RecentRoom | null {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null');
    if (!value || typeof value !== 'object') return null;
    const room = value as Partial<RecentRoom>;
    if (typeof room.roomCode !== 'string' || !room.roomCode
      || typeof room.playerId !== 'number' || !Number.isInteger(room.playerId) || room.playerId < 0
      || typeof room.sessionToken !== 'string' || !room.sessionToken
      || typeof room.nickname !== 'string' || typeof room.manualControl !== 'boolean') return null;
    return {
      roomCode: room.roomCode,
      playerId: room.playerId,
      sessionToken: room.sessionToken,
      nickname: room.nickname,
      manualControl: room.manualControl,
    };
  } catch {
    return null;
  }
}

export function rememberRoom(room: RecentRoom): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(room));
  } catch {
    // A denied durable-storage write must not interrupt the active tab's session.
  }
}

export function forgetRecentRoom(roomCode: string): void {
  try {
    if (readRecentRoom()?.roomCode === roomCode) localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Match the existing storage-denied behavior.
  }
}
