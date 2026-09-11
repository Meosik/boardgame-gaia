import { indexAssetsById } from './assetIndex';

// Ids follow `FinalScoringTile::IDS` in gaia-engine (1-6, 8-10; there is no tile 7).
const finalScoringTiles = indexAssetsById(
  import.meta.glob('./final_scoring_tiles/normalized/final_*.webp', {
    eager: true,
    import: 'default',
  }) as Record<string, string>,
  'final',
);

export function finalScoringTileImageSrc(tileId: number): string | undefined {
  return finalScoringTiles.get(tileId);
}
