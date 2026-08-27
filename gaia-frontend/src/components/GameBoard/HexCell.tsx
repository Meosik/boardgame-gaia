import { hexCorners } from './hex-utils';
import { PlanetHex } from './PlanetHex';
import {
  FACTION_STRUCTURE_COLOR,
  structureAssetName,
  structureImageSrc,
  type StructureAssetColor,
} from '../../assets/structureImages';
import type { FactionId, Hex, PlayerId } from '../../types/game';

interface Props {
  hex: Hex;
  cx: number;
  cy: number;
  size: number;
  playerFactions: Record<PlayerId, FactionId | null>;
  isHighlighted: boolean;
  isSelected: boolean;
  isPrintedOnSectorArt: boolean;
  showPlanetOverlay: boolean;
  hasPowerRing: boolean;
  onClick: () => void;
}

export function HexCell({
  hex,
  cx,
  cy,
  size,
  playerFactions,
  isHighlighted,
  isSelected,
  isPrintedOnSectorArt,
  showPlanetOverlay,
  hasPowerRing,
  onClick,
}: Props) {
  const points = hexCorners(cx, cy, size);
  const planet = hex.planet;

  // The grid line itself always shows, printed sector/interspace art or not
  // — only the FILL (the plain navy hex backdrop `HexCell` draws for
  // not-yet-imaged hexes) is suppressed once real art is underneath, so the
  // photo isn't tinted. A thinner line here than the "no art" case reads as
  // the same kind of subtle seam the physical board's own printed hex grid
  // has, not a competing overlay.
  const stroke = isSelected
    ? '#ffffff'
    : isHighlighted
      ? '#ffeb3b'
      : '#2a5fa8';
  const strokeWidth = isSelected || isHighlighted ? 2.5 : isPrintedOnSectorArt ? 1 : 1.5;
  const hexFill = isSelected
    ? '#ffffff'
    : isHighlighted
      ? '#ffeb3b'
      : isPrintedOnSectorArt
        ? 'transparent'
        : '#0d1b3e';
  const hexOpacity = isSelected
    ? 0.2
    : isHighlighted
      ? 0.14
      : isPrintedOnSectorArt
        ? 0
        : planet
          ? 1
          : 0.3;

  const mainStructure = hex.structures[0];
  const structureAsset = mainStructure ? structureAssetName(mainStructure.kind) : null;
  const structureColor = mainStructure
    ? colorForPlayer(playerFactions[mainStructure.owner])
    : null;
  const structureSrc = structureAsset && structureColor
    ? structureImageSrc(structureColor, structureAsset)
    : null;

  return (
    <g
      className="hex-cell"
      role="button"
      aria-label={`hex ${hex.coord.q},${hex.coord.r}`}
      onClick={onClick}
      style={{ cursor: isHighlighted ? 'pointer' : 'default' }}
    >
      <polygon
        points={points}
        fill={hexFill}
        fillOpacity={hexOpacity}
        stroke={stroke}
        strokeWidth={strokeWidth}
        filter={isHighlighted ? 'url(#hex-glow)' : undefined}
      />
      {planet && showPlanetOverlay && (
        <PlanetHex
          planetType={planet.is_gaia_formed ? 'Gaia' : planet.planet_type}
          cx={cx}
          cy={cy}
          size={size}
          hexKey={`${hex.coord.q},${hex.coord.r}`}
        />
      )}
      {structureSrc && (
        <image
          href={structureSrc}
          x={cx - size * 0.22}
          y={cy - size * 0.24}
          width={size * 0.44}
          height={size * 0.44}
          preserveAspectRatio="xMidYMid meet"
          style={{ pointerEvents: 'none' }}
        />
      )}
      {hasPowerRing && structureColor && (
        // Moweyds' Power Ring (rulebook Appendix I) has no dedicated art asset, so it reuses the
        // same per-color "marker" token image as Satellites — placed opposite them (bottom-left
        // vs. top-right) so the two badges never overlap.
        <image
          href={structureImageSrc(structureColor, 'marker')}
          x={cx - size * 0.52}
          y={cy + size * 0.28}
          width={size * 0.24}
          height={size * 0.24}
          preserveAspectRatio="xMidYMid meet"
          style={{ pointerEvents: 'none' }}
        />
      )}
      {hex.satellites.length > 0 && (
        <image
          href={structureImageSrc(colorForPlayer(playerFactions[hex.satellites[0]]), 'marker')}
          x={cx + size * 0.28}
          y={cy - size * 0.52}
          width={size * 0.24}
          height={size * 0.24}
          preserveAspectRatio="xMidYMid meet"
          style={{ pointerEvents: 'none' }}
        />
      )}
    </g>
  );
}

function colorForPlayer(faction: FactionId | null | undefined): StructureAssetColor {
  return faction ? FACTION_STRUCTURE_COLOR[faction] : 'gray';
}
