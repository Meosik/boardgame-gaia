const normalized = import.meta.glob('./round_scoring_tiles/normalized/*.webp', {
  eager: true,
  import: 'default',
}) as Record<string, string>;

function normalizedRoundTile(tileId: number): string | undefined {
  const stem = String(tileId).padStart(2, '0');
  return normalized[`./round_scoring_tiles/normalized/round_${stem}.webp`];
}

export function roundScoringTileImageSrc(tileId: number): string | undefined {
  return normalizedRoundTile(tileId);
}
