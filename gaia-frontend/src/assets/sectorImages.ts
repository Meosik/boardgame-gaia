import spaceSector01 from './space_sectors/normalized/01.webp';
import spaceSector02 from './space_sectors/normalized/02.webp';
import spaceSector03 from './space_sectors/normalized/03.webp';
import spaceSector04 from './space_sectors/normalized/04.webp';
import spaceSector05 from './space_sectors/normalized/05.webp';
import spaceSector06 from './space_sectors/normalized/06.webp';
import spaceSector07 from './space_sectors/normalized/07.webp';
import spaceSector08 from './space_sectors/normalized/08.webp';
import spaceSector09 from './space_sectors/normalized/09.webp';
import spaceSector10 from './space_sectors/normalized/10.webp';
import deepSpace11A from './deep_space_sectors/normalized/11-1.webp';
import deepSpace11B from './deep_space_sectors/normalized/11-2.webp';
import deepSpace12A from './deep_space_sectors/normalized/12-1.webp';
import deepSpace12B from './deep_space_sectors/normalized/12-2.webp';
import deepSpace13A from './deep_space_sectors/normalized/13-1.webp';
import deepSpace13B from './deep_space_sectors/normalized/13-2.webp';
import deepSpace14A from './deep_space_sectors/normalized/14-1.webp';
import deepSpace14B from './deep_space_sectors/normalized/14-2.webp';
import deepSpace15A from './deep_space_sectors/normalized/15-1.webp';
import deepSpace15B from './deep_space_sectors/normalized/15-2.webp';
import deepSpace16A from './deep_space_sectors/normalized/16-1.webp';
import deepSpace16B from './deep_space_sectors/normalized/16-2.webp';
import deepSpace17A from './deep_space_sectors/normalized/17-1.webp';
import deepSpace17B from './deep_space_sectors/normalized/17-2.webp';
import deepSpace18A from './deep_space_sectors/normalized/18-1.webp';
import deepSpace18B from './deep_space_sectors/normalized/18-2.webp';
import { rotateHexN } from '../components/GameBoard/hex-utils';
import type { BoardState, PlanetType, Sector } from '../types/game';

/**
 * Sector image -> sector NN, confirmed by the number printed on
 * each tile's own scan (the original scan-order filenames were mismatched —
 * `space_sector_01.jpg` used to show a tile printed "09" — since fixed by
 * renaming each file to match its printed id directly). All ten sectors use
 * 2600x2820 runtime WebP files derived from the reviewed High Fidelity 4x
 * masters; the PNG files remain source/reference material.
 * Sectors 5/6/7 are
 * double-sided in the physical game and 4-player Lost Fleet setup always
 * uses side "A" specifically (`sectors.toml`); these three scans are
 * whichever side was rescanned/kept for this filename, not independently
 * re-verified against `sectors.toml`'s side-A hex list.
 */
const STANDARD_SECTOR_IMAGES: Record<number, string> = {
  1: spaceSector01,
  2: spaceSector02,
  3: spaceSector03,
  4: spaceSector04,
  5: spaceSector05,
  6: spaceSector06,
  7: spaceSector07,
  8: spaceSector08,
  9: spaceSector09,
  10: spaceSector10,
};

/** Sector ids 11-18 (Lost Fleet expansion, `gaia-engine/data/sectors.toml`).
 * The original-scan `-1` image is side A and `-2` is side B. These deterministic
 * 2x assets share one canvas, mask, and three-hex junction coordinate. */
const DEEP_SPACE_SECTOR_IMAGES: Record<number, Record<'A' | 'B', string>> = {
  11: { A: deepSpace11A, B: deepSpace11B },
  12: { A: deepSpace12A, B: deepSpace12B },
  13: { A: deepSpace13A, B: deepSpace13B },
  14: { A: deepSpace14A, B: deepSpace14B },
  15: { A: deepSpace15A, B: deepSpace15B },
  16: { A: deepSpace16A, B: deepSpace16B },
  17: { A: deepSpace17A, B: deepSpace17B },
  18: { A: deepSpace18A, B: deepSpace18B },
};

const DEEP_SPACE_SIDE_A_PLANETS: Record<number, [PlanetType | null, PlanetType | null, PlanetType | null]> = {
  11: ['Asteroid', null, 'ProtoPlanet'],
  12: ['ProtoPlanet', null, 'Transdim'],
  13: [null, 'Asteroid', 'Transdim'],
  14: [null, 'Asteroid', 'ProtoPlanet'],
  15: [null, null, 'ProtoPlanet'],
  16: [null, 'ProtoPlanet', null],
  17: [null, null, 'Transdim'],
  18: [null, null, 'ProtoPlanet'],
};

const DEEP_SPACE_SIDE_B_PLANETS: Record<number, [PlanetType | null, PlanetType | null, PlanetType | null]> = {
  11: ['Asteroid', null, null],
  12: [null, null, 'Asteroid'],
  13: [null, 'Asteroid', null],
  14: [null, 'Asteroid', null],
  15: [null, 'Asteroid', 'ProtoPlanet'],
  16: [null, 'Asteroid', 'Asteroid'],
  17: ['Asteroid', null, null],
  18: ['Asteroid', null, null],
};

const DEEP_SPACE_LOCAL_HEXES: [number, number][] = [[0, 0], [1, 0], [0, 1]];

/** `Sector` snapshots omit their setup-only side field. Recover the selected
 * face from the actual Asteroid/ProtoPlanet layout inserted by the engine. */
export function deepSpaceSectorSide(
  sector: Sector,
  hexes: BoardState['hexes'],
): 'A' | 'B' {
  const sideA = DEEP_SPACE_SIDE_A_PLANETS[sector.id];
  const sideB = DEEP_SPACE_SIDE_B_PLANETS[sector.id];
  if (!sideA || !sideB) return 'A';

  const boardHexes = Object.values(hexes);
  let sideAMatches = 0;
  let sideBMatches = 0;
  let sideADiscriminators = 0;
  let sideBDiscriminators = 0;
  DEEP_SPACE_LOCAL_HEXES.forEach(([q, r], index) => {
    const expectedA = sideA[index];
    const expectedB = sideB[index];
    if (expectedA === expectedB) return;
    if (expectedA !== null) sideADiscriminators += 1;
    if (expectedB !== null) sideBDiscriminators += 1;
    const [rotatedQ, rotatedR] = rotateHexN(q, r, sector.rotation);
    const worldQ = sector.origin.q + rotatedQ;
    const worldR = sector.origin.r + rotatedR;
    const hex = boardHexes.find((candidate) => (
      candidate.coord.q === worldQ && candidate.coord.r === worldR
    ));
    const actual = hex?.planet?.planet_type ?? null;
    if (expectedA !== null && actual === expectedA) sideAMatches += 1;
    if (expectedB !== null && actual === expectedB) sideBMatches += 1;
  });

  if (sideAMatches > sideBMatches) return 'A';
  if (sideBMatches > sideAMatches) return 'B';
  // If one face's distinguishing cell is blank, a Lost Planet may later
  // occupy it. Prefer the face that requires no missing printed planet.
  return sideADiscriminators <= sideBDiscriminators ? 'A' : 'B';
}

/** Resolve the scanned photo for a standard Space Sector (ids 1-10) — see
 * the mapping comment above for the side-A caveat on sectors 5-7. */
export function sectorImageSrc(id: number): string | null {
  return STANDARD_SECTOR_IMAGES[id] ?? null;
}

/** Resolve the scanned photo for a Deep Space sector (ids 11-18). Unlike
 * `sectorImageSrc`'s 19-hex standard sectors, these are a 3-hex L-tromino —
 * see `sectorCentroidPixel` (`hex-utils.ts`) for how the image gets
 * positioned/sized against that much smaller footprint. */
export function deepSpaceSectorImageSrc(id: number, side?: 'A' | 'B' | null): string | null {
  const images = DEEP_SPACE_SECTOR_IMAGES[id];
  if (!images) return null;
  return images[side === 'B' ? 'B' : 'A'];
}
