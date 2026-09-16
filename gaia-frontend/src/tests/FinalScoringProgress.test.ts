import { describe, expect, it } from 'vitest';
import { decodeHexCoordinates } from '../api/websocket';
import { finalScoringMetric } from '../finalScoring';
import type { FinalScoringCondition, GameState } from '../types/game';
import fixture from './fixtures/finalScoringProgress.json';

function state(): GameState {
  return decodeHexCoordinates(structuredClone(fixture.state)) as GameState;
}

describe('final goal progress matches the Rust scoring engine', () => {
  it.each(fixture.conditions)('%s matches all four players in the shared Rust fixture', name => {
    const condition = name as FinalScoringCondition;
    const snapshot = state();
    const before = structuredClone(snapshot);
    const index = fixture.conditions.indexOf(name);
    expect(snapshot.players.map(p => finalScoringMetric(snapshot, p.player_id, condition)))
      .toEqual(fixture.expected.map(row => row[index]));
    expect(snapshot).toEqual(before);
  });

  it('uses the same formation membership in replay decision history, without counting satellites or later attachments', () => {
    const snapshot = state();
    snapshot.event_log = fixture.state.event_log.map(event => ({ ReplayDecision: {
      player: event.FederationFormed.player,
      action: { type: 'FormFederation', hexes: decodeHexCoordinates(event.FederationFormed.hexes) },
    } }));
    for (const p of snapshot.players) {
      expect(finalScoringMetric(snapshot, p.player_id, 'MostStructuresInFederation'))
        .toBe(fixture.expected[p.player_id][0]);
    }
    // A restored earlier history must not retain formation progress from the future.
    snapshot.event_log = [];
    expect(finalScoringMetric(snapshot, 1, 'MostStructuresInFederation')).toBe(0);
  });

  it('does not double-count an already tracked Lost Planet', () => {
    const snapshot = state();
    snapshot.players[1].structures.push({ hex: { q: 21, r: 0 }, kind: 'Mine' });
    expect(finalScoringMetric(snapshot, 1, 'MostBuildings')).toBe(fixture.expected[1][1]);
    expect(finalScoringMetric(snapshot, 1, 'MostStructuresInFederation')).toBe(fixture.expected[1][0]);
  });

  it('handles missing players, no PI/academy pair, and optional empty artifact/history fields', () => {
    const snapshot = state();
    expect(finalScoringMetric(snapshot, 99, 'MostBuildings')).toBe(0);
    expect(finalScoringMetric(snapshot, 0, 'GreatestDistancePiAcademy')).toBe(0);
    snapshot.event_log = undefined;
    snapshot.players[0].artifact_mines = undefined;
    expect(finalScoringMetric(snapshot, 0, 'MostStructuresInFederation')).toBe(0);
    expect(finalScoringMetric(snapshot, 0, 'MostBuildings')).toBe(4);
  });

  it('uses all six rotations of the three-hex deep-space footprint, not its enclosing radius', () => {
    for (let rotation = 0; rotation < 6; rotation++) {
      const snapshot = state();
      snapshot.board.sectors = [{ id: 11, origin: { q: 0, r: 0 }, rotation }];
      snapshot.players[3].structures = [];
      const cells = Object.values(snapshot.board.hexes);
      for (const cell of cells) if (cell.planet) cell.planet.owner = null;
      const tip = { q: 2, r: 0 };
      snapshot.board.hexes['2,0'] = { coord: tip, planet: { planet_type: 'Asteroid', owner: 3, is_gaia_formed: false },
        structures: [], satellites: [], space_tile_kind: null };
      expect(finalScoringMetric(snapshot, 3, 'MostDeepSpaceSectors')).toBe(0);
      snapshot.board.hexes['0,0'].planet!.owner = 3;
      expect(finalScoringMetric(snapshot, 3, 'MostDeepSpaceSectors')).toBe(1);
    }
  });
});
