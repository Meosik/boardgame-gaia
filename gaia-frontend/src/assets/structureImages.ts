import type { FactionId, StructureType } from '../types/game';

export type StructureAssetColor =
  | 'blue'
  | 'brown'
  | 'cyan'
  | 'gray'
  | 'orange'
  | 'pink'
  | 'red'
  | 'white'
  | 'yellow';

export type StructureAssetName =
  | 'academy'
  | 'gaiaformer'
  | 'marker'
  | 'mine'
  | 'planetary_institute'
  | 'research_lab'
  | 'trading_station';

const UPSCALED_STRUCTURE_IMAGES = import.meta.glob('./structures/upscaled/*.png', {
  eager: true,
  import: 'default',
}) as Record<string, string>;

export const FACTION_STRUCTURE_COLOR: Record<FactionId, StructureAssetColor> = {
  Terrans: 'blue',
  Lantids: 'blue',
  Xenos: 'yellow',
  Gleens: 'yellow',
  Taklons: 'brown',
  Ambas: 'brown',
  HadschHallas: 'red',
  Ivits: 'red',
  Geodens: 'orange',
  BalTaks: 'orange',
  Firaks: 'gray',
  Bescods: 'gray',
  Nevlas: 'white',
  Itars: 'white',
  Tinkeroids: 'pink',
  Moweyds: 'cyan',
  SpaceGiants: 'cyan',
  Darkanians: 'pink',
};

/** Screen-safe equivalents of the physical player-piece colors. */
export const STRUCTURE_COLOR_HEX: Record<StructureAssetColor, string> = {
  blue: '#3b82f6',
  brown: '#a16207',
  cyan: '#06b6d4',
  gray: '#94a3b8',
  orange: '#f97316',
  pink: '#ec4899',
  red: '#ef4444',
  white: '#f8fafc',
  yellow: '#facc15',
};

export function structureAssetName(kind: StructureType): StructureAssetName | null {
  if (kind === 'Mine') return 'mine';
  if (kind === 'TradingStation') return 'trading_station';
  if (kind === 'ResearchLab') return 'research_lab';
  if (kind === 'PlanetaryInstitute') return 'planetary_institute';
  if (kind === 'Satellite') return 'marker';
  if (kind === 'SpaceStation') return 'marker';
  if (typeof kind === 'object' && 'Academy' in kind) return 'academy';
  return null;
}

export function structureImageSrc(
  color: StructureAssetColor,
  assetName: StructureAssetName,
): string {
  return UPSCALED_STRUCTURE_IMAGES[`./structures/upscaled/${color}_${assetName}.png`];
}
