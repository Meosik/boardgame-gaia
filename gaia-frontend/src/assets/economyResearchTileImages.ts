import powerSide from './boards/normalized/economy_research_power.webp';
import victoryPointSide from './boards/normalized/economy_research_victory_points.webp';
import type { EconomyResearchTileSide } from '../types/game';

const ECONOMY_RESEARCH_TILE_IMAGES: Record<EconomyResearchTileSide, string> = {
  Power: powerSide,
  VictoryPoints: victoryPointSide,
};

export function economyResearchTileImageSrc(side: EconomyResearchTileSide): string {
  return ECONOMY_RESEARCH_TILE_IMAGES[side];
}
