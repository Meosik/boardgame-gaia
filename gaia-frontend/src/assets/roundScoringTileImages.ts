import tile10 from './round_scoring_tiles/round_scoring_10_tile.webp';
import tile11 from './round_scoring_tiles/round_scoring_11_tile.webp';
import tile12 from './round_scoring_tiles/round_scoring_12_tile.webp';

const images: Record<number, string> = {
  1: '/assets/gaiaproject/round_mine2.png',
  2: '/assets/gaiaproject/round_terra2.png',
  3: '/assets/gaiaproject/round_gaia4.png',
  4: '/assets/gaiaproject/round_trade3.png',
  5: '/assets/gaiaproject/round_fed5.png',
  6: '/assets/gaiaproject/round_big5.png',
  7: '/assets/gaiaproject/round_gaia3.png',
  8: '/assets/gaiaproject/round_trade4.png',
  9: '/assets/gaiaproject/round_adv2.png',
  10: tile10,
  11: tile11,
  12: tile12,
};

export function roundScoringTileImageSrc(tileId: number): string | undefined {
  return images[tileId];
}
