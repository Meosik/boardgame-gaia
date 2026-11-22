import type { FactionId, PlanetType, SpaceshipId } from './types/game';

export const FACTION_DISPLAY_NAMES: Record<FactionId, string> = {
  Terrans: '테란',
  Lantids: '란티다',
  Xenos: '제노스',
  Gleens: '글린',
  Taklons: '타클론',
  Ambas: '앰바스',
  HadschHallas: '하드쉬 할라',
  Ivits: '하이브',
  Geodens: '기오덴',
  BalTaks: '발 타크',
  Firaks: '파이락',
  Bescods: '매드 안드로이드',
  Nevlas: '네블라',
  Itars: '아이타',
  Tinkeroids: '팅커로이드',
  Darkanians: '다카니안',
  Moweyds: '모웨이드',
  SpaceGiants: '스페이스자이언트',
};

export const SPACESHIP_DISPLAY_NAMES: Record<SpaceshipId, string> = {
  Twilight: '트와일라잇',
  Rebellion: '리벨리온',
  TFMars: 'T F 마스',
  Eclipse: '이클립스',
};

export const PLANET_TYPE_DISPLAY_NAMES: Record<PlanetType, string> = {
  Terra: '대지',
  Desert: '사막',
  Ice: '얼음',
  Swamp: '늪',
  Oxide: '산성',
  Titanium: '티타늄',
  Volcanic: '화산',
  Transdim: '차원변형행성',
  Gaia: '가이아',
  LostPlanet: '검은 행성',
  Asteroid: '소행성',
  ProtoPlanet: '원시 행성',
};

export const LOST_FLEET_DISPLAY_NAME = '잃어버린 함대';

export function factionDisplayName(faction: FactionId | null | undefined): string {
  return faction ? FACTION_DISPLAY_NAMES[faction] : '종족 미정';
}

export function spaceshipDisplayName(spaceship: SpaceshipId): string {
  return SPACESHIP_DISPLAY_NAMES[spaceship];
}

export function planetTypeDisplayName(planetType: PlanetType): string {
  return PLANET_TYPE_DISPLAY_NAMES[planetType];
}
