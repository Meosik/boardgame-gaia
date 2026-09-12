import { describe, expect, it } from 'vitest';
import { hexLocationLabel } from '../hexLocation';
import type { BoardState } from '../types/game';

function board(overrides: Partial<BoardState> = {}): BoardState {
  return {
    sectors: [
      { id: 3, rotation: 0, origin: { q: 0, r: 0 } },
      // Deep Space sectors are the 3-hex tromino [0,0], [1,0], [0,1] from their origin.
      { id: 14, rotation: 0, origin: { q: 10, r: 0 } },
    ],
    hexes: {
      '1,-1': {
        coord: { q: 1, r: -1 },
        planet: { planet_type: 'Volcanic', is_gaia_formed: false, owner: null },
        space_tile_kind: null,
        structures: [],
        satellites: [],
      },
      '10,1': {
        coord: { q: 10, r: 1 },
        planet: { planet_type: 'Ice', is_gaia_formed: false, owner: null },
        space_tile_kind: null,
        structures: [],
        satellites: [],
      },
      '30,0': {
        coord: { q: 30, r: 0 },
        planet: { planet_type: 'Asteroid', is_gaia_formed: false, owner: null },
        space_tile_kind: 'Single',
        structures: [],
        satellites: [],
      },
    },
    lost_planet: null,
    spaceship_tiles: { Twilight: { q: 20, r: 0 } },
    ...overrides,
  } as unknown as BoardState;
}

describe('hexLocationLabel', () => {
  it('names a standard sector and its planet', () => {
    expect(hexLocationLabel({ q: 1, r: -1 }, board())).toBe('3번 섹터 화산 행성');
  });

  it('names an empty hex by its sector alone', () => {
    expect(hexLocationLabel({ q: 2, r: 0 }, board())).toBe('3번 섹터');
  });

  it('marks Deep Space sectors', () => {
    expect(hexLocationLabel({ q: 10, r: 1 }, board())).toBe('심우주 14번 섹터 얼음 행성');
  });

  it('names a spaceship tile by its ship', () => {
    expect(hexLocationLabel({ q: 20, r: 0 }, board())).toBe('트와일라잇 함선 칸');
  });

  it('calls the leftover single-hex tiles Interspace, without a doubled 행성 suffix', () => {
    expect(hexLocationLabel({ q: 30, r: 0 }, board())).toBe('인터스페이스 소행성');
    expect(hexLocationLabel({ q: 31, r: 0 }, board())).toBe('인터스페이스 빈 칸');
  });

  it('reports a gaia-formed planet as Gaia', () => {
    const gaia = board();
    gaia.hexes['1,-1'].planet!.is_gaia_formed = true;
    expect(hexLocationLabel({ q: 1, r: -1 }, gaia)).toBe('3번 섹터 가이아 행성');
  });

  it('falls back to the raw coordinate without a board', () => {
    expect(hexLocationLabel({ q: 1, r: -1 })).toBe('(1,-1)');
    expect(hexLocationLabel(null)).toBe('알 수 없는 칸');
  });
});
