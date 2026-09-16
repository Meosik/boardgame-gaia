import { describe, expect, it } from 'vitest';
import native from './fixtures/xenos140Settlement.json';
import fixture from './fixtures/replay.json';
import { parseReplay } from '../replay/records';
import { buildReplaySettlement, rankAwards, settlementState, adjacentReplayPosition } from '../replay/settlement';

function completed() {
  // One actual terminal snapshot; no claim this test fixture replays earlier actions.
  return parseReplay({ ...fixture, metadata: { ...fixture.metadata, steps: 0 }, events: [],
    frames: [{ ...fixture.frames[0], state: native.state, event_end: 0 }] });
}

describe('replay-only final settlement', () => {
  it('matches native Xenos140 in five explicit stages without modifying the record', () => {
    const record = completed();
    const original = JSON.stringify(record);
    const result = buildReplaySettlement(record);
    expect(result.warning).toBeUndefined();
    expect(result.steps.map(s => s.kind)).toEqual(['goal', 'goal', 'research', 'resources', 'ranking']);
    expect(result.steps.map(s => s.awards.find(a => a.player === 2)?.amount)).toEqual([18, 18, 28, 0, 0]);
    expect(result.steps.map(s => s.awards.find(a => a.player === 2)?.total)).toEqual([94, 112, 140, 140, 140]);
    expect(result.steps[0].awards.find(a => a.player === 2)?.detail).toContain('6');
    expect(result.steps[1].awards.find(a => a.player === 2)?.detail).toContain('4');
    expect(result.steps[4].awards.map(a => [a.player, a.total])).toEqual([[2, 140], [1, 52], [3, 41], [0, 29]]);
    const view = settlementState(record.frames[0].state, result.steps[0]);
    expect(view.players[2].vp).toBe(94);
    expect(view.players[2].resources).toEqual(record.frames[0].state.players[2].resources);
    expect(JSON.stringify(record)).toBe(original);
  });

  it('pools occupied ranks for ties including all-zero metrics', () => {
    expect(rankAwards([4, 4, 1, 0], [18, 12, 6, 0]).map(a => [a.rank, a.amount])).toEqual([[1, 15], [1, 15], [3, 6], [4, 0]]);
    expect(rankAwards([0, 0, 0, 0], [18, 12, 6, 0]).map(a => a.amount)).toEqual([9, 9, 9, 9]);
    expect(rankAwards([1, 1, 1, 0], [18, 12, 6, 0]).map(a => a.amount)).toEqual([12, 12, 12, 0]);
  });

  it('does not manufacture end scoring for a partial game or a mismatched total', () => {
    expect(buildReplaySettlement(parseReplay(fixture)).steps).toEqual([]);
    const record = completed();
    if (typeof record.frames[0].state.phase === 'object' && 'Ended' in record.frames[0].state.phase) {
      record.frames[0].state.phase.Ended.final_scores[2][1] += 1;
    }
    const result = buildReplaySettlement(record);
    expect(result.steps).toEqual([]);
    expect(result.warning).toContain('최종 점수');
  });

  it('applies the existing auction deduction once at the final ranking and rewinds cleanly', () => {
    const record = completed();
    const state = record.frames[0].state;
    state.players[2].setup_bid_vp = 3;
    if (typeof state.phase === 'object' && 'Ended' in state.phase) state.phase.Ended.final_scores[2][1] = 137;
    const result = buildReplaySettlement(record);
    expect(result.steps[4].awards.find(a => a.player === 2)?.amount).toBe(-3);
    expect(settlementState(state, result.steps[4]).players[2].vp).toBe(137);
    expect(settlementState(state, result.steps[0]).players[2].vp).toBe(94);
    expect(state.players[2].vp).toBe(76);
  });

  it('recovers formation membership from actions when an older event log omits decisions', () => {
    const record = completed();
    const original = buildReplaySettlement(record);
    const state = record.frames[0].state;
    state.final_scoring_tiles[0].condition = 'MostStructuresInFederation';
    if (typeof state.phase === 'object' && 'Ended' in state.phase) {
      for (const pair of state.phase.Ended.final_scores) {
        pair[1] += (pair[0] === 2 ? 18 : 6) - original.steps[0].awards.find(a => a.player === pair[0])!.amount;
      }
    }
    expect(buildReplaySettlement(record).warning).toBeDefined();
    record.frames.push({ ...record.frames[0], decision_id: 1, player: 2,
      action: { type: 'FormFederation', hexes: [state.players[2].structures[0].hex] } });
    record.metadata.steps = 1;
    const result = buildReplaySettlement(record);
    expect(result.warning).toBeUndefined();
    expect(result.steps[0].awards.find(a => a.player === 2)?.detail).toBe('1위 · 달성 1');
    record.events.push({ ReplayDecision: { player: 2, action: record.frames[1].action } });
    expect(buildReplaySettlement(record).steps).toEqual(result.steps.map(s => ({ ...s, eventStart: s.eventStart + 1, eventEnd: s.eventEnd + 1 })));
  });

  it('reaches the final pass and every global settlement step through actor filters', () => {
    const base = completed().frames[0];
    const frames = [null, 0, 1, 0, 2].map((player, index) => ({ ...base, player,
      action: index ? { type: 'Pass' } : null, decision_id: index }));
    expect(adjacentReplayPosition(frames, 3, 1, 0, 5)).toBe(4);
    expect(adjacentReplayPosition(frames, 4, 1, 0, 5)).toBe(5);
    expect(adjacentReplayPosition(frames, 5, -1, 0, 5)).toBe(4);
    expect(adjacentReplayPosition(frames, 4, -1, 0, 5)).toBe(3);
    expect(adjacentReplayPosition(frames, 9, 1, 0, 5)).toBeNull();
    expect(adjacentReplayPosition(frames, 3, 1, 0, 0)).toBeNull();
  });
});
