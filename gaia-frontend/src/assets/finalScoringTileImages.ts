import tile01 from './final_scoring_tiles/normalized/final_01.webp';
import tile02 from './final_scoring_tiles/normalized/final_02.webp';
import tile03 from './final_scoring_tiles/normalized/final_03.webp';
import tile04 from './final_scoring_tiles/normalized/final_04.webp';
import tile05 from './final_scoring_tiles/normalized/final_05.webp';
import tile06 from './final_scoring_tiles/normalized/final_06.webp';
import tile08 from './final_scoring_tiles/normalized/final_08.webp';
import tile09 from './final_scoring_tiles/normalized/final_09.webp';
import tile10 from './final_scoring_tiles/normalized/final_10.webp';

const images: Record<number, string> = {
  1: tile01,
  2: tile02,
  3: tile03,
  4: tile04,
  5: tile05,
  6: tile06,
  8: tile08,
  9: tile09,
  10: tile10,
};

export function finalScoringTileImageSrc(tileId: number): string | undefined {
  return images[tileId];
}
