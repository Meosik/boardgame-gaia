import { describe, expect, it } from 'vitest';
import { replayRewardBatches } from '../replay/rewards';
import { parseReplay } from '../replay/records';
import fixture from './fixtures/replay.json';

function record() {
  const replay = parseReplay(fixture);
  for (const frame of replay.frames) { frame.state.round = 1; frame.event_end = 0; }
  replay.frames[1].state = structuredClone(replay.frames[0].state);
  replay.frames[2].state = structuredClone(replay.frames[0].state);
  replay.events = [];
  return replay;
}

describe('replay resource motion data', () => {
  it('animates only observed changes for the correct players, without mutating snapshots', () => {
    const replay = record();
    replay.frames[1].player = 0;
    replay.frames[1].action = { type: 'Build', coord: { q: 2, r: -1 } };
    replay.frames[1].state.players[0].resources.ore -= 1;
    replay.frames[1].state.players[0].resources.credits -= 2;
    replay.frames[1].state.players[0].vp += 3;
    replay.frames[1].state.players[1].resources.power.bowl3 += 2;
    const original = structuredClone(replay);
    expect(replayRewardBatches(replay, 1, 4)).toEqual([{ id: 4, player: 0,
      costs: [{ kind: 'ore', amount: 1 }, { kind: 'credits', amount: 2 }],
      gains: [{ kind: 'vp', amount: 3 }], hex: { q: 2, r: -1 } }]);
    expect(replay).toEqual(original);
    expect(replayRewardBatches(replay, 0, 5)).toEqual([]);
  });

  it('splits verified income from spending without counting income twice', () => {
    const replay = record();
    replay.frames[0].state.round = 0;
    replay.frames[1].state.players[0].resources.ore += 1;
    replay.frames[1].state.players[1].resources.knowledge += 2;
    replay.events = [{ IncomeReceived: { player: 0, ore: 3 } },
      { IncomeReceived: { player: 1, knowledge: 2 } }];
    replay.frames[1].event_end = 2;
    const batches = replayRewardBatches(replay, 1, 1);
    expect(batches[0].gains).toEqual([{ kind: 'ore', amount: 3 }]);
    expect(batches[0].costs).toEqual([{ kind: 'ore', amount: 2 }]);
    expect(batches[1].gains).toEqual([{ kind: 'knowledge', amount: 2 }]);
  });

  it('uses the immediately preceding recorded frame, not the previously viewed filtered frame', () => {
    const replay = record();
    replay.frames[1].state.players[1].resources.ore += 5;
    replay.frames[2].state = structuredClone(replay.frames[1].state);
    replay.frames[2].state.players[0].resources.qic -= 1;
    const batches = replayRewardBatches(replay, 2, 8);
    expect(batches).toHaveLength(1);
    expect(batches[0].player).toBe(0);
    expect(batches[0].costs).toEqual([{ kind: 'qic', amount: 1 }]);
    expect(batches[0].gains).toEqual([]);
  });
});
