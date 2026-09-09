const normalized = import.meta.glob('./round_boosters/normalized/booster_*.webp', {
  eager: true,
  import: 'default',
  query: '?url',
}) as Record<string, string>;

export function roundBoosterImageSrc(boosterId: number): string | undefined {
  const stem = String(boosterId).padStart(2, '0');
  return normalized[`./round_boosters/normalized/booster_${stem}.webp`];
}
