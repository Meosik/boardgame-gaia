import { axialDistance, hexKey, rotateHexN } from './components/GameBoard/hex-utils';
import type { FinalScoringCondition, GameState, HexCoord, PlayerId, StructureType } from './types/game';

export type FinalScoringState = Pick<GameState, 'players' | 'board' | 'event_log'>;

export const FINAL_SCORING_LABELS: Record<FinalScoringCondition, string> = {
  MostGaiaPlanets: '가장 많은 가이아 행성',
  MostDeepSpaceSectors: '가장 많은 심우주 섹터',
  MostStructuresInFederation: '연방에 포함된 건물 수',
  MostPlanetTypes: '개척한 행성 유형 수',
  MostBuildings: '전체 건물 수',
  MostAsteroids: '개척한 소행성 수',
  MostSectors: '개척한 일반 우주 섹터 수',
  GreatestDistancePiAcademy: '행성 의회와 아카데미 사이 최장 거리',
  MostSatellites: '배치한 위성 수',
};

function key(coord: HexCoord): string {
  return hexKey(coord.q, coord.r);
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function coordinate(value: unknown): value is HexCoord {
  return record(value) && typeof value.q === 'number' && typeof value.r === 'number';
}

function federationHexes(state: FinalScoringState, playerId: PlayerId): Set<string> {
  const result = new Set<string>();
  for (const event of state.event_log ?? []) {
    // Replays retain actual formation decisions instead of native FederationFormed events.
    // Do not use federated_hexes: it also contains satellites and later auto-attachments.
    const formed = 'FederationFormed' in event ? event.FederationFormed : undefined;
    const decision = 'ReplayDecision' in event ? event.ReplayDecision : undefined;
    let hexes: unknown;
    if (record(formed) && formed.player === playerId) hexes = formed.hexes;
    if (record(decision) && decision.player === playerId && record(decision.action)
      && decision.action.type === 'FormFederation') hexes = decision.action.hexes;
    if (Array.isArray(hexes)) {
      for (const hex of hexes) if (coordinate(hex)) result.add(key(hex));
    }
  }
  return result;
}

function scoringBuilding(kind: StructureType): boolean {
  return kind !== 'Satellite' && kind !== 'SpaceStation';
}

function sectorAt(state: FinalScoringState, coord: HexCoord): number | undefined {
  return state.board.sectors.find(sector => {
    if (sector.id < 11 || sector.id > 18) return axialDistance(coord, sector.origin) <= 2;
    return [[0, 0], [1, 0], [0, 1]].some(([q, r]) => {
      const [rq, rr] = rotateHexN(q, r, sector.rotation);
      return coord.q === sector.origin.q + rq && coord.r === sector.origin.r + rr;
    });
  })?.id;
}

/** Mirrors ScoringEngine::final_scoring_metric, without changing snapshots or awarding VP.
 * The shared Rust/TypeScript fixture checks all nine metrics against the scoring engine. */
export function finalScoringMetric(
  state: FinalScoringState,
  playerId: PlayerId,
  condition: FinalScoringCondition,
): number {
  const player = state.players.find(p => p.player_id === playerId);
  if (!player) return 0;
  const structures = new Set(player.structures.map(s => key(s.hex)));
  const planets = Object.values(state.board.hexes).filter(hex => hex.planet
    && (hex.planet.owner === playerId || structures.has(key(hex.coord))));
  const ownTypes = planets.filter(hex => !(player.faction === 'Lantids'
    && structures.has(key(hex.coord)) && hex.planet!.owner !== null && hex.planet!.owner !== playerId));
  const artifacts = player.artifact_mines ?? [];
  const lost = state.board.lost_planet;
  const untrackedLost = lost !== null && state.board.hexes[key(lost)]?.planet?.owner === playerId
    && !structures.has(key(lost));

  switch (condition) {
    case 'MostStructuresInFederation': {
      const federated = federationHexes(state, playerId);
      return player.structures.filter(s => scoringBuilding(s.kind) && federated.has(key(s.hex))).length
        + Number(untrackedLost && lost !== null && federated.has(key(lost)));
    }
    case 'MostBuildings':
      return player.structures.filter(s => scoringBuilding(s.kind)).length + Number(untrackedLost) + artifacts.length;
    case 'MostPlanetTypes':
      return new Set([...ownTypes.map(h => h.planet!.is_gaia_formed ? 'Gaia' : h.planet!.planet_type), ...artifacts]).size;
    case 'MostGaiaPlanets':
      return ownTypes.filter(h => h.planet!.is_gaia_formed || h.planet!.planet_type === 'Gaia').length;
    case 'MostSectors':
    case 'MostDeepSpaceSectors': {
      const deep = condition === 'MostDeepSpaceSectors';
      const sectors = planets.map(h => sectorAt(state, h.coord))
        .filter((id): id is number => id !== undefined && (id >= 11 && id <= 18) === deep);
      return new Set(sectors).size;
    }
    case 'MostSatellites':
      return Object.values(state.board.hexes).reduce((n, h) => n + h.satellites.filter(id => id === playerId).length, 0)
        + player.structures.filter(s => s.kind === 'SpaceStation').length;
    case 'MostAsteroids':
      return planets.filter(h => h.planet!.planet_type === 'Asteroid').length
        + artifacts.filter(type => type === 'Asteroid').length;
    case 'GreatestDistancePiAcademy': {
      const institutes = player.structures.filter(s => s.kind === 'PlanetaryInstitute');
      const academies = player.structures.filter(s => typeof s.kind === 'object' && 'Academy' in s.kind);
      return Math.max(0, ...institutes.flatMap(pi => academies.map(a => axialDistance(pi.hex, a.hex))));
    }
  }
}
