import explorationShuttlesSide from './boards/normalized/lost_fleet_tech_requirement_shuttles.webp';
import victoryPointsSide from './boards/normalized/lost_fleet_tech_requirement_victory_points.webp';

export type LostFleetTechRequirementSide = 'exploration-shuttles' | '25-vp';

const REQUIREMENT_BOARD_IMAGE: Record<LostFleetTechRequirementSide, string> = {
  'exploration-shuttles': explorationShuttlesSide,
  '25-vp': victoryPointsSide,
};

export function lostFleetTechRequirementBoardImageSrc(
  side: LostFleetTechRequirementSide,
): string {
  return REQUIREMENT_BOARD_IMAGE[side];
}
