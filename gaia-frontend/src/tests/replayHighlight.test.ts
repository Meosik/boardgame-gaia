import { describe, expect, it } from 'vitest';
import { parseReplay } from '../replay/records';
import { replayHighlight } from '../replay/highlight';
import fixture from './fixtures/replay.json';

const initial = parseReplay(fixture).frames[0];
function move(action: NonNullable<typeof initial.action>) {
  return { ...structuredClone(initial), player: 0, action };
}
describe('replay move highlighting', () => {
  it('has no marks initially and follows the selected frame, not cumulative history', () => {
    expect(replayHighlight(initial).hexes.size).toBe(0);
    const first = move({ type: 'Build', coord: { q: 1, r: -2 } });
    const next = move({ type: 'Build', coord: { q: 3, r: 0 } });
    expect([...replayHighlight(first, initial).hexes]).toEqual(['1,-2']);
    expect([...replayHighlight(next, first).hexes]).toEqual(['3,0']);
    expect([...replayHighlight(first, initial).hexes]).toEqual(['1,-2']);
    expect(replayHighlight(move({ type: 'Pass' }), initial).hexes.size).toBe(0);
  });
  it('marks all federation and satellite coordinates, including zero and negative coordinates', () => {
    const result = replayHighlight(move({ type: 'FormFederation', hexes: [{ q: 0, r: 0 }], satellite_hexes: [{ q: -1, r: 2 }] }), initial);
    expect([...result.hexes]).toEqual(['0,0', '-1,2']);
  });
  it('labels upgrades and highlights actual research changes for only the actor', () => {
    const before = structuredClone(initial);
    before.state.players[0].structures = [{ hex: { q: 1, r: 2 }, kind: 'TradingStation' }];
    const after = structuredClone(before);
    after.player = 0;
    after.action = { type: 'Upgrade', coord: { q: 1, r: 2 }, to: 'ResearchLab' };
    after.state.players[0].structures[0].kind = 'ResearchLab';
    after.state.players[0].research_tracks.economy += 1;
    after.state.players[1].research_tracks.science += 1;
    const result = replayHighlight(after, before);
    expect(result.label).toBe('교역소 → 연구소');
    expect([...result.research]).toEqual(['economy']);
    expect(result.hexes.has('1,2')).toBe(true);
  });
  it('identifies power and ship targets without retaining previous targets', () => {
    expect(replayHighlight(move({ type: 'PowerAction', id: 3 })).powerAction).toBe(3);
    expect(replayHighlight(move({ type: 'ExploreSpaceship', ship: 'Twilight' })).ship).toBe('Twilight');
    expect(replayHighlight(move({ type: 'Pass' })).powerAction).toBeNull();
  });
});

it('distinguishes newly acquired and used technology pools and clears on the next move', () => {
  const before = structuredClone(initial);
  before.state.players[0].tech_tiles = [1];
  before.state.players[0].advanced_tech_tiles = [];
  const after = structuredClone(before);
  after.player = 0;
  after.action = { type: 'Upgrade' };
  after.state.players[0].tech_tiles = [1, 8];
  after.state.players[0].advanced_tech_tiles = [20];
  expect([...replayHighlight(after, before).standardTech]).toEqual([8]);
  expect([...replayHighlight(after, before).advancedTech]).toEqual([20]);
  const used = structuredClone(after);
  used.action = { type: 'TechTileSpecialAction', tile: { pool: 'Standard', tile: 10 } };
  expect([...replayHighlight(used, after).standardTech]).toEqual([10]);
  expect(replayHighlight(used, after).advancedTech.size).toBe(0);
  const pass = { ...used, action: { type: 'Pass' } };
  expect(replayHighlight(pass, used).standardTech.size).toBe(0);
});

it('marks the selected booster on initial selection and passing, then clears it', () => {
  for (const type of ['Pass', 'SelectStartingBooster']) {
    expect(replayHighlight(move({type, booster_id: 8}), initial).booster).toBe(8);
  }
  expect(replayHighlight(move({type: 'Build'}), initial).booster).toBeNull();
});
