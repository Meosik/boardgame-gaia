import { describe, expect, it } from 'vitest';
import raw from './setup-replay.json';
import { parseReplay } from '../../src/replay/records';
import { deepSpaceSectorSide } from '../../src/assets/sectorImages';
import { TERRAFORMING_SATELLITE_COLOR } from '../../src/assets/terraformingBoard';

describe('observed uiqoo setup 145526867337', () => {
  const replay = parseReplay(raw);
  const state = replay.frames[0].state;
  it('loads through the real replay parser without inventing a match', () => {
    expect(replay.frames).toHaveLength(1);
    expect(replay.events).toEqual([]);
    expect(replay.metadata.steps).toBe(0);
    expect(state.players.every(p => p.faction === null && p.structures.length === 0)).toBe(true);
    expect(state.bidding).toBeNull();
    expect(state.faction_selection?.available_factions).toEqual(['Geodens', 'Tinkeroids', 'HadschHallas', 'Moweyds']);
    expect(state.faction_selection?.assignments).toEqual([]);
    expect(Object.values(state.board.hexes)).toHaveLength(224);
    expect(state.board.sectors).toHaveLength(18);
  });
  it('preserves all observed outer-sector faces in the existing renderer', () => {
    for (const source of raw.metadata.versions.source_observation.sectors.filter(s => s.sector_id > 10)) {
      const sector = state.board.sectors.find(s => s.id === source.sector_id)!;
      expect(deepSpaceSectorSide(sector, state.board.hexes)).toBe(source.side);
    }
  });
  it('does not reshuffle technology, ship rewards or source-specific board faces', () => {
    expect(state.research_board.tech_tile_slots).toEqual([3, 2, 9, 8, 5, 10, 6, 7, 4]);
    expect(state.research_board.advanced_tech_tiles).toEqual([7, 9, 13, 3, 8, 5]);
    expect(state.research_board.lost_fleet_advanced_tech_tile).toBe(19);
    expect(state.research_board.lost_fleet_advanced_tech_requirement).toBe('25-vp');
    expect(state.research_board.economy_research_tile_side).toBe('VictoryPoints');
    expect(state.terraforming_color_order).toEqual(['Terra', 'Swamp', 'Titanium', 'Oxide', 'Ice', 'Desert', 'Volcanic']);
    expect(state.terraforming_color_order?.map(p => TERRAFORMING_SATELLITE_COLOR[p]))
      .toEqual(['blue', 'brown', 'gray', 'red', 'white', 'yellow', 'orange']);
    expect(state.research_board.terraforming_level_5_token).toBe(2);
    expect(state.research_board.federation_tokens).toHaveLength(17);
    const ships = Object.fromEntries(state.spaceship_boards.map(s => [s.id, s]));
    expect(ships.Twilight.artifact_pool).toEqual([12, 6, 8, 3]);
    expect([ships.Twilight, ships.Eclipse, ships.TFMars, ships.Rebellion].map(s => s.federation_token))
      .toEqual([11, 8, 12, 14]);
    expect([ships.Eclipse, ships.TFMars, ships.Rebellion].map(s => s.tech_tiles))
      .toEqual([[12, 12, 12, 12], [13, 13, 13, 13], [11, 11, 11, 11]]);
  });
});
