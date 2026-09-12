import { axialDistance, rotateHexN } from './components/GameBoard/hex-utils';
import { PLANET_TYPE_DISPLAY_NAMES, SPACESHIP_DISPLAY_NAMES } from './displayNames';
import type { BoardState, HexCoord, Planet, SpaceshipId } from './types/game';

/** Deep Space sectors are 3-hex trominoes — the offsets `GameBoard` clips their art with. */
const DEEP_SPACE_HEX_OFFSETS: [number, number][] = [
  [0, 0],
  [1, 0],
  [0, 1],
];

/** Planet names that already read as a planet on their own take no `행성` suffix. */
const BARE_PLANET_NAMES = new Set(['Asteroid', 'ProtoPlanet', 'LostPlanet', 'Transdim']);

function planetLabel(planet: Planet | null | undefined): string | null {
  if (!planet) return null;
  if (planet.is_gaia_formed || planet.planet_type === 'Gaia') return '가이아 행성';
  const name = PLANET_TYPE_DISPLAY_NAMES[planet.planet_type];
  if (!name) return null;
  return BARE_PLANET_NAMES.has(planet.planet_type) ? name : `${name} 행성`;
}

/**
 * Where a hex is, in the words printed on the physical board — "3번 섹터 화산 행성" rather than the
 * axial coordinate "(1,-1)", which means nothing to a player looking at the table. Sector
 * membership is derived from `Sector.origin`/`rotation` the same way `GameBoard` places sector art.
 * Falls back to the raw coordinate when no board is available (old snapshots, isolated tests).
 */
export function hexLocationLabel(
  coord: HexCoord | null | undefined,
  board?: BoardState | null,
): string {
  if (!coord || typeof coord.q !== 'number' || typeof coord.r !== 'number') return '알 수 없는 칸';
  if (!board) return `(${coord.q},${coord.r})`;

  const planet = planetLabel(board.hexes?.[`${coord.q},${coord.r}`]?.planet);

  const ship = (Object.entries(board.spaceship_tiles ?? {}) as [SpaceshipId, HexCoord][]).find(
    ([, tile]) => tile && tile.q === coord.q && tile.r === coord.r,
  )?.[0];
  if (ship) return `${SPACESHIP_DISPLAY_NAMES[ship] ?? ship} 함선 칸`;

  const standard = (board.sectors ?? []).find(
    (sector) => sector.id <= 10 && axialDistance(coord, sector.origin) <= 2,
  );
  if (standard) return planet ? `${standard.id}번 섹터 ${planet}` : `${standard.id}번 섹터`;

  const deepSpace = (board.sectors ?? []).find(
    (sector) => sector.id > 10 && DEEP_SPACE_HEX_OFFSETS.some(([relQ, relR]) => {
      const [rotatedQ, rotatedR] = rotateHexN(relQ, relR, sector.rotation);
      return coord.q === rotatedQ + sector.origin.q && coord.r === rotatedR + sector.origin.r;
    }),
  );
  if (deepSpace) {
    return planet ? `심우주 ${deepSpace.id}번 섹터 ${planet}` : `심우주 ${deepSpace.id}번 섹터`;
  }

  // Everything else is one of the 10 single-hex Interspace tiles filling the gaps between sectors.
  return planet ? `인터스페이스 ${planet}` : '인터스페이스 빈 칸';
}
