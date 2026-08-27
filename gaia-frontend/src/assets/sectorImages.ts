import spaceSector01 from './space_sectors/space_sector_01.jpg';
import spaceSector02 from './space_sectors/space_sector_02.jpg';
import spaceSector03 from './space_sectors/space_sector_03.jpg';
import spaceSector04 from './space_sectors/space_sector_04.jpg';
import spaceSector05 from './space_sectors/space_sector_05.jpg';
import spaceSector06 from './space_sectors/space_sector_06.jpg';
import spaceSector07 from './space_sectors/space_sector_07.jpg';
import spaceSector08 from './space_sectors/space_sector_08.jpg';
import spaceSector09 from './space_sectors/space_sector_09.jpg';
import spaceSector10 from './space_sectors/space_sector_10.jpg';
import deepSpace01 from './deep_space_sectors/deep_space_sector_01.jpg';
import deepSpace02 from './deep_space_sectors/deep_space_sector_02.jpg';
import deepSpace03 from './deep_space_sectors/deep_space_sector_03.jpg';
import deepSpace04 from './deep_space_sectors/deep_space_sector_04.jpg';
import deepSpace05 from './deep_space_sectors/deep_space_sector_05.jpg';
import deepSpace06 from './deep_space_sectors/deep_space_sector_06.jpg';
import deepSpace07 from './deep_space_sectors/deep_space_sector_07.jpg';
import deepSpace08 from './deep_space_sectors/deep_space_sector_08.jpg';

/**
 * `space_sector_NN.jpg` -> sector NN, confirmed by the number printed on
 * each tile's own scan (the original scan-order filenames were mismatched —
 * `space_sector_01.jpg` used to show a tile printed "09" — since fixed by
 * renaming each file to match its printed id directly). Sectors 5/6/7 are
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

/** Sector ids 11-18 (Lost Fleet expansion, `gaia-engine/data/sectors.toml`),
 * mapped to the physically-scanned tile photos at
 * `gaia-frontend/src/assets/deep_space_sectors/`. Side "A" vs "B" isn't
 * distinguished here (both sides show the same 3-hex layout with the
 * Asteroid/ProtoPlanet swapped between the two non-empty hexes — visually
 * near-identical from this distance, and `Sector` doesn't carry which side
 * was placed), so every deep-space sector always renders its "front" scan. */
const DEEP_SPACE_SECTOR_IMAGES: Record<number, string> = {
  11: deepSpace01,
  12: deepSpace02,
  13: deepSpace03,
  14: deepSpace04,
  15: deepSpace05,
  16: deepSpace06,
  17: deepSpace07,
  18: deepSpace08,
};

/** Resolve the scanned photo for a standard Space Sector (ids 1-10) — see
 * the mapping comment above for the side-A caveat on sectors 5-7. */
export function sectorImageSrc(id: number): string | null {
  return STANDARD_SECTOR_IMAGES[id] ?? null;
}

/** Resolve the scanned photo for a Deep Space sector (ids 11-18). Unlike
 * `sectorImageSrc`'s 19-hex standard sectors, these are a 3-hex L-tromino —
 * see `sectorCentroidPixel` (`hex-utils.ts`) for how the image gets
 * positioned/sized against that much smaller footprint. */
export function deepSpaceSectorImageSrc(id: number): string | null {
  return DEEP_SPACE_SECTOR_IMAGES[id] ?? null;
}
