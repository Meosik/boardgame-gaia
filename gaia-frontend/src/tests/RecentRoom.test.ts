import { beforeEach, expect, it, vi } from 'vitest';
import { readRecentRoom, rememberRoom } from '../store/recentRoom';

beforeEach(() => localStorage.clear());

it('stores only reconnect fields, including manual control, across tab session loss', () => {
  const room = { roomCode: 'ROOM01', playerId: 0, sessionToken: 'test-token', nickname: 'Test', manualControl: true };
  rememberRoom(room);
  sessionStorage.clear();
  expect(readRecentRoom()).toEqual(room);
});

it('ignores corrupted or incomplete saved data', () => {
  for (const data of ['broken', '{}', 'null', '{"roomCode":"ROOM01"}']) {
    localStorage.setItem('gaia-recent-room', data);
    expect(readRecentRoom()).toBeNull();
  }
});

it('does not break the active game if durable storage is unavailable', () => {
  const spy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('denied'); });
  expect(() => rememberRoom({ roomCode: 'ROOM01', playerId: 0, sessionToken: 'test-token', nickname: 'Test', manualControl: false })).not.toThrow();
  spy.mockRestore();
});
