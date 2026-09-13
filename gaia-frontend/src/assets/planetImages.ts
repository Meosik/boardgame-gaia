import type { PlanetType } from '../types/game';

import terraPng from './planets/terra.png';
import desertPng from './planets/desert.png';
import icePng from './planets/ice.png';
import swampPng from './planets/swamp.png';
import oxidePng from './planets/oxide.png';
import titaniumPng from './planets/titanium.png';
import volcanicPng from './planets/volcanic.png';
import transdimPng from './planets/transdim.png';
import gaiaPng from './planets/gaia.png';
import lostPlanetWebp from './boards/normalized/lost_planet.webp';

/**
 * Planet art, shared so the board and the tutorial cannot disagree about which picture is which
 * planet. Asteroids and Protoplanets have no portrait of their own — they are drawn from the
 * Interspace tiles — so they resolve to `null` rather than to a wrong image.
 */
const PLANET_IMAGES: Partial<Record<PlanetType, string>> = {
  Terra: terraPng,
  Desert: desertPng,
  Ice: icePng,
  Swamp: swampPng,
  Oxide: oxidePng,
  Titanium: titaniumPng,
  Volcanic: volcanicPng,
  Transdim: transdimPng,
  Gaia: gaiaPng,
  LostPlanet: lostPlanetWebp,
};

export function planetImageSrc(planet: PlanetType): string | null {
  return PLANET_IMAGES[planet] ?? null;
}

/**
 * The terraforming ring in printed order (rulebook p.11). Terraforming distance is how many steps
 * apart two types sit on this ring, so the order is the rule, not a display preference.
 */
export const TERRAFORMING_RING: PlanetType[] = [
  'Terra',
  'Oxide',
  'Volcanic',
  'Desert',
  'Swamp',
  'Titanium',
  'Ice',
];
