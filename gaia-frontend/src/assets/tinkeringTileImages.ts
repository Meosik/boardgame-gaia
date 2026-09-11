import { indexAssetsById } from './assetIndex';

const normalized = import.meta.glob('./tinkering_tiles/normalized/tile_*.webp', {
  eager: true,
  import: 'default',
  query: '?url',
}) as Record<string, string>;

const tinkeringTiles = indexAssetsById(normalized, 'tile');

/**
 * Returns the Tinkering tile image for the engine's tile id.
 *
 * The supplied upscale filenames followed scan order rather than the engine's effect ids, so both
 * the originals and the normalized files are named by engine id: 2=QIC 1, 3=charge 4, 4=QIC 2,
 * 5=build with 3 free terraforming steps.
 */
export function tinkeringTileImageSrc(tileId: number): string | undefined {
  return tinkeringTiles.get(tileId);
}
