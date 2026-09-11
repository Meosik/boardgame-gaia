import { describe, expect, it } from 'vitest';
import fixture from './fixtures/replay.json';
import { parseReplay } from '../replay/records';
import { adjacentReplayFrame } from '../replay/stepping';

const base = parseReplay(fixture);
const frames = [null, 0, 1, 0, 2].map((player, index) => ({
  ...base.frames[index === 0 ? 0 : 1], player, decision_id: index,
}));

describe('faction action stepping', () => {
  it('preserves every original frame in all-action mode', () => {
    expect(adjacentReplayFrame(frames, 0, 1, null)).toBe(1);
    expect(adjacentReplayFrame(frames, 3, 1, null)).toBe(4);
    expect(adjacentReplayFrame(frames, 3, -1, null)).toBe(2);
  });
  it('skips other actors in both directions without modifying their snapshots', () => {
    const original = JSON.stringify(frames);
    expect(adjacentReplayFrame(frames, 1, 1, 0)).toBe(3);
    expect(adjacentReplayFrame(frames, 3, -1, 0)).toBe(1);
    expect(adjacentReplayFrame(frames, 4, -1, 0)).toBe(3);
    expect(JSON.stringify(frames)).toBe(original);
  });
  it('handles initial state, last matching action and a faction with no actions', () => {
    expect(adjacentReplayFrame(frames, 1, -1, 0)).toBe(0);
    expect(adjacentReplayFrame(frames, 0, -1, 0)).toBeNull();
    expect(adjacentReplayFrame(frames, 3, 1, 0)).toBeNull();
    expect(adjacentReplayFrame(frames, 0, 1, 3)).toBeNull();
    expect(adjacentReplayFrame([], 0, 1, 0)).toBeNull();
  });
});
