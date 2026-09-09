import type { SpaceshipId } from '../types/game';
import eclipseBoard from './boards/normalized/spaceship_eclipse.webp';
import tfMarsBoard from './boards/normalized/spaceship_tf_mars.webp';
import rebellionBoard from './boards/normalized/spaceship_rebellion.webp';
import twilightBoard from './boards/normalized/spaceship_twilight.webp';

/** Each supplied board prints its ship name directly in the upper-left corner. */
const SHIP_BOARD_IMAGE: Record<SpaceshipId, string> = {
  Eclipse: eclipseBoard,
  Twilight: twilightBoard,
  TFMars: tfMarsBoard,
  Rebellion: rebellionBoard,
};

export function spaceshipBoardImageSrc(ship: SpaceshipId): string | null {
  return SHIP_BOARD_IMAGE[ship] ?? null;
}
