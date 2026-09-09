import { hexKey } from './GameBoard/hex-utils';
import type { GameState, Hex, HexCoord, PlayerId, PlayerState, StructureType } from '../types/game';

const FEDERATION_MIN_POWER = 7;
const SATELLITE_SUPPLY = 25;
const DIRECTIONS = [
  [1, 0], [1, -1], [0, -1], [-1, 0], [-1, 1], [0, 1],
] as const;

export interface FederationSelectionStatus {
  valid: boolean;
  reason: string;
  planetHexes: HexCoord[];
  satelliteHexes: HexCoord[];
  power: number;
  minimumPower: number;
}

function neighboringKeys(coord: HexCoord): string[] {
  return DIRECTIONS.map(([dq, dr]) => hexKey(coord.q + dq, coord.r + dr));
}

function isAcademy(kind: StructureType): boolean {
  return typeof kind === 'object' && 'Academy' in kind;
}

function structurePower(kind: StructureType): number {
  if (kind === 'Mine' || kind === 'SpaceStation') return 1;
  if (kind === 'TradingStation' || kind === 'ResearchLab') return 2;
  if (kind === 'PlanetaryInstitute' || isAcademy(kind)) return 3;
  return 0;
}

function ownsColonizedHex(hex: Hex | undefined, playerId: PlayerId): boolean {
  if (!hex) return false;
  return hex.structures.some(({ owner, kind }) => owner === playerId && kind !== 'Satellite')
    || Boolean(hex.planet?.planet_type === 'LostPlanet' && hex.planet.owner === playerId);
}

function isLegalSatelliteHex(gameState: GameState, hex: Hex | undefined): boolean {
  if (!hex || hex.planet !== null || hex.structures.length > 0 || hex.satellites.length > 0) {
    return false;
  }
  const key = hexKey(hex.coord.q, hex.coord.r);
  return !Object.values(gameState.board.spaceship_tiles)
    .some((coord) => coord !== undefined && hexKey(coord.q, coord.r) === key);
}

function activeTechTile(player: PlayerState, tile: number): boolean {
  return Boolean(player.tech_tiles?.includes(tile) && !player.covered_tech_tiles?.includes(tile));
}

function selectedFederationPower(
  gameState: GameState,
  player: PlayerState,
  planetHexes: HexCoord[],
  includeExistingIvitsFederation: boolean,
): number {
  const coords = includeExistingIvitsFederation
    ? [...(player.federated_hexes ?? []), ...planetHexes]
    : planetHexes;
  const uniqueKeys = new Set(coords.map(({ q, r }) => hexKey(q, r)));
  let power = 0;
  for (const key of uniqueKeys) {
    const hex = gameState.board.hexes[key];
    const ownStructures = hex?.structures.filter(({ owner, kind }) => (
      owner === player.player_id && kind !== 'Satellite'
    )) ?? [];
    power += ownStructures.reduce((sum, { kind }) => sum + structurePower(kind), 0);
    if (ownStructures.length === 0
      && hex?.planet?.planet_type === 'LostPlanet'
      && hex.planet.owner === player.player_id) {
      power += 1;
    }
    if (includeExistingIvitsFederation) continue;
    if (player.faction === 'Bescods'
      && player.structures.some(({ kind }) => kind === 'PlanetaryInstitute')
      && hex?.planet?.planet_type === 'Titanium'
      && !hex.planet.is_gaia_formed) {
      power += ownStructures.length;
    }
    if (player.faction === 'Moweyds'
      && player.moweyds_power_ring_hexes?.some(({ q, r }) => hexKey(q, r) === key)) {
      power += 2;
    }
    if (activeTechTile(player, 6)) {
      power += ownStructures.filter(({ kind }) => (
        kind === 'PlanetaryInstitute' || isAcademy(kind)
      )).length;
    }
  }
  return power;
}

function isConnected(coords: HexCoord[]): boolean {
  if (coords.length === 0) return false;
  const remaining = new Set(coords.map(({ q, r }) => hexKey(q, r)));
  const queue = [remaining.values().next().value as string];
  remaining.delete(queue[0]);
  for (let index = 0; index < queue.length; index += 1) {
    const [q, r] = queue[index].split(',').map(Number);
    for (const key of neighboringKeys({ q, r })) {
      if (!remaining.delete(key)) continue;
      queue.push(key);
    }
  }
  return remaining.size === 0;
}

function minimumSatelliteCount(
  gameState: GameState,
  player: PlayerState,
  requiredHexes: HexCoord[],
  isIvitsGrowth: boolean,
): number | null {
  const requiredKeys = new Set(requiredHexes.map(({ q, r }) => hexKey(q, r)));
  const existingKeys = new Set((player.federated_hexes ?? []).map(({ q, r }) => hexKey(q, r)));
  const coords: HexCoord[] = [];
  const weights: number[] = [];

  for (const hex of Object.values(gameState.board.hexes)) {
    const key = hexKey(hex.coord.q, hex.coord.r);
    const isExistingAnchor = isIvitsGrowth && existingKeys.has(key);
    const isOwnedPlanet = ownsColonizedHex(hex, player.player_id);
    const isRequired = requiredKeys.has(key);
    if (!isIvitsGrowth
      && !isRequired
      && neighboringKeys(hex.coord).some((neighbor) => existingKeys.has(neighbor))) {
      continue;
    }
    const weight = isExistingAnchor || (isOwnedPlanet && !existingKeys.has(key))
      ? 0
      : isLegalSatelliteHex(gameState, hex) ? 1 : null;
    if (weight === null) continue;
    coords.push(hex.coord);
    weights.push(weight);
  }

  const indexByKey = new Map(coords.map((coord, index) => [hexKey(coord.q, coord.r), index]));
  const neighbors = coords.map((coord) => neighboringKeys(coord)
    .map((key) => indexByKey.get(key))
    .filter((index): index is number => index !== undefined));
  const zeroComponent: (number | null)[] = Array(coords.length).fill(null);
  let componentCount = 0;
  for (let start = 0; start < coords.length; start += 1) {
    if (weights[start] !== 0 || zeroComponent[start] !== null) continue;
    zeroComponent[start] = componentCount;
    const queue = [start];
    for (let cursor = 0; cursor < queue.length; cursor += 1) {
      for (const neighbor of neighbors[queue[cursor]]) {
        if (weights[neighbor] !== 0 || zeroComponent[neighbor] !== null) continue;
        zeroComponent[neighbor] = componentCount;
        queue.push(neighbor);
      }
    }
    componentCount += 1;
  }

  const terminals: number[] = [];
  for (const coord of requiredHexes) {
    const index = indexByKey.get(hexKey(coord.q, coord.r));
    if (index === undefined || zeroComponent[index] === null) return null;
    const component = zeroComponent[index] as number;
    if (!terminals.includes(component)) terminals.push(component);
  }
  if (isIvitsGrowth) {
    const anchor = player.federated_hexes?.[0];
    if (!anchor) return null;
    const index = indexByKey.get(hexKey(anchor.q, anchor.r));
    if (index === undefined || zeroComponent[index] === null) return null;
    const component = zeroComponent[index] as number;
    if (!terminals.includes(component)) terminals.push(component);
  }
  if (terminals.length <= 1) return 0;
  if (terminals.length > 12) return null;

  const stateCount = 1 << terminals.length;
  const infinity = Number.MAX_SAFE_INTEGER;
  const costs = Array.from({ length: stateCount }, () => Array(coords.length).fill(infinity));
  terminals.forEach((component, terminal) => {
    zeroComponent.forEach((nodeComponent, node) => {
      if (nodeComponent === component) costs[1 << terminal][node] = 0;
    });
  });

  for (let mask = 1; mask < stateCount; mask += 1) {
    for (let subset = (mask - 1) & mask; subset > 0; subset = (subset - 1) & mask) {
      const other = mask ^ subset;
      if (subset >= other) continue;
      for (let node = 0; node < coords.length; node += 1) {
        if (costs[subset][node] === infinity || costs[other][node] === infinity) continue;
        costs[mask][node] = Math.min(
          costs[mask][node],
          costs[subset][node] + costs[other][node] - weights[node],
        );
      }
    }

    const visited = Array(coords.length).fill(false);
    for (let count = 0; count < coords.length; count += 1) {
      let current = -1;
      for (let node = 0; node < coords.length; node += 1) {
        if (!visited[node] && (current < 0 || costs[mask][node] < costs[mask][current])) {
          current = node;
        }
      }
      if (current < 0 || costs[mask][current] === infinity) break;
      visited[current] = true;
      for (const neighbor of neighbors[current]) {
        costs[mask][neighbor] = Math.min(
          costs[mask][neighbor],
          costs[mask][current] + weights[neighbor],
        );
      }
    }
  }
  return Math.min(...costs[stateCount - 1]);
}

export function validateFederationSelection(
  gameState: GameState,
  playerId: PlayerId,
  selectedHexes: HexCoord[],
): FederationSelectionStatus {
  const player = gameState.players.find(({ player_id }) => player_id === playerId);
  const empty = {
    valid: false,
    reason: '내 건물을 선택하세요.',
    planetHexes: [],
    satelliteHexes: [],
    power: 0,
    minimumPower: FEDERATION_MIN_POWER,
  } satisfies FederationSelectionStatus;
  if (!player) return empty;

  const planetHexes = selectedHexes.filter((coord) => (
    ownsColonizedHex(gameState.board.hexes[hexKey(coord.q, coord.r)], playerId)
  ));
  const satelliteHexes = selectedHexes.filter((coord) => (
    !ownsColonizedHex(gameState.board.hexes[hexKey(coord.q, coord.r)], playerId)
  ));
  const isIvitsGrowth = player.faction === 'Ivits' && (player.federated_hexes?.length ?? 0) > 0;
  const minimumPower = isIvitsGrowth
    ? FEDERATION_MIN_POWER * (player.federation_tokens.length + 1)
    : player.faction === 'Xenos' ? 6 : FEDERATION_MIN_POWER;
  const power = selectedFederationPower(gameState, player, planetHexes, isIvitsGrowth);
  const status = (valid: boolean, reason: string): FederationSelectionStatus => ({
    valid,
    reason,
    planetHexes,
    satelliteHexes,
    power,
    minimumPower,
  });

  if (planetHexes.length === 0) return status(false, '내 건물을 선택하세요.');
  if (selectedHexes.some((coord) => player.federated_hexes?.some(
    ({ q, r }) => q === coord.q && r === coord.r,
  ))) return status(false, '이미 다른 연방에 사용한 칸은 다시 선택할 수 없습니다.');
  if (satelliteHexes.some((coord) => !isLegalSatelliteHex(
    gameState,
    gameState.board.hexes[hexKey(coord.q, coord.r)],
  ))) return status(false, '위성을 놓을 수 없는 칸이 포함되어 있습니다.');

  const alreadyPlaced = Object.values(gameState.board.hexes)
    .filter((hex) => hex.satellites.includes(playerId)).length;
  if (alreadyPlaced + satelliteHexes.length > SATELLITE_SUPPLY) {
    return status(false, '남은 위성이 부족합니다.');
  }
  const satelliteResource = isIvitsGrowth
    ? player.resources.qic
    : player.resources.power.bowl1 + player.resources.power.bowl2 + player.resources.power.bowl3;
  if (satelliteHexes.length > satelliteResource) {
    return status(false, isIvitsGrowth ? '정보 큐브가 부족합니다.' : '위성에 사용할 파워가 부족합니다.');
  }
  if (!isIvitsGrowth) {
    const existingKeys = new Set((player.federated_hexes ?? []).map(({ q, r }) => hexKey(q, r)));
    if (selectedHexes.some((coord) => neighboringKeys(coord).some((key) => existingKeys.has(key)))) {
      return status(false, '기존 연방과 인접한 칸은 새 연방에 사용할 수 없습니다.');
    }
  }

  const connected = isIvitsGrowth
    ? [...selectedHexes, ...(player.federated_hexes ?? [])]
    : selectedHexes;
  if (!isConnected(connected)) return status(false, '선택한 건물과 위성 경로가 연결되지 않았습니다.');
  if (power < minimumPower) return status(false, `연방 파워가 ${minimumPower - power} 부족합니다.`);

  for (let dropped = 0; dropped < selectedHexes.length; dropped += 1) {
    const remaining = selectedHexes.filter((_, index) => index !== dropped);
    const remainingConnected = isIvitsGrowth
      ? [...remaining, ...(player.federated_hexes ?? [])]
      : remaining;
    if (!isConnected(remainingConnected)) continue;
    const remainingPlanetHexes = remaining.filter((coord) => ownsColonizedHex(
      gameState.board.hexes[hexKey(coord.q, coord.r)],
      playerId,
    ));
    if (selectedFederationPower(gameState, player, remainingPlanetHexes, isIvitsGrowth) >= minimumPower) {
      return status(false, '빼도 되는 건물이나 위성이 포함되어 있습니다.');
    }
  }

  const minimumSatellites = minimumSatelliteCount(gameState, player, planetHexes, isIvitsGrowth);
  if (minimumSatellites === null || satelliteHexes.length !== minimumSatellites) {
    return status(false, minimumSatellites === null
      ? '이 건물들을 연결할 수 있는 위성 경로가 없습니다.'
      : `최소 위성 ${minimumSatellites}개 경로로 연결해야 합니다.`);
  }
  return status(true, '연방 구축 가능');
}

export function selectableFederationHexes(
  gameState: GameState,
  playerId: PlayerId,
  selectedHexes: HexCoord[],
): HexCoord[] {
  const player = gameState.players.find(({ player_id }) => player_id === playerId);
  if (!player) return [];
  const selectedKeys = new Set(selectedHexes.map(({ q, r }) => hexKey(q, r)));
  const existingKeys = new Set((player.federated_hexes ?? []).map(({ q, r }) => hexKey(q, r)));
  const isIvitsGrowth = player.faction === 'Ivits' && existingKeys.size > 0;
  const selectedSatelliteCount = selectedHexes.filter((coord) => (
    !ownsColonizedHex(gameState.board.hexes[hexKey(coord.q, coord.r)], playerId)
  )).length;
  const alreadyPlaced = Object.values(gameState.board.hexes)
    .filter((hex) => hex.satellites.includes(playerId)).length;
  const satelliteResource = isIvitsGrowth
    ? player.resources.qic
    : player.resources.power.bowl1 + player.resources.power.bowl2 + player.resources.power.bowl3;
  const canAddSatellite = selectedSatelliteCount < satelliteResource
    && alreadyPlaced + selectedSatelliteCount < SATELLITE_SUPPLY;

  return Object.values(gameState.board.hexes)
    .filter((hex) => {
      const key = hexKey(hex.coord.q, hex.coord.r);
      if (selectedKeys.has(key)) return true;
      if (existingKeys.has(key)) return false;
      const ownsHex = ownsColonizedHex(hex, playerId);
      if (ownsHex) {
        return isIvitsGrowth
          || !neighboringKeys(hex.coord).some((neighbor) => existingKeys.has(neighbor));
      }
      if (!canAddSatellite || !isLegalSatelliteHex(gameState, hex)) return false;
      if (!isIvitsGrowth && neighboringKeys(hex.coord).some((neighbor) => existingKeys.has(neighbor))) {
        return false;
      }
      const routeAnchors = selectedKeys.size > 0 ? selectedKeys : isIvitsGrowth ? existingKeys : new Set<string>();
      return neighboringKeys(hex.coord).some((neighbor) => routeAnchors.has(neighbor));
    })
    .map(({ coord }) => coord);
}
