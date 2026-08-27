import tile02 from './final_scoring_tiles/final_scoring_02_tile.webp';
import tile06 from './final_scoring_tiles/final_scoring_06_tile.webp';
import tile09 from './final_scoring_tiles/final_scoring_09_tile.webp';

const images: Record<number, string> = {
  1: '/assets/gaiaproject/final_gaia.png',
  2: tile02,
  3: '/assets/gaiaproject/final_fed.png',
  4: '/assets/gaiaproject/final_planet.png',
  5: '/assets/gaiaproject/final_building.png',
  6: tile06,
  8: '/assets/gaiaproject/final_sector.png',
  9: tile09,
  10: '/assets/gaiaproject/final_satellite.png',
};

export function finalScoringTileImageSrc(tileId: number): string | undefined {
  return images[tileId];
}
