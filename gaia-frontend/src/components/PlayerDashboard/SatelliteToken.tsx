import {
  FACTION_STRUCTURE_COLOR,
  structureImageSrc,
  type StructureAssetColor,
} from '../../assets/structureImages';
import type { FactionId } from '../../types/game';

interface Props {
  color: string;
  faction?: FactionId | null;
  size?: number;
}

const HEX_TO_STRUCTURE_COLOR: Record<string, StructureAssetColor> = {
  '#4a7c59': 'cyan',
  '#9575cd': 'pink',
  '#9b59b6': 'pink',
  '#81c784': 'cyan',
  '#ff8a65': 'orange',
  '#4fc3f7': 'cyan',
  '#ffd54f': 'yellow',
  '#e57373': 'red',
  '#aed581': 'yellow',
  '#ff7043': 'orange',
  '#ba68c8': 'pink',
  '#90a4ae': 'gray',
  '#80deea': 'cyan',
  '#ffb74d': 'orange',
  '#64b5f6': 'blue',
  '#a5d6a7': 'cyan',
  '#ffe082': 'yellow',
  '#ef9a9a': 'red',
};

function assetColorForToken(color: string, faction: FactionId | null | undefined): StructureAssetColor {
  return faction ? FACTION_STRUCTURE_COLOR[faction] : HEX_TO_STRUCTURE_COLOR[color.toLowerCase()] ?? 'gray';
}

export function SatelliteToken({ color, faction = null, size = 16 }: Props) {
  const assetColor = assetColorForToken(color, faction);
  return (
    <img
      src={structureImageSrc(assetColor, 'marker')}
      alt=""
      width={size}
      height={size}
      style={{ display: 'inline-block', verticalAlign: 'middle', objectFit: 'contain' }}
      aria-hidden
    />
  );
}
