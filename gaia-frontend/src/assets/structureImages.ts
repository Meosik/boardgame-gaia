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

type StructureAssetName =
  | 'academy'
  | 'marker'
  | 'mine'
  | 'planetary_institute'
  | 'researchlab'
  | 'structure6';

const STRUCTURE_IMAGES = import.meta.glob('./structures/*.png', {
  eager: true,
  import: 'default',
}) as Record<string, string>;

export const FACTION_STRUCTURE_COLOR: Record<FactionId, StructureAssetColor> = {
  Terrans: 'cyan',
  Lantids: 'pink',
  Xenos: 'pink',
  Gleens: 'cyan',
  Taklons: 'orange',
  Ambas: 'cyan',
  HadschHallas: 'yellow',
  Ivits: 'red',
  Geodens: 'yellow',
  BalTaks: 'orange',
  Firaks: 'pink',
  Bescods: 'gray',
  Nevlas: 'cyan',
  Itars: 'orange',
  Tinkeroids: 'blue',
  Moweyds: 'cyan',
  SpaceGiants: 'yellow',
  Darkanians: 'red',
};

export function structureAssetName(kind: StructureType): StructureAssetName | null {
  if (kind === 'Mine') return 'mine';
  if (kind === 'TradingStation') return 'structure6';
  if (kind === 'ResearchLab') return 'researchlab';
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
  return STRUCTURE_IMAGES[`./structures/${color}_${assetName}.png`];
}

