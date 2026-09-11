import { indexAssetsById } from './assetIndex';

const rendered = import.meta.glob('./tech_tiles/rendered/*.webp', {
  eager: true,
  import: 'default',
}) as Record<string, string>;

const standardTechTiles = indexAssetsById(rendered, 'std');
const advancedTechTiles = indexAssetsById(rendered, 'adv');

export function standardTechTileImageSrc(tileId: number): string | undefined {
  return standardTechTiles.get(tileId);
}

export function advancedTechTileImageSrc(tileId: number): string | undefined {
  return advancedTechTiles.get(tileId);
}
