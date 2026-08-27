import booster05 from './round_boosters/booster_05_tile.webp';
import booster06 from './round_boosters/booster_06_tile.webp';
import booster14 from './round_boosters/booster_14_tile.webp';

const images: Record<number, string> = {
  1: '/assets/gaiaproject/booster_rl.png',
  2: '/assets/gaiaproject/booster_pwt.png',
  3: '/assets/gaiaproject/booster_m.png',
  4: '/assets/gaiaproject/booster_big.png',
  5: booster05,
  6: booster06,
  7: '/assets/gaiaproject/booster_ts.png',
  8: '/assets/gaiaproject/booster_range.png',
  9: '/assets/gaiaproject/booster_q.png',
  10: '/assets/gaiaproject/booster_planet.png',
  11: '/assets/gaiaproject/booster_gaia.png',
  12: '/assets/gaiaproject/booster_terra.png',
  13: '/assets/gaiaproject/booster_1o1k.png',
  14: booster14,
};

export function roundBoosterImageSrc(boosterId: number): string | undefined {
  return images[boosterId];
}
