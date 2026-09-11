export { default as roundScoringTileBackImageSrc } from './round_scoring_tiles/normalized/707b3cfa-3620-457a-aec7-15dcf7f729e5.png';

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
