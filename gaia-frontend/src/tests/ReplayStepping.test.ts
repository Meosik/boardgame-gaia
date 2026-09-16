import { describe, expect, it } from 'vitest';
import fixture from './fixtures/replay.json';
import { parseReplay } from '../replay/records';
import { adjacentReplayFrame, replayRoundStarts } from '../replay/stepping';

const base = parseReplay(fixture);
const frames = [null, 0, 1, 0, 2].map((player, index) => ({
  ...base.frames[index === 0 ? 0 : 1], player, decision_id: index,
}));

describe('round starts', () => {
  it('uses the first recorded state of each round, not an actor or decision-id offset', () => {
    const rounds = [0, 0, 1, 1, 2, 2, 3, 4, 4, 5, 6, 6].map((round, index) => ({
      ...structuredClone(base.frames[0]), decision_id: 100 + index,
      state: { ...structuredClone(base.frames[0].state), round },
    }));
    const original = JSON.stringify(rounds);
    expect(replayRoundStarts(rounds)).toEqual([
      { round: 1, cursor: 2 }, { round: 2, cursor: 4 }, { round: 3, cursor: 6 },
      { round: 4, cursor: 7 }, { round: 5, cursor: 9 }, { round: 6, cursor: 10 },
    ]);
    expect(JSON.stringify(rounds)).toBe(original);
  });

  it('does not invent missing rounds or include initial placement', () => {
    expect(replayRoundStarts([])).toEqual([]);
    expect(replayRoundStarts([base.frames[0]])).toEqual([]);
  });
});

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
