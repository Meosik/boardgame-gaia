import { describe, expect, it } from 'vitest';
import {
  deepSpaceSectorImageSrc,
  deepSpaceSectorSide,
  sectorImageSrc,
} from '../assets/sectorImages';
import type { BoardState, Hex, PlanetType, Sector } from '../types/game';

function hex(q: number, r: number, planetType: PlanetType | null): Hex {
  return {
    coord: { q, r },
    planet: planetType === null ? null : {
      planet_type: planetType,
      is_gaia_formed: false,
      owner: null,
    },
    space_tile_kind: null,
    structures: [],
    satellites: [],
  };
}

function boardHexes(values: Hex[]): BoardState['hexes'] {
  return Object.fromEntries(values.map((value) => [`${value.coord.q},${value.coord.r}`, value]));
}

describe('upscaled Deep Space sector images', () => {
  it('maps every standard sector to its normalized High Fidelity WebP', () => {
    for (let id = 1; id <= 10; id += 1) {
      expect(sectorImageSrc(id)).toContain(`${String(id).padStart(2, '0')}.webp`);
    }
    expect(sectorImageSrc(99)).toBeNull();
  });

  it('maps every engine side to its original-scan 2x image', () => {
    for (let id = 11; id <= 18; id += 1) {
      expect(deepSpaceSectorImageSrc(id, 'A')).toContain(`${id}-1.webp`);
      expect(deepSpaceSectorImageSrc(id, 'B')).toContain(`${id}-2.webp`);
    }
  });

  it('keeps side A as the fallback for legacy snapshots without a side', () => {
    expect(deepSpaceSectorImageSrc(11)).toContain('11-1.webp');
    expect(deepSpaceSectorImageSrc(99, 'A')).toBeNull();
  });

  it('recovers the randomized face from the rotated planet layout', () => {
    const sector: Sector = { id: 11, rotation: 1, origin: { q: 5, r: -2 } };
    const sideAHexes = boardHexes([
      hex(5, -2, 'Asteroid'),
      hex(5, -1, 'LostPlanet'),
      hex(4, -1, 'ProtoPlanet'),
    ]);
    const sideBHexes = boardHexes([
      hex(5, -2, 'Asteroid'),
      hex(5, -1, null),
      hex(4, -1, null),
    ]);

    expect(deepSpaceSectorSide(sector, sideAHexes)).toBe('A');
    expect(deepSpaceSectorSide(sector, sideBHexes)).toBe('B');
  });

  it.each([
    [11, ['Asteroid', null, 'ProtoPlanet']],
    [12, ['ProtoPlanet', null, 'Transdim']],
    [13, [null, 'Asteroid', 'Transdim']],
    [14, [null, 'Asteroid', 'ProtoPlanet']],
    [15, [null, null, 'ProtoPlanet']],
    [16, [null, 'ProtoPlanet', null]],
    [17, [null, null, 'Transdim']],
    [18, [null, null, 'ProtoPlanet']],
  ] as const)('recognizes sector %i side A from its physical scan layout', (id, planets) => {
    const sector: Sector = { id, rotation: 0, origin: { q: 0, r: 0 } };
    const hexes = boardHexes([
      hex(0, 0, planets[0]),
      hex(1, 0, planets[1]),
      hex(0, 1, planets[2]),
    ]);

    expect(deepSpaceSectorSide(sector, hexes)).toBe('A');
  });

  it.each([
    [11, ['Asteroid', null, null]],
    [12, [null, null, 'Asteroid']],
    [13, [null, 'Asteroid', null]],
    [14, [null, 'Asteroid', null]],
    [15, [null, 'Asteroid', 'ProtoPlanet']],
    [16, ['Asteroid', 'Asteroid', null]],
    [17, ['Asteroid', null, null]],
    [18, ['Asteroid', null, null]],
  ] as const)('recognizes sector %i side B from its physical scan layout', (id, planets) => {
    const sector: Sector = { id, rotation: 0, origin: { q: 0, r: 0 } };
    const hexes = boardHexes([
      hex(0, 0, planets[0]),
      hex(1, 0, planets[1]),
      hex(0, 1, planets[2]),
    ]);

    expect(deepSpaceSectorSide(sector, hexes)).toBe('B');
  });
});
