import interspaceBlank from './interspace_tiles/normalized/01.webp';
import interspaceEclipse from './interspace_tiles/normalized/02.webp';
import interspaceTFMars from './interspace_tiles/normalized/03.webp';
import interspaceRebellion from './interspace_tiles/normalized/04.webp';
import interspaceTwilight from './interspace_tiles/normalized/05.webp';
import interspaceAsteroid from './interspace_tiles/normalized/06.webp';
import interspaceProtoPlanet from './interspace_tiles/normalized/07.webp';
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
 * - The remaining three were originally assigned by guesswork (process of
 *   elimination plus loose symbolism) and landed one slot off from the real
 *   mapping — a player reported that exploring the ship pictured on a map
 *   hex actually paid into a *different* spaceship's board, in a full
 *   3-cycle (tile showing "Rebellion" → really Eclipse; tile showing
 *   "Eclipse" → really T.F. Mars; tile showing "T.F. Mars" → really
 *   Rebellion) — cosmetic-looking but not harmless, since it made players
 *   pay the 5 VP exploration cost expecting the wrong ship's rewards/tech
 *   tile. Re-confirmed directly against each ship's own labelled board scan
 *   (`spaceshipBoardImageSrc`) by matching hull color and emblem:
 *   `interspace_02.jpg` (gold hull, ringed-planet emblem) = Eclipse
 *   (matches `ECLIPSE`'s board exactly), `interspace_03.jpg` (white hull,
 *   leaf emblem) = T.F. Mars (matches `TF MARS`'s board), `interspace_04.jpg`
 *   (tan hull, angular mask emblem) = Rebellion (matches `REBELLION`'s
 *   board).
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
