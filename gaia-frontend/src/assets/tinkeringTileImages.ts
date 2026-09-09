const normalized = import.meta.glob('./tinkering_tiles/normalized/tile_*.webp', {
  eager: true,
  import: 'default',
  query: '?url',
}) as Record<string, string>;

/**
 * Returns the Tinkering tile image for the engine's tile id.
 *
 * The supplied upscale filenames followed scan order rather than the engine's effect ids, so the
 * normalized files are deliberately remapped by effect: 2=QIC 1, 3=charge 4, 4=QIC 2,
 * 5=build with 3 free terraforming steps.
 */
export function tinkeringTileImageSrc(tileId: number): string | undefined {
  return normalized[
    `./tinkering_tiles/normalized/tile_${String(tileId).padStart(2, '0')}.webp`
  ];
}
