import interspaceBlank from './interspace_tiles/interspace_01.jpg';
import interspaceTFMars from './interspace_tiles/interspace_02.jpg';
import interspaceRebellion from './interspace_tiles/interspace_03.jpg';
import interspaceEclipse from './interspace_tiles/interspace_04.jpg';
import interspaceTwilight from './interspace_tiles/interspace_05.jpg';
import interspaceAsteroid from './interspace_tiles/interspace_06.jpg';
import interspaceProtoPlanet from './interspace_tiles/interspace_07.jpg';
import type { SpaceshipId } from '../types/game';

/**
 * The 7 physical Interspace tile faces (Lost Fleet expansion, rulebook p.5:
 * "Front: Tile with a Lost Fleet spaceship [x4] / Tile with a planet
 * (Protoplanet, Asteroid) [x2] / Blank tile [x1]") that fill the 10 single-
 * hex holes in the 4-player variable board layout — a hole not covered by
 * any Space/Deep Space sector's own art (see `GameBoard`'s `printedHexKeys`).
 *
 * Identified by viewing each scan directly, same as the Space Sector fix:
 * - `interspace_01.jpg` = the plain starfield tile = Blank (unambiguous).
 * - `interspace_06.jpg` = a jagged rock cluster = Asteroid (unambiguous,
 *   matches this project's other Asteroid art, e.g. `final_scoring_06`).
 * - `interspace_07.jpg` = a glowing swirling sphere = ProtoPlanet
 *   (unambiguous, matches this project's Transdim/ProtoPlanet art style).
 * - `interspace_05.jpg` (purple hull, nautilus-shell emblem) = Twilight —
 *   confirmed against a reference screenshot showing that exact nautilus
 *   emblem next to a "TWILIGHT" label.
 * - `interspace_02.jpg` (tan hull, ringed-planet emblem) = T.F. Mars,
 *   `interspace_03.jpg` (white hull, leaf emblem) = Rebellion,
 *   `interspace_04.jpg` (gold hull, crescent emblem) = Eclipse —
 *   these three are NOT independently confirmed (no reference showed their
 *   emblems), only inferred from the process of elimination plus loose
 *   symbolism (crescent ~ "Eclipse"). Wrong here just means the wrong one of
 *   the 4 hull designs shows through the map on that ship's own interspace
 *   hex — cosmetic, not a game-data bug — but worth fixing for real if
 *   there's a way to check against the physical tiles.
 */
const SPACESHIP_INTERSPACE_IMAGES: Record<SpaceshipId, string> = {
  Twilight: interspaceTwilight,
  Rebellion: interspaceRebellion,
  TFMars: interspaceTFMars,
  Eclipse: interspaceEclipse,
};

export function spaceshipInterspaceImageSrc(ship: SpaceshipId): string {
  return SPACESHIP_INTERSPACE_IMAGES[ship];
}

export function asteroidInterspaceImageSrc(): string {
  return interspaceAsteroid;
}

export function protoPlanetInterspaceImageSrc(): string {
  return interspaceProtoPlanet;
}

export function blankInterspaceImageSrc(): string {
  return interspaceBlank;
}
