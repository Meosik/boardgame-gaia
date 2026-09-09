import { Fragment, useMemo } from 'react';
import type { MouseEvent as ReactMouseEvent } from 'react';
import { shallow } from 'zustand/shallow';
import {
  axialDistance,
  axialToPixel,
  hexCorners,
  hexKey,
  rotateHexN,
  sectorCentroidPixel,
  sectorHexPixelPositions,
  STANDARD_HEX_OFFSETS,
} from './hex-utils';
import { HexCell } from './HexCell';
import { useGameStore } from '../../store/gameStore';
import {
  deepSpaceSectorImageSrc,
  deepSpaceSectorSide,
  sectorImageSrc,
} from '../../assets/sectorImages';
import {
  asteroidInterspaceImageSrc,
  blankInterspaceImageSrc,
  protoPlanetInterspaceImageSrc,
  spaceshipInterspaceImageSrc,
} from '../../assets/interspaceTileImages';
import type {
  BoardState,
  FactionId,
  Hex,
  HexCoord,
  PlayerId,
  PlayerState,
  Sector,
  SpaceshipId,
} from '../../types/game';

const HEX_SIZE = 36;
const SVG_WIDTH = 1800;
const SVG_HEIGHT = 1400;
const OFFSET_X = SVG_WIDTH / 2;
const OFFSET_Y = SVG_HEIGHT / 2;

// A standard sector is a radius-2 cluster of 19 hexes. Normalize every
// source canvas into the same physical footprint; the hex clip below keeps
// the transformed rectangular image inside the sector silhouette.
const SECTOR_IMAGE_WIDTH = HEX_SIZE * 8;
const SECTOR_IMAGE_HEIGHT = HEX_SIZE * 5 * Math.sqrt(3);
// Every normalized 01-10 scan uses the same photographed resting orientation: its printed
// planets are four clockwise hex-steps ahead of the canonical sector templates used by the
// engine. Undo that baked-in 240° turn before applying the randomized sector rotation. This was
// verified across all ten images against each sector's distinctive planet pattern, rather than
// guessed from a single highlighted starting planet.
const STANDARD_SECTOR_PHOTO_ROTATION_OFFSET = 4;

// A Deep Space sector (Lost Fleet expansion, ids 11-18) is a 3-hex
// L-tromino at relative offsets (0,0)/(1,0)/(0,1) — see
// `gaia-engine/data/sectors.toml`'s "Deep Space Sectors" block, which
// `insert_sector` places by rotating each of these same three offsets and
// adding the sector's origin. The three hex centers plus one hex-radius of
// margin on every side spans exactly 3.5 radii horizontally and 2*sqrt(3)
// radii vertically. The normalized art uses that same physical footprint.
const DEEP_SPACE_HEX_OFFSETS: [number, number][] = [
  [0, 0],
  [1, 0],
  [0, 1],
];
const DEEP_SPACE_IMAGE_WIDTH = HEX_SIZE * 3.5;
const DEEP_SPACE_IMAGE_HEIGHT = HEX_SIZE * 2 * Math.sqrt(3);
// The scanned `deep_space_sector_*.jpg` photos weren't shot in the same
// orientation `DEEP_SPACE_HEX_OFFSETS` assumes as "unrotated" — there's no
// printed orientation arrow on these tiles the way standard sectors have, so
// nothing pins down which way is "rotation 0" for the photo itself, only for
// the *game's* hex positions. Empirically a constant one-step (60°) offset
// between the two lines them up — i.e. the photo's own layout matches the
// hex offsets after they've already been turned 60° once. Applied only to
// how the *image* is anchored/rotated, never to the clip mask, which must
// stay tied to the hexes' true board positions regardless of this.
const DEEP_SPACE_PHOTO_ROTATION_OFFSET = 1;
// The image's important anchor is the common vertex of its three hexes, not
// the canvas center. The normalization script fixes that vertex at 4/7 of
// the width and 1/2 of the height for every source image.
const DEEP_SPACE_JUNCTION_X_RATIO = 4 / 7;
const DEEP_SPACE_JUNCTION_Y_RATIO = 1 / 2;
const CALM_STANDARD_SECTOR_IDS = new Set([1, 3, 5]);
const NAVIGATION_RANGE = [1, 1, 2, 2, 3, 4] as const;
const HEX_DIRECTIONS = [
  [1, 0], [1, -1], [0, -1], [-1, 0], [-1, 1], [0, 1],
] as const;
interface StarDot { cx: number; cy: number; r: number; opacity: number }

interface Props {
  board: BoardState;
  players?: PlayerState[];
  validTargets?: HexCoord[];
  /** During federation formation, only these owned buildings and route hexes may be added.
   * Already-selected hexes remain clickable so the player can always remove them. */
  federationSelectableHexes?: HexCoord[];
  selectedCoord?: HexCoord | null;
  onHexClick?: (coord: HexCoord) => void;
  /** Opens a contextual action popup only for a structure owned by this player. */
  interactivePlayerId?: PlayerId;
  onOwnedStructureClick?: (
    hex: Hex,
    anchor: { x: number; y: number },
  ) => void;
  /** Opens the direct planet-action popup when no action is already selected. */
  onPlanetClick?: (
    hex: Hex,
    anchor: { x: number; y: number },
  ) => void;
  /** Opens the direct spaceship-exploration popup from a spaceship map tile. */
  onSpaceshipClick?: (
    ship: SpaceshipId,
    anchor: { x: number; y: number },
  ) => void;
  /** Lets a temporarily activated board action reuse the normal planet popup. */
  allowPlanetPopupDuringSelectedAction?: boolean;
  /** DEV sandbox target mode: clicking an owned structure opens the normal charge decision. */
  devPowerChargeTargeting?: boolean;
  onPowerChargeStructureClick?: (hex: Hex) => void;
  onContextDismiss?: () => void;
  /** Reports every board click before action/valid-target filtering. Intended for temporary
   * diagnostics and read-only inspection without weakening the actual action rules. */
  onHexInspect?: (coord: HexCoord) => void;
  /** Outlines every Deep Space sector's hexes in white so they're easy to tell apart from the
   * single-hex Interspace tiles during room setup, where there's no other way to distinguish
   * them at a glance. Off by default — once the actual game starts, the grid's normal blue
   * stroke is enough since players have had time to learn the board. */
  highlightDeepSpace?: boolean;
  /** Gives every single-hex Interspace tile the same white setup outline as Deep Space. */
  highlightInterspace?: boolean;
  /** Enables the structure-separation treatment while it is being evaluated in the dev game. */
  emphasizeStructures?: boolean;
  /** Faintly outlines the hexes inside this player's current basic Navigation range. */
  rangePlayerId?: PlayerId;
  /** Read-only preview bonus, normally +2 for one QIC. */
  rangePreviewBonus?: number;
}

export function GameBoard({
  board,
  players = [],
  validTargets = [],
  federationSelectableHexes = [],
  selectedCoord = null,
  onHexClick,
  interactivePlayerId,
  onOwnedStructureClick,
  onPlanetClick,
  onSpaceshipClick,
  allowPlanetPopupDuringSelectedAction = false,
  devPowerChargeTargeting = false,
  onPowerChargeStructureClick,
  onContextDismiss,
  onHexInspect,
  highlightDeepSpace = false,
  highlightInterspace = false,
  emphasizeStructures = false,
  rangePlayerId,
  rangePreviewBonus = 0,
}: Props) {
  const { activePlanet, selectedHexes, selectedAction, actions } = useGameStore(
    (s) => ({
      activePlanet: s.activePlanet,
      selectedHexes: s.selectedHexes,
      selectedAction: s.selectedAction,
      actions: s.actions,
    }),
    shallow,
  );
  const multiSelect = selectedAction === 'FormFederation';

  const validSet = new Set(validTargets.map((c) => hexKey(c.q, c.r)));
  const selectedHexSet = new Set(selectedHexes.map((c) => hexKey(c.q, c.r)));
  const federationSelectableSet = new Set(
    federationSelectableHexes.map((c) => hexKey(c.q, c.r)),
  );

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
  function handleHexClick(hex: Hex, event: ReactMouseEvent<SVGGElement>) {
    const { coord } = hex;
    onHexInspect?.(coord);
    if (devPowerChargeTargeting) {
      const hasOwnedBuilding = interactivePlayerId !== undefined
        && hex.structures.some((structure) => (
          structure.owner === interactivePlayerId
          && structure.kind !== 'Satellite'
          && structure.kind !== 'SpaceStation'
        ));
      if (hasOwnedBuilding) {
        onPowerChargeStructureClick?.(hex);
      } else {
        onContextDismiss?.();
      }
      return;
    }
    if (onHexClick) {
      if (!validSet.has(hexKey(coord.q, coord.r))) return;
      onHexClick(coord);
      return;
    }
    if (!selectedAction) {
      const spaceship = shipByHexKey.get(hexKey(coord.q, coord.r));
      if (spaceship && onSpaceshipClick) {
        onSpaceshipClick(spaceship, { x: event.clientX, y: event.clientY });
        return;
      }
      const ownStructure = interactivePlayerId === undefined
        ? undefined
        : hex.structures.find((structure) => structure.owner === interactivePlayerId);
      if (ownStructure && onOwnedStructureClick) {
        onOwnedStructureClick(hex, { x: event.clientX, y: event.clientY });
      } else if (hex.planet && hex.structures.length === 0 && onPlanetClick) {
        onPlanetClick(hex, { x: event.clientX, y: event.clientY });
      } else {
        onContextDismiss?.();
      }
      return;
    }
    if (allowPlanetPopupDuringSelectedAction) {
      if (hex.planet && hex.structures.length === 0 && onPlanetClick) {
        onPlanetClick(hex, { x: event.clientX, y: event.clientY });
      } else {
        onContextDismiss?.();
      }
      return;
    }
    if (multiSelect) {
      const selectedKey = hexKey(coord.q, coord.r);
      const alreadySelected = selectedHexSet.has(selectedKey);
      if (!alreadySelected && !federationSelectableSet.has(selectedKey)) return;
      actions.toggleHex(coord);
      return;
    }
    const isSame = activePlanet !== null && activePlanet.q === coord.q && activePlanet.r === coord.r;
    actions.selectPlanet(isSame ? null : coord);
  }

  const hexEntries = Object.values(board.hexes);
  const boardViewport = useMemo(() => {
    if (hexEntries.length === 0) {
      return { x: 0, y: 0, width: SVG_WIDTH, height: SVG_HEIGHT };
    }

    let minX = Number.POSITIVE_INFINITY;
    let minY = Number.POSITIVE_INFINITY;
    let maxX = Number.NEGATIVE_INFINITY;
    let maxY = Number.NEGATIVE_INFINITY;
    for (const hex of hexEntries) {
      const [px, py] = axialToPixel(hex.coord.q, hex.coord.r, HEX_SIZE);
      minX = Math.min(minX, px + OFFSET_X);
      minY = Math.min(minY, py + OFFSET_Y);
      maxX = Math.max(maxX, px + OFFSET_X);
      maxY = Math.max(maxY, py + OFFSET_Y);
    }

    // Keep enough room for the outer hex corners, glow and sector artwork,
    // but discard the large unused star-field margins around the galaxy.
    const padding = HEX_SIZE * 1.75;
    return {
      x: minX - padding,
      y: minY - padding,
      width: maxX - minX + padding * 2,
      height: maxY - minY + padding * 2,
    };
  }, [board.hexes]);
  const playerFactions = useMemo<Record<PlayerId, FactionId | null>>(() => {
    return Object.fromEntries(players.map((player) => [player.player_id, player.faction]));
  }, [players]);
  const powerRingHexKeys = useMemo(() => {
    const keys = new Set<string>();
    for (const player of players) {
      for (const coord of player.moweyds_power_ring_hexes ?? []) {
        keys.add(hexKey(coord.q, coord.r));
      }
    }
    return keys;
  }, [players]);
  const rangePlayer = players.find((player) => player.player_id === rangePlayerId);
  const navigationRange = rangePlayer
    ? NAVIGATION_RANGE[Math.min(rangePlayer.research_tracks.navigation, NAVIGATION_RANGE.length - 1)]
      + Number(Boolean(
        rangePlayer.tech_tiles?.includes(12) && !rangePlayer.covered_tech_tiles?.includes(12),
      ))
      + rangePreviewBonus
    : 0;
  const navigationRangeHexKeys = useMemo(() => {
    const reachable = new Set<string>();
    if (!rangePlayer || navigationRange <= 0) return reachable;

    const starts = rangePlayer.structures.map(({ hex }) => hex);
    if (board.lost_planet) {
      const lostPlanet = board.hexes[hexKey(board.lost_planet.q, board.lost_planet.r)]?.planet;
      if (lostPlanet?.owner === rangePlayer.player_id) starts.push(board.lost_planet);
    }

    const queue = starts.map((coord) => ({ coord, distance: 0 }));
    const distances = new Map(queue.map(({ coord }) => [hexKey(coord.q, coord.r), 0]));
    for (let index = 0; index < queue.length; index += 1) {
      const { coord, distance } = queue[index];
      if (distance >= navigationRange) continue;
      for (const [dq, dr] of HEX_DIRECTIONS) {
        const neighbor = { q: coord.q + dq, r: coord.r + dr };
        const key = hexKey(neighbor.q, neighbor.r);
        if (!(key in board.hexes) || distances.has(key)) continue;
        distances.set(key, distance + 1);
        reachable.add(key);
        queue.push({ coord: neighbor, distance: distance + 1 });
      }
    }
    return reachable;
  }, [board.hexes, board.lost_planet, navigationRange, rangePlayer]);
  // Map every standard-sector hex to its owning sector so its generated art
  // can receive the common grid treatment below.
  const standardSectorByHexKey = useMemo(() => {
    const sectors = new Map<string, Sector>();
    for (const hex of hexEntries) {
      const sector = board.sectors.find(
        (sector) => sector.id <= 10 && axialDistance(hex.coord, sector.origin) <= 2,
      );
      if (sector) sectors.set(hexKey(hex.coord.q, hex.coord.r), sector);
    }
    return sectors;
  }, [hexEntries, board.sectors]);
  const sectorPrintedHexKeys = useMemo(() => {
    const keys = new Set(standardSectorByHexKey.keys());
    for (const hex of hexEntries) {
      const printed = board.sectors.some((sector) => {
        if (sector.id <= 10) return false;
        return DEEP_SPACE_HEX_OFFSETS.some(([relQ, relR]) => {
          const [rq, rr] = rotateHexN(relQ, relR, sector.rotation);
          return hex.coord.q === rq + sector.origin.q && hex.coord.r === rr + sector.origin.r;
        });
      });
      if (printed) keys.add(hexKey(hex.coord.q, hex.coord.r));
    }
    return keys;
  }, [hexEntries, board.sectors, standardSectorByHexKey]);
  const deepSpaceHexKeys = useMemo(() => {
    const keys = new Set<string>();
    if (!highlightDeepSpace) return keys;
    for (const hex of hexEntries) {
      const inDeepSpace = board.sectors.some((sector) => {
        if (sector.id <= 10) return false;
        return DEEP_SPACE_HEX_OFFSETS.some(([relQ, relR]) => {
          const [rq, rr] = rotateHexN(relQ, relR, sector.rotation);
          return hex.coord.q === rq + sector.origin.q && hex.coord.r === rr + sector.origin.r;
        });
      });
      if (inDeepSpace) keys.add(hexKey(hex.coord.q, hex.coord.r));
    }
    return keys;
  }, [hexEntries, board.sectors, highlightDeepSpace]);
  const shipByHexKey = useMemo(() => {
    const map = new Map<string, SpaceshipId>();
    for (const [ship, coord] of Object.entries(board.spaceship_tiles)) {
      if (coord) map.set(hexKey(coord.q, coord.r), ship as SpaceshipId);
    }
    return map;
  }, [board.spaceship_tiles]);
  // Every hex not covered by a Space/Deep Space sector's art is one of the
  // 4-player layout's 10 single-hex Interspace holes (rulebook p.5) — the
  // board's hexes are entirely partitioned between the two, there's nothing
  // else a hex could be. Resolves to a real per-hex background image (a
  // spaceship, Asteroid, ProtoPlanet, or the plain Blank tile) rather than
  // leaving these hexes as bare grid cells.
  const interspaceImageByHexKey = useMemo(() => {
    const map = new Map<string, string>();
    for (const hex of hexEntries) {
      const key = hexKey(hex.coord.q, hex.coord.r);
      if (sectorPrintedHexKeys.has(key)) continue;
      const ship = shipByHexKey.get(key);
      if (ship) {
        map.set(key, spaceshipInterspaceImageSrc(ship));
      } else if (hex.planet?.planet_type === 'Asteroid') {
        map.set(key, asteroidInterspaceImageSrc());
      } else if (hex.planet?.planet_type === 'ProtoPlanet') {
        map.set(key, protoPlanetInterspaceImageSrc());
      } else {
        map.set(key, blankInterspaceImageSrc());
      }
    }
    return map;
  }, [hexEntries, sectorPrintedHexKeys, shipByHexKey]);
  const printedHexKeys = useMemo(
    () => new Set([...sectorPrintedHexKeys, ...interspaceImageByHexKey.keys()]),
    [sectorPrintedHexKeys, interspaceImageByHexKey],
  );

  // Mirrors HexCell's own stroke precedence (isSelected > isHighlighted > isDeepSpaceOutline >
  // plain grid) so hexes drawn later — and thus painting over their shared edges last — are
  // exactly the ones whose border needs to stay fully visible.
  function strokePriority(hex: BoardState['hexes'][string]): number {
    const { q, r } = hex.coord;
    const key = hexKey(q, r);
    const isSelected = onHexClick
      ? selectedCoord !== null && selectedCoord.q === q && selectedCoord.r === r
      : multiSelect
        ? selectedHexSet.has(key)
        : activePlanet !== null && activePlanet.q === q && activePlanet.r === r;
    if (isSelected) return 3;
    if (validSet.has(key)) return 2;
    if (deepSpaceHexKeys.has(key) || (highlightInterspace && interspaceImageByHexKey.has(key))) return 1;
    return 0;
  }

  return (
    <div className="game-board-container">
      <svg
        width={boardViewport.width}
        height={boardViewport.height}
        viewBox={`${boardViewport.x} ${boardViewport.y} ${boardViewport.width} ${boardViewport.height}`}
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
          const isDeepSpace = sector.id >= 11;
          const href = isDeepSpace
            ? deepSpaceSectorImageSrc(sector.id, deepSpaceSectorSide(sector, board.hexes))
            : sectorImageSrc(sector.id);
          if (!href) return null;

          // Deep Space sectors are a 3-hex tromino, not a 19-hex disk
          // centered on `origin` — `origin` is just one corner hex (the
          // template's relative (0,0)), so the image needs to be centered
          // on the cluster's actual pixel centroid instead, or two of its
          // three hexes would render mostly off the art.
          const offsets = isDeepSpace ? DEEP_SPACE_HEX_OFFSETS : STANDARD_HEX_OFFSETS;
          const width = isDeepSpace ? DEEP_SPACE_IMAGE_WIDTH : SECTOR_IMAGE_WIDTH;
          const height = isDeepSpace ? DEEP_SPACE_IMAGE_HEIGHT : SECTOR_IMAGE_HEIGHT;
          const sectorKey = `sector-${sector.id}-${sector.origin.q}-${sector.origin.r}`;
          const clipId = `${sectorKey}-clip`;
          // `insert_sector` (Rust) rotates each hex's *relative* offset
          // around local (0,0) and only then adds `origin` — i.e. `origin`
          // is the one fixed pivot point the whole sector template rotates
          // around, not the cluster's centroid. For a standard sector these
          // coincide (`origin` is a radially symmetric disk's own center),
          // which is why using `origin` as both the image's anchor *and*
          // the `transform="rotate(...)"` pivot happened to work before —
          // but for Deep Space's asymmetric L-tromino they're different
          // points, and pivoting the already-rotation-aware centroid around
          // itself again double-counted the rotation, which is exactly the
          // "rotated an extra 45°/90°-ish and cropped wrong, on every one of
          // the 8" symptom. The fix: position the (still axis-aligned)
          // image at the UNROTATED centroid (`rotation` forced to 0 here —
          // i.e. "where would this tile's own art sit if it had no spin"),
          // then let one single `transform="rotate(...)"` — pivoting on the
          // true fixed point, `origin` — carry both the image and its
          // implied center to the real rotated position, the same way
          // `insert_sector` derives every one of the sector's actual hexes.
          const [pivotX0, pivotY0] = axialToPixel(sector.origin.q, sector.origin.r, HEX_SIZE);
          const pivotX = pivotX0 + OFFSET_X;
          const pivotY = pivotY0 + OFFSET_Y;
          // Deep Space images additionally bake in `DEEP_SPACE_PHOTO_ROTATION_OFFSET`
          // as their "resting" orientation (see that constant's comment) —
          // the `transform` below then only needs to cover the *remaining*
          // distance from that resting state to the real `sector.rotation`.
          const photoOffset = isDeepSpace
            ? DEEP_SPACE_PHOTO_ROTATION_OFFSET
            : STANDARD_SECTOR_PHOTO_ROTATION_OFFSET;
          const [imgCx0, imgCy0] = sectorCentroidPixel(offsets, sector.origin, photoOffset, HEX_SIZE);
          const imgCx = imgCx0 + OFFSET_X;
          const imgCy = imgCy0 + OFFSET_Y;
          // The clip region is this sector's real hex-cluster silhouette
          // (the union of its actual hexes, in true world position — already
          // reflecting `sector.rotation`, since `sectorHexPixelPositions`
          // mirrors `insert_sector`'s own placement math) — deliberately
          // NOT rotated again here, so it lives in the same coordinate space
          // as the `<image>`'s un-rotated x/y/width/height box regardless of
          // that image's own `transform`. Referencing it from a wrapping
          // `<g>` with no transform of its own keeps that unambiguous.
          const clipHexes = sectorHexPixelPositions(offsets, sector.origin, sector.rotation, HEX_SIZE);
          const imgX = isDeepSpace
            ? imgCx - width * DEEP_SPACE_JUNCTION_X_RATIO
            : imgCx - width / 2;
          const imgY = isDeepSpace
            ? imgCy - height * DEEP_SPACE_JUNCTION_Y_RATIO
            : imgCy - height / 2;

          return (
            <Fragment key={sectorKey}>
              <clipPath id={clipId}>
                {clipHexes.map(([hx, hy], i) => (
                  <polygon key={i} points={hexCorners(hx + OFFSET_X, hy + OFFSET_Y, HEX_SIZE)} />
                ))}
              </clipPath>
              <g clipPath={`url(#${clipId})`}>
                <image
                  href={href}
                  x={imgX}
                  y={imgY}
                  width={width}
                  height={height}
                  preserveAspectRatio="none"
                  transform={`rotate(${(sector.rotation - photoOffset) * 60} ${pivotX} ${pivotY})`}
                  style={{ pointerEvents: 'none' }}
                />
              </g>
            </Fragment>
          );
        })}

        {/* Interspace tile backgrounds — the 10 single-hex holes between
            sectors (spaceship/Asteroid/ProtoPlanet/Blank); see
            `interspaceImageByHexKey` above. Single-hex, so unlike sector art
            there's no multi-hex rotation math needed — just clip straight to
            that one hex's own polygon. */}
        {hexEntries.map((hex) => {
          const key = hexKey(hex.coord.q, hex.coord.r);
          const href = interspaceImageByHexKey.get(key);
          if (!href) return null;

          const [px, py] = axialToPixel(hex.coord.q, hex.coord.r, HEX_SIZE);
          const cx = px + OFFSET_X;
          const cy = py + OFFSET_Y;
          const size = HEX_SIZE * 2.1;
          const clipId = `interspace-${key}-clip`;

          return (
            <Fragment key={key}>
              <clipPath id={clipId}>
                <polygon points={hexCorners(cx, cy, HEX_SIZE)} />
              </clipPath>
              <g clipPath={`url(#${clipId})`}>
                <image
                  href={href}
                  x={cx - size / 2}
                  y={cy - size / 2}
                  width={size}
                  height={size}
                  preserveAspectRatio="xMidYMid slice"
                  style={{ pointerEvents: 'none' }}
                />
              </g>
            </Fragment>
          );
        })}

        {/* Hex cells — drawn in ascending stroke-prominence order (plain/grid, then Deep
            Space/Interspace outline, then hint highlight, then selection) rather than hex-map
            insertion order. Each hex polygon's stroke is painted over its full edge, including
            the edges it shares with neighbors; if a plain neighbor happened to be drawn after a
            hex with a more prominent outline, its dim grid stroke silently overpainted that
            shared edge, leaving a gap in what should be a closed white/yellow border. Sorting by
            prominence guarantees every hex that needs a visible border paints its edges last. */}
        {[...hexEntries]
          .sort((a, b) => strokePriority(a) - strokePriority(b))
          .map((hex) => {
          const { q, r } = hex.coord;
          const [px, py] = axialToPixel(q, r, HEX_SIZE);
          const cx = px + OFFSET_X;
          const cy = py + OFFSET_Y;
          const key = hexKey(q, r);
          const isHighlighted = validSet.has(key);
          const isSelected = onHexClick
            ? selectedCoord !== null && selectedCoord.q === q && selectedCoord.r === r
            : multiSelect
              ? selectedHexSet.has(key)
              : activePlanet !== null && activePlanet.q === q && activePlanet.r === r;
          const isPrintedOnSectorArt = printedHexKeys.has(key);
          const standardSector = standardSectorByHexKey.get(key);
          const isStandardSectorLabel = standardSector?.origin.q === q
            && standardSector.origin.r === r;
          const showPlanetOverlay = !isPrintedOnSectorArt
            || hex.planet?.is_gaia_formed === true
            || hex.planet?.planet_type === 'LostPlanet';
          const isOwnedStructureInteractive =
            interactivePlayerId !== undefined
            && onOwnedStructureClick !== undefined
            && hex.structures.some((structure) => structure.owner === interactivePlayerId);
          const isPowerChargeStructureInteractive =
            devPowerChargeTargeting
            && interactivePlayerId !== undefined
            && hex.structures.some((structure) => (
              structure.owner === interactivePlayerId
              && structure.kind !== 'Satellite'
              && structure.kind !== 'SpaceStation'
            ));
          const isSpaceshipInteractive = onSpaceshipClick !== undefined && shipByHexKey.has(key);

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
              isPrintedOnSectorArt={isPrintedOnSectorArt}
              isStandardSectorArt={standardSector !== undefined}
              mutePrintedBackground={
                standardSector !== undefined
                && !CALM_STANDARD_SECTOR_IDS.has(standardSector.id)
                && !isStandardSectorLabel
              }
              showPlanetOverlay={showPlanetOverlay}
              hasPowerRing={powerRingHexKeys.has(key)}
              isDeepSpaceOutline={
                deepSpaceHexKeys.has(key)
                || (highlightInterspace && interspaceImageByHexKey.has(key))
              }
              isInNavigationRange={navigationRangeHexKeys.has(key)}
              navigationRangeColor="#7dd3fc"
              emphasizeStructure={emphasizeStructures}
              isInspectable={
                onHexInspect !== undefined
                || isSpaceshipInteractive
                || isOwnedStructureInteractive
                || isPowerChargeStructureInteractive
                || (multiSelect && (
                  selectedHexSet.has(key) || federationSelectableSet.has(key)
                ))
              }
              onClick={(event) => handleHexClick(hex, event)}
            />
          );
        })}
      </svg>
    </div>
  );
}
