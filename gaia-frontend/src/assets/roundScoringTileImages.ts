import { indexAssetsById } from './assetIndex';

const normalized = import.meta.glob('./round_scoring_tiles/normalized/round_*.{webp,png}', {
  eager: true,
  import: 'default',
}) as Record<string, string>;

// Id 0 is the shared face-down back; ids 1-12 are the printed round tiles.
const roundTiles = indexAssetsById(normalized, 'round');

export const roundScoringTileBackImageSrc = roundTiles.get(0) as string;

export function roundScoringTileImageSrc(tileId: number): string | undefined {
  return tileId === 0 ? undefined : roundTiles.get(tileId);
}
