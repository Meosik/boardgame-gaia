import { describe, it, expect } from 'vitest';
import fixture from './fixtures/replay.json';
import { frameForEvent, parseCatalog, parseReplay } from '../replay/records';
import { replayHighlight } from '../replay/highlight';

describe('AI replay recording boundary', () => {
  it('labels booster 12 as terraforming construction and highlights its target', () => {
    const replay = parseReplay(fixture);
    const frame = { ...replay.frames[1], action: {
      type: 'RoundBoosterTerraformBuild', coord: { q: 1, r: 0 },
    } };
    const highlight = replayHighlight(frame);
    expect(highlight.label).toBe('부스터 광산 건설 (테라포밍 1단계 무료)');
    expect(highlight.hexes.has('1,0')).toBe(true);
  });

  it('decodes native coordinates and maps log entries to resulting actions', () => {
    const replay = parseReplay(fixture);
    expect(replay.frames).toHaveLength(3);
    const hex = Object.values(replay.frames[0].state.board.hexes)[0];
    expect(typeof hex.coord.q).toBe('number');
    expect(frameForEvent(replay.frames, replay.frames[0].event_end)).toBe(1);
    expect(frameForEvent(replay.frames, replay.frames[1].event_end)).toBe(2);
  });
  it('rejects unknown schema and corrupt state, sequence and event ranges', () => {
    for (const corrupt of [
      { ...fixture, schema_version: 2 },
      { ...fixture, frames: [] },
      { ...fixture, frames: [{ ...fixture.frames[0], state: {} }, ...fixture.frames.slice(1)] },
      { ...fixture, frames: [{ ...fixture.frames[0], event_end: 99999 }, ...fixture.frames.slice(1)] },
      { ...fixture, frames: [fixture.frames[0], { ...fixture.frames[1], decision_id: 80 }, fixture.frames[2]] },
    ]) expect(() => parseReplay(corrupt)).toThrow();
  });
  it('restricts catalog files to local replay filenames', () => {
    const game = { id: 'one', file: 'one.json.gz', policy: 'teacher', faction: 'Xenos', seed: 'seed', vp: 20, steps: 2 };
    expect(parseCatalog({ schema_version: 1, games: [game] })).toEqual([game]);
    expect(() => parseCatalog({ schema_version: 1, games: [{ ...game, file: '../secret.json.gz' }] })).toThrow();
    expect(() => parseCatalog({ schema_version: 1, games: [game, game] })).toThrow();
  });
});
