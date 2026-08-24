import { useMemo } from 'react';
import { axialToPixel, hexKey } from './hex-utils';
import { HexCell } from './HexCell';
import { useGameStore } from '../../store/gameStore';
import { sectorImageSrc } from '../../assets/sectorImages';
import type { BoardState, FactionId, HexCoord, PlayerId, PlayerState } from '../../types/game';

const HEX_SIZE = 36;
const SVG_WIDTH = 900;
const SVG_HEIGHT = 780;
const OFFSET_X = SVG_WIDTH / 2;
const OFFSET_Y = SVG_HEIGHT / 2;

// A standard sector is a radius-2 cluster of 19 hexes (see gaia-engine
// data/sectors.toml). For flat-top hexes with circumradius `size`, the
// pixel bounding box of that cluster (hex centers ±2 rings out, plus each
// outer hex's own corner extent) works out to width = 8*size,
// height = 5*sqrt(3)*size — this closely matches the ~0.92 aspect ratio of
// the actual space_sector_*.jpg art (1246x1354), so it's used directly to
// size the sector background image rather than clipping to an exact hex
// silhouette.
const SECTOR_IMAGE_WIDTH = HEX_SIZE * 8;
const SECTOR_IMAGE_HEIGHT = HEX_SIZE * 5 * Math.sqrt(3);

interface StarDot { cx: number; cy: number; r: number; opacity: number }

interface Props {
  board: BoardState;
  players?: PlayerState[];
  validTargets?: HexCoord[];
}

export function GameBoard({ board, players = [], validTargets = [] }: Props) {
  const { activePlanet, selectedHexes, selectedAction, actions } = useGameStore((s) => ({
    activePlanet: s.activePlanet,
    selectedHexes: s.selectedHexes,
    selectedAction: s.selectedAction,
    actions: s.actions,
  }));
  const multiSelect = selectedAction === 'FormFederation';

  const validSet = new Set(validTargets.map((c) => hexKey(c.q, c.r)));
  const selectedHexSet = new Set(selectedHexes.map((c) => hexKey(c.q, c.r)));

  // Stable star field — generated once on mount
  const stars = useMemo<StarDot[]>(() => {
    const count = 65;
    return Array.from({ length: count }, () => ({
      cx: Math.random() * SVG_WIDTH,
      cy: Math.random() * SVG_HEIGHT,
      r: Math.random() * 1.2 + 0.3,
      opacity: Math.random() * 0.55 + 0.25,
    }));
  }, []);

  // No server-side "valid targets" endpoint exists yet (see README "Known
  // migration work"), so any hex is clickable while a coord-taking action is
  // selected — the server is authoritative and rejects illegal targets via
  // `command_rejected`. `validTargets`, when populated, still highlights a
  // hint set of hexes without restricting which ones are clickable.
  function handleHexClick(coord: HexCoord) {
    if (!selectedAction) return;
    if (multiSelect) {
      actions.toggleHex(coord);
      return;
    }
    const isSame = activePlanet !== null && activePlanet.q === coord.q && activePlanet.r === coord.r;
    actions.selectPlanet(isSame ? null : coord);
  }

  const hexEntries = Object.values(board.hexes);
  const playerFactions = useMemo<Record<PlayerId, FactionId | null>>(() => {
    return Object.fromEntries(players.map((player) => [player.player_id, player.faction]));
  }, [players]);

  return (
    <div className="game-board-container">
      <svg
        width={SVG_WIDTH}
        height={SVG_HEIGHT}
        viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
        className="game-board-svg"
      >
        <defs>
          {/* Blue glow filter — applied to highlighted hexes */}
          <filter id="hex-glow" x="-35%" y="-35%" width="170%" height="170%">
            <feGaussianBlur in="SourceAlpha" stdDeviation="2" result="blur" />
            <feFlood floodColor="#2a9fff" floodOpacity="0.75" result="color" />
            <feComposite in="color" in2="blur" operator="in" result="glow" />
            <feMerge>
              <feMergeNode in="glow" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Space background */}
        <rect width={SVG_WIDTH} height={SVG_HEIGHT} fill="#080818" />

        {/* Star field */}
        {stars.map((s, i) => (
          <circle key={i} cx={s.cx} cy={s.cy} r={s.r} fill="#ffffff" opacity={s.opacity} />
        ))}

        {/* Sector tile backgrounds — drawn beneath hex polygons/planets/structures */}
        {board.sectors.map((sector) => {
          const [px, py] = axialToPixel(sector.origin.q, sector.origin.r, HEX_SIZE);
          const cx = px + OFFSET_X;
          const cy = py + OFFSET_Y;
          const href = sectorImageSrc(sector.id);
          if (!href) return null;

          return (
            <image
              key={`sector-${sector.id}-${sector.origin.q}-${sector.origin.r}`}
              href={href}
              x={cx - SECTOR_IMAGE_WIDTH / 2}
              y={cy - SECTOR_IMAGE_HEIGHT / 2}
              width={SECTOR_IMAGE_WIDTH}
              height={SECTOR_IMAGE_HEIGHT}
              preserveAspectRatio="xMidYMid slice"
              transform={`rotate(${sector.rotation * 60} ${cx} ${cy})`}
              style={{ pointerEvents: 'none' }}
            />
          );
        })}

        {/* Hex cells */}
        {hexEntries.map((hex) => {
          const { q, r } = hex.coord;
          const [px, py] = axialToPixel(q, r, HEX_SIZE);
          const cx = px + OFFSET_X;
          const cy = py + OFFSET_Y;
          const key = hexKey(q, r);
          const isHighlighted = validSet.has(key);
          const isSelected = multiSelect
            ? selectedHexSet.has(key)
            : activePlanet !== null && activePlanet.q === q && activePlanet.r === r;

          return (
            <HexCell
              key={key}
              hex={hex}
              cx={cx}
              cy={cy}
              size={HEX_SIZE}
              playerFactions={playerFactions}
              isHighlighted={isHighlighted}
              isSelected={isSelected}
              onClick={() => handleHexClick(hex.coord)}
            />
          );
        })}
      </svg>
    </div>
  );
}
