import { indexAssetsById } from './assetIndex';

const normalized = import.meta.glob('./round_boosters/normalized/booster_*.webp', {
  eager: true,
  import: 'default',
  query: '?url',
}) as Record<string, string>;

const boosters = indexAssetsById(normalized, 'booster');

export function roundBoosterImageSrc(boosterId: number): string | undefined {
  return boosters.get(boosterId);
}
