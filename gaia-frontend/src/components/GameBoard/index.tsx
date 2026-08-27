import { Fragment, useMemo } from 'react';
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
import { sectorImageSrc, deepSpaceSectorImageSrc } from '../../assets/sectorImages';
import {
  asteroidInterspaceImageSrc,
  blankInterspaceImageSrc,
  protoPlanetInterspaceImageSrc,
  spaceshipInterspaceImageSrc,
} from '../../assets/interspaceTileImages';
import type {
  BoardState,
  FactionId,
  HexCoord,
  PlayerId,
  PlayerState,
  SpaceshipId,
} from '../../types/game';

const HEX_SIZE = 36;
const SVG_WIDTH = 1800;
const SVG_HEIGHT = 1400;
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

// A Deep Space sector (Lost Fleet expansion, ids 11-18) is a 3-hex
// L-tromino at relative offsets (0,0)/(1,0)/(0,1) — see
// `gaia-engine/data/sectors.toml`'s "Deep Space Sectors" block, which
// `insert_sector` places by rotating each of these same three offsets and
// adding the sector's origin. The three hex centers plus one hex-radius of
// margin on every side span roughly 3.5 hex-widths in both axes, which is
// also close to the scanned `deep_space_sector_*.jpg` art's own ~1:1 aspect
// ratio (822x818) — sized a bit generous (3.6) so `xMidYMid slice` always
// has art to crop from rather than ever showing empty space at a corner.
const DEEP_SPACE_HEX_OFFSETS: [number, number][] = [
  [0, 0],
  [1, 0],
  [0, 1],
];
const DEEP_SPACE_IMAGE_WIDTH = HEX_SIZE * 3.6;
const DEEP_SPACE_IMAGE_HEIGHT = HEX_SIZE * 3.6;
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
// The scans' own 3-way hex vertex (where the tromino's gridlines converge —
// visible in every `deep_space_sector_*.jpg` as the point 2+ blue grid lines
// meet, usually next to a small printed sector-id label) sits well off the
// raw file's own pixel center (822x818 -> center (411,409)), consistently
// across all 8 scans (measured directly: mean vertex pixel (449,402) across
// deep_space_sector_01..08.jpg, individual values 428-474/389-407 — a real,
// consistent scan-framing offset, not per-photo noise). `preserveAspectRatio
//="xMidYMid slice"` centers the photo's own pixel-center at the `<image>`
// box's center by construction, so without correction the true vertex
// (and everything else in the photo) renders shifted from where the hex
// grid actually is — the "whole board shifted toward one corner" symptom.
// These two constants are that fixed pixel offset (vertex minus photo
// center, in the scan's own unrotated pixel space) plus the scan's own
// dimensions, used below to shift the image box back by the equivalent
// amount post-scale so the vertex — not the raw file's geometric center —
// lands on the true world position `sectorCentroidPixel` computes.
const DEEP_SPACE_PHOTO_WIDTH = 822;
const DEEP_SPACE_PHOTO_HEIGHT = 818;
const DEEP_SPACE_VERTEX_OFFSET_X = 449 - DEEP_SPACE_PHOTO_WIDTH / 2;
const DEEP_SPACE_VERTEX_OFFSET_Y = 402 - DEEP_SPACE_PHOTO_HEIGHT / 2;

interface StarDot { cx: number; cy: number; r: number; opacity: number }

interface Props {
  board: BoardState;
  players?: PlayerState[];
  validTargets?: HexCoord[];
  selectedCoord?: HexCoord | null;
  onHexClick?: (coord: HexCoord) => void;
}

export function GameBoard({
  board,
  players = [],
  validTargets = [],
  selectedCoord = null,
  onHexClick,
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
    if (onHexClick) {
      if (!validSet.has(hexKey(coord.q, coord.r))) return;
      onHexClick(coord);
      return;
    }
    if (!selectedAction) return;
    if (multiSelect) {
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
  // Hexes whose planet is already drawn directly on a sector's background
  // art (both the 19-hex standard sectors and the 3-hex Deep Space
  // tromino's art print their Asteroid/ProtoPlanet), so `HexCell` skips
  // rendering a second, separate planet icon on top of it. Standard sectors
  // use the same "within 2 rings of origin" radius their whole 19-hex disk
  // occupies; Deep Space sectors need their exact 3 hexes instead — that
  // radius would be far too generous for a sector this small and would
  // wrongly swallow up unrelated neighboring hexes.
  const sectorPrintedHexKeys = useMemo(() => {
    const keys = new Set<string>();
    for (const hex of hexEntries) {
      const printed = board.sectors.some((sector) => {
        if (sector.id <= 10) {
          return axialDistance(hex.coord, sector.origin) <= 2;
        }
        return DEEP_SPACE_HEX_OFFSETS.some(([relQ, relR]) => {
          const [rq, rr] = rotateHexN(relQ, relR, sector.rotation);
          return hex.coord.q === rq + sector.origin.q && hex.coord.r === rr + sector.origin.r;
        });
      });
      if (printed) keys.add(hexKey(hex.coord.q, hex.coord.r));
    }
    return keys;
  }, [hexEntries, board.sectors]);
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
  // leaving these hexes as bare grid cells the way `sectorImageSrc`-less ids
  // used to.
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
            ? deepSpaceSectorImageSrc(sector.id)
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
          const photoOffset = isDeepSpace ? DEEP_SPACE_PHOTO_ROTATION_OFFSET : 0;
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
          // `xMidYMid slice`'s cover-scale factor — height is the limiting
          // dimension (818 < 822), so that's what maps 1:1 to `height`; see
          // `DEEP_SPACE_VERTEX_OFFSET_X/Y`'s comment for why this is needed.
          const deepSpaceScale = isDeepSpace ? height / DEEP_SPACE_PHOTO_HEIGHT : 0;
          const imgX = imgCx - width / 2 - DEEP_SPACE_VERTEX_OFFSET_X * deepSpaceScale;
          const imgY = imgCy - height / 2 - DEEP_SPACE_VERTEX_OFFSET_Y * deepSpaceScale;

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
                  preserveAspectRatio="xMidYMid slice"
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

        {/* Hex cells */}
        {hexEntries.map((hex) => {
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
          const showPlanetOverlay = !isPrintedOnSectorArt
            || hex.planet?.is_gaia_formed === true
            || hex.planet?.planet_type === 'LostPlanet';

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
              showPlanetOverlay={showPlanetOverlay}
              hasPowerRing={powerRingHexKeys.has(key)}
              onClick={() => handleHexClick(hex.coord)}
            />
          );
        })}
      </svg>
    </div>
  );
}
