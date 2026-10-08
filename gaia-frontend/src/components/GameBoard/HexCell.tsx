import moweydsPowerRing from '../../assets/structures/special/moweyds-power-ring.png';
import { useReplayHighlight } from '../../replay/highlight';
import { hexCorners } from './hex-utils';
import type { MouseEvent as ReactMouseEvent } from 'react';
import { PlanetHex } from './PlanetHex';
import {
  FACTION_STRUCTURE_COLOR,
  STRUCTURE_COLOR_HEX,
  structureAssetName,
  structureImageSrc,
  type StructureAssetColor,
} from '../../assets/structureImages';
import type { FactionId, Hex, PlayerId } from '../../types/game';
import { GamePieceIcon } from '../GamePieceIcon';

interface Props {
  hex: Hex;
  chargeRangeOrigin?: boolean;
  chargeSource?: boolean;
  cx: number;
  cy: number;
  size: number;
  playerFactions: Record<PlayerId, FactionId | null>;
  isHighlighted: boolean;
  isSelected: boolean;
  isPrintedOnSectorArt: boolean;
  isStandardSectorArt: boolean;
  mutePrintedBackground: boolean;
  showPlanetOverlay: boolean;
  hasPowerRing: boolean;
  isDeepSpaceOutline: boolean;
  isInNavigationRange?: boolean;
  navigationRangeColor?: string;
  emphasizeStructure?: boolean;
  isInspectable?: boolean;
  onClick: (event: ReactMouseEvent<SVGGElement>) => void;
}

export function HexCell({
  hex,
  chargeRangeOrigin = false,
  chargeSource = false,
  cx,
  cy,
  size,
  playerFactions,
  isHighlighted,
  isSelected,
  isPrintedOnSectorArt,
  isStandardSectorArt,
  mutePrintedBackground,
  showPlanetOverlay,
  hasPowerRing,
  isDeepSpaceOutline,
  isInNavigationRange = false,
  navigationRangeColor = STRUCTURE_COLOR_HEX.cyan,
  emphasizeStructure = false,
  isInspectable = false,
  onClick,
}: Props) {
  const replay = useReplayHighlight();
  const lastMove = replay?.hexes.has(`${hex.coord.q},${hex.coord.r}`);
  const points = hexCorners(cx, cy, size);
  const planet = hex.planet;
  const hasMutedBackground = mutePrintedBackground && planet === null;
  const satelliteCount = hex.satellites.length;
  const satelliteGap = size * 0.04;
  const satelliteSize = size * Math.min(0.475, (1.4 - 0.04 * (satelliteCount - 1)) / Math.max(1, satelliteCount));
  const satelliteRowWidth = satelliteCount * satelliteSize + Math.max(0, satelliteCount - 1) * satelliteGap;

  // The grid line itself always shows, printed sector/interspace art or not
  // — only the FILL (the plain navy hex backdrop `HexCell` draws for
  // not-yet-imaged hexes) is suppressed once real art is underneath, so the
  // photo isn't tinted. Standard-sector art is generated independently, so
  // a consistent opaque stroke masks small source-to-source differences in
  // the baked-in grid color and width.
  const stroke = isSelected
    ? '#ffffff'
    : isHighlighted
      ? '#ffeb3b'
      : isDeepSpaceOutline
        ? '#ffffff'
        : isStandardSectorArt
          ? '#314B5A'
          : '#2a5fa8';
  const strokeWidth = isSelected || isHighlighted
    ? 2.5
    : isDeepSpaceOutline
      ? 2
      : isStandardSectorArt
        ? 2.5
        : isPrintedOnSectorArt ? 1 : 1.5;
  const hexFill = isSelected
    ? '#ffffff'
    : isHighlighted
      ? '#ffeb3b'
      : hasMutedBackground
        ? '#020712'
      : isPrintedOnSectorArt
        ? 'transparent'
        : '#0d1b3e';
  const hexOpacity = isSelected
    ? 0.2
    : isHighlighted
      ? 0.14
      : hasMutedBackground
        ? 0.2
      : isPrintedOnSectorArt
        ? 0
        : planet
          ? 1
          : 0.3;

  const mainStructure = hex.structures[0];
  const sharedPlanetStructures = hex.structures.slice(1);
  const structureAsset = mainStructure ? structureAssetName(mainStructure.kind) : null;
  const structureColor = mainStructure
    ? colorForPlayer(playerFactions[mainStructure.owner])
    : null;
  const structureSrc = structureAsset && structureColor
    ? structureImageSrc(structureColor, structureAsset)
    : null;
  const gaiaformerOwner = planet?.planet_type === 'Transdim'
    && planet.owner !== null
    && hex.structures.length === 0
    ? planet.owner
    : null;
  const gaiaformerSrc = gaiaformerOwner !== null
    ? structureImageSrc(colorForPlayer(playerFactions[gaiaformerOwner]), 'gaiaformer')
    : null;
  const structureScale = structureAsset === 'planetary_institute'
    ? 0.99
    : structureAsset === 'academy'
      ? 0.946
      : structureAsset === 'trading_station' || structureAsset === 'research_lab'
      ? 0.80
        : structureAsset === 'mine'
          ? 0.792
          : 0.72;
  const structureVisibilityScale = emphasizeStructure
    ? structureAsset === 'planetary_institute' || structureAsset === 'academy'
      ? 1.05
      : 1.12
    : 1;
  const renderedStructureScale = structureScale * structureVisibilityScale * (replay ? 1.15 : 1);
  const structureCenterXOffset = structureAsset === 'research_lab'
    ? 0.179
    : structureAsset === 'planetary_institute'
      ? 0.033
    : structureAsset === 'academy'
      ? -0.033
    : structureAsset === 'mine'
      ? -0.04
      : 0;
  const structureTopOffset = structureAsset === 'mine'
    ? 0.893
    : structureAsset === 'trading_station'
      ? 0.64
    : structureAsset === 'research_lab'
      ? 0.663
    : structureAsset === 'academy'
      ? 0.441
      : 0.54;
  const structureDownwardOffset = structureAsset === 'mine' ? 10 : 0;
  const structureLift = emphasizeStructure ? size * 0.04 : 0;

  return (
    <g
      data-tutorial-target={`hex:${hex.coord.q},${hex.coord.r}`}
      className={`hex-cell${chargeSource ? ' tutorial-charge-source' : ''}`}
      role="button"
      aria-label={`hex ${hex.coord.q},${hex.coord.r}`}
      onClick={onClick}
      style={{ cursor: isHighlighted || isInspectable ? 'pointer' : 'default' }}
    >
      <polygon
        points={points}
        fill={hexFill}
        fillOpacity={hexOpacity}
        stroke={stroke}
        strokeWidth={strokeWidth}
        filter={isHighlighted ? 'url(#hex-glow)' : undefined}
      />
      {chargeRangeOrigin && <circle className="tutorial-charge-range" cx={cx} cy={cy} r={size * 3.5} fill="none" stroke="#ffcf50" strokeWidth="3" strokeDasharray="7 5" pointerEvents="none" aria-label="파워 충전 거리 2칸" />}
      {isInNavigationRange && (
        <polygon
          className="game-board-range-outline"
          points={hexCorners(cx, cy, size * 0.9)}
          fill="none"
          stroke={navigationRangeColor}
          strokeWidth="1.65"
          strokeOpacity="0.58"
          pointerEvents="none"
          aria-hidden="true"
        />
      )}
      {planet && showPlanetOverlay && (
        <PlanetHex
          planetType={planet.is_gaia_formed ? 'Gaia' : planet.planet_type}
          cx={cx}
          cy={cy}
          size={size}
          hexKey={`${hex.coord.q},${hex.coord.r}`}
        />
      )}
      {hasPowerRing && structureColor && (
        <image href={moweydsPowerRing}
          x={cx - size * 0.78} y={cy - size * 0.86}
          width={size * 1.56} height={size * 1.56}
          preserveAspectRatio="xMidYMid meet"
          aria-label="모웨이드 파워 링 · 건물 파워값 +2"
          style={{ pointerEvents: 'none' }}
        />
      )}
      {gaiaformerSrc && (
        <image
          className="game-board-gaiaformer"
          href={gaiaformerSrc}
          x={cx - size * 0.297}
          y={cy - size * 0.52}
          width={size * (replay ? 0.72 : 0.62)}
          height={size * (replay ? 0.72 : 0.62)}
          preserveAspectRatio="xMidYMid meet"
          style={{ pointerEvents: 'none' }}
          aria-label="가이아포머"
        />
      )}
      {structureSrc && emphasizeStructure && (
        <g className="game-board-structure-separation" aria-hidden="true">
          <ellipse
            className="game-board-structure-backdrop"
            cx={cx}
            cy={cy + size * 0.03}
            rx={size * 0.42}
            ry={size * 0.31}
          />
          <ellipse
            className="game-board-structure-contact-shadow"
            cx={cx}
            cy={cy + size * 0.25}
            rx={size * 0.29}
            ry={size * 0.075}
          />
        </g>
      )}
      {structureSrc && mainStructure?.kind === 'SpaceStation' && (
        <GamePieceIcon
          className={emphasizeStructure ? 'game-board-structure game-board-structure--emphasized' : 'game-board-structure'}
          kind="ivits-station"
          x={cx - size * 0.6}
          y={cy - size * 0.6}
          width={size * 1.2}
          height={size * 1.2}
          decorative={false}
          label="이비츠 우주 정거장"
          style={{ pointerEvents: 'visiblePainted' }}
        />
      )}
      {structureSrc && mainStructure?.kind !== 'SpaceStation' && (
        <image
          className={emphasizeStructure ? 'game-board-structure game-board-structure--emphasized' : 'game-board-structure'}
          href={structureSrc}
          x={hasPowerRing ? cx - size * 0.37 : cx + size * structureCenterXOffset - size * renderedStructureScale / 2}
          y={hasPowerRing ? cy - size * 0.37 : cy - size * structureTopOffset + structureDownwardOffset - structureLift}
          width={size * (hasPowerRing ? 0.74 : renderedStructureScale)}
          height={size * (hasPowerRing ? 0.74 : renderedStructureScale)}
          preserveAspectRatio="xMidYMid meet"
          style={{ pointerEvents: 'visiblePainted' }}
          aria-label="구조물"
        />
      )}
      {sharedPlanetStructures.map((structure, index) => {
        const asset = structureAssetName(structure.kind);
        if (!asset) return null;
        const color = colorForPlayer(playerFactions[structure.owner]);
        const src = structureImageSrc(color, asset);
        const tokenSize = size * (replay ? 0.575 : 0.5);
        return (
          <image
            key={`${structure.owner}-${JSON.stringify(structure.kind)}-${index}`}
            className="game-board-shared-planet-structure"
            href={src}
            x={cx + size * 0.08 + index * size * 0.12}
            y={cy + size * 0.02}
            width={tokenSize}
            height={tokenSize}
            preserveAspectRatio="xMidYMid meet"
            style={{ pointerEvents: 'visiblePainted' }}
            aria-label={`공동 점유 구조물 ${structure.owner}`}
          />
        );
      })}
      {hex.satellites.map((owner, index) => (
        <image
          key={owner}
          className="game-board-satellite"
          role="img"
          aria-label={`플레이어 ${owner + 1} 위성`}
          href={structureImageSrc(colorForPlayer(playerFactions[owner]), 'marker')}
          x={satelliteCount === 1 ? cx - size * 0.233 : cx - satelliteRowWidth / 2 + index * (satelliteSize + satelliteGap)}
          y={cy - size * 0.57}
          width={satelliteSize}
          height={satelliteSize}
          preserveAspectRatio="xMidYMid meet"
          style={{ pointerEvents: 'none' }}
        />
      ))}
      {lastMove && (
        <g className="replay-hex-highlight" pointerEvents="none" aria-label={`직전 행동: ${replay?.label}`}>
          <polygon points={hexCorners(cx, cy, size * 0.91)} fill="none" stroke="#111827" strokeWidth="6" />
          <polygon points={hexCorners(cx, cy, size * 0.91)} fill="none" stroke="#fde047" strokeWidth="3" />

        </g>
      )}
    </g>
  );
}

function colorForPlayer(faction: FactionId | null | undefined): StructureAssetColor {
  return faction ? FACTION_STRUCTURE_COLOR[faction] : 'gray';
}
