import type { SpaceshipId } from '../types/game';

const SPACESHIP_BOARD_IMAGES = import.meta.glob('./boards/ship_faction_board_*.jpg', {
  eager: true,
  import: 'default',
}) as Record<string, string>;

/**
 * `boards/ship_faction_board_0X.jpg` (4 scans) — each prints its ship name
 * directly ("ECLIPSE", "TWILIGHT", "TF MARS", "REBELLION"), so this mapping
 * is read straight off the art, not inferred. Not to be confused with the
 * unrelated `spaceship_boards/spaceship_board_0X.jpg` (7 scans, no printed
 * names, doesn't map 1:1 to the 4 `SpaceshipId`s) — deliberately unused.
 */
const SHIP_BOARD_FILE: Record<SpaceshipId, string> = {
  Eclipse: 'ship_faction_board_01',
  Twilight: 'ship_faction_board_02',
  TFMars: 'ship_faction_board_03',
  Rebellion: 'ship_faction_board_04',
};

export function spaceshipBoardImageSrc(ship: SpaceshipId): string | null {
  const file = SHIP_BOARD_FILE[ship];
  return SPACESHIP_BOARD_IMAGES[`./boards/${file}.jpg`] ?? null;
}
