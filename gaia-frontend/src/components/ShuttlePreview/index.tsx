import { useState, type MouseEvent as ReactMouseEvent } from 'react';
import { ExplorationBoard } from '../PlayerDashboard/ExplorationBoard';
import { FactionBoard } from '../PlayerDashboard/FactionBoard';
import { SpaceshipBoards } from '../SpaceshipBoards';
import { ResourceTokens } from '../ResourceTokens';
import { PlanetHex } from '../GameBoard/PlanetHex';
import { TerraformingToken } from '../TerraformingToken';
import { explorationShuttleImageSrc } from '../../assets/explorationShuttleImages';
import { factionBoardImageSrc } from '../../assets/factionBoardImages';
import { sectorImageSrc } from '../../assets/sectorImages';
import {
  structureImageSrc,
  type StructureAssetColor,
  type StructureAssetName,
} from '../../assets/structureImages';
import type { FactionId, GameAction, PlanetType, SpaceshipBoard } from '../../types/game';

const PREVIEW_PLAYERS: { player_id: number; faction: FactionId }[] = [
  { player_id: 0, faction: 'Terrans' },
  { player_id: 1, faction: 'Ivits' },
  { player_id: 2, faction: 'Gleens' },
  { player_id: 3, faction: 'Bescods' },
];

const PREVIEW_FACTIONS: FactionId[] = [
  'Terrans', 'Lantids', 'Xenos', 'Gleens', 'Taklons', 'Ambas',
  'HadschHallas', 'Ivits', 'Geodens', 'BalTaks', 'Firaks', 'Bescods',
  'Nevlas', 'Itars', 'Tinkeroids', 'Moweyds', 'SpaceGiants', 'Darkanians',
];

const PREVIEW_SHIPS: SpaceshipBoard[] = [
  {
    id: 'Twilight',
    explorers: [0, 1, 2, 3],
    artifact_pool: [],
    tech_tiles: [],
    federation_token: null,
  },
  {
    id: 'Rebellion',
    explorers: [0, 1, 2, 3],
    artifact_pool: [],
    tech_tiles: [],
    federation_token: null,
  },
  {
    id: 'TFMars',
    explorers: [0, 1, 2, 3],
    artifact_pool: [],
    tech_tiles: [],
    federation_token: null,
  },
  {
    id: 'Eclipse',
    explorers: [0, 1, 2, 3],
    artifact_pool: [],
    tech_tiles: [],
    federation_token: null,
  },
];

const COMPONENTS: { asset: StructureAssetName | 'exploration_shuttle'; label: string }[] = [
  { asset: 'mine', label: '광산' },
  { asset: 'trading_station', label: '교역소' },
  { asset: 'research_lab', label: '연구소' },
  { asset: 'planetary_institute', label: '행성 의회' },
  { asset: 'academy', label: '아카데미' },
  { asset: 'gaiaformer', label: '가이아포머' },
  { asset: 'marker', label: '위성/마커' },
  { asset: 'exploration_shuttle', label: '탐사 셔틀' },
];

type InteractiveStructureId = 'mine' | 'trading-station' | 'academy' | 'research-lab';
type HexCoordinate = { q: number; r: number };
type SatelliteHexId = 'center-bridge' | 'lower-bridge';
type PreviewPopupAnchor = { x: number; y: number };
type PreviewPlanetId = 'transdim' | 'empty' | 'gaia' | 'proto' | 'asteroid';

const PREVIEW_PLANET_TARGETS: {
  id: PreviewPlanetId;
  planetType: PlanetType;
  label: string;
  actionType: Extract<GameAction['type'], 'Build' | 'GaiaFormation'>;
  actionLabel: string;
  actionIcon: Extract<StructureAssetName, 'mine' | 'gaiaformer'>;
  help: string;
}[] = [
  {
    id: 'transdim',
    planetType: 'Transdim',
    label: '차원 변환 행성',
    actionType: 'GaiaFormation',
    actionLabel: '가이아 프로젝트 시작',
    actionIcon: 'gaiaformer',
    help: '가이아포머를 배치하고 필요한 파워를 가이아 구역으로 옮깁니다. 광산은 아직 놓지 않습니다.',
  },
  {
    id: 'empty',
    planetType: 'Desert',
    label: '빈 일반 행성',
    actionType: 'Build',
    actionLabel: '광산 건설',
    actionIcon: 'mine',
    help: '테라포밍 비용과 광산 비용을 지불하고 광산을 놓습니다.',
  },
  {
    id: 'gaia',
    planetType: 'Gaia',
    label: '가이아 행성',
    actionType: 'Build',
    actionLabel: '광산 건설',
    actionIcon: 'mine',
    help: '정보 큐브와 광산 비용을 지불하고 광산을 놓습니다.',
  },
  {
    id: 'proto',
    planetType: 'ProtoPlanet',
    label: '원시 행성',
    actionType: 'Build',
    actionLabel: '광산 건설',
    actionIcon: 'mine',
    help: '항상 3단계 테라포밍을 적용한 뒤 광산 비용을 지불합니다.',
  },
  {
    id: 'asteroid',
    planetType: 'Asteroid',
    label: '소행성',
    actionType: 'Build',
    actionLabel: '광산 건설',
    actionIcon: 'gaiaformer',
    help: '가이아포머 1개를 영구 소모하고 광산을 놓습니다. 광석과 크레딧은 들지 않습니다.',
  },
];

const INTERACTIVE_STRUCTURES: {
  id: InteractiveStructureId;
  asset: StructureAssetName;
  color: StructureAssetColor;
  label: string;
  power: number;
  x: number;
  y: number;
  hex: HexCoordinate;
}[] = [
  {
    id: 'mine', asset: 'mine', color: 'blue', label: '내 광산', power: 1, x: 87.6, y: 52.2,
    hex: { q: 2, r: -1 },
  },
  {
    id: 'trading-station',
    asset: 'trading_station',
    color: 'blue',
    label: '내 교역소',
    power: 2,
    x: 68.6,
    y: 41.1,
    hex: { q: 1, r: -1 },
  },
  {
    id: 'academy', asset: 'academy', color: 'blue', label: '내 아카데미', power: 3, x: 31.1, y: 62.8,
    hex: { q: -1, r: 1 },
  },
  {
    id: 'research-lab',
    asset: 'research_lab',
    color: 'blue',
    label: '내 연구소',
    power: 2,
    x: 30.8,
    y: 81.8,
    hex: { q: -1, r: 2 },
  },
];

const FEDERATION_SATELLITE_HEXES: {
  id: SatelliteHexId;
  label: string;
  x: number;
  y: number;
  hex: HexCoordinate;
}[] = [
  { id: 'center-bridge', label: '중앙 위성', x: 50, y: 52.1, hex: { q: 0, r: 0 } },
  { id: 'lower-bridge', label: '하단 위성', x: 50, y: 72.9, hex: { q: 0, r: 1 } },
];

type PreviewContext = 'idle' | 'structure' | 'planet' | 'source' | 'plan' | 'federation';

const PLANET_TARGET_ACTIONS: GameAction['type'][] = [
  'Build',
  'SpaceshipCreditTerraform',
  'TwilightRangeBuild',
  'TFMarsGaiaFormation',
  'EclipseAsteroidMine',
];

const YELLOW_PLANET_ACTIONS: GameAction['type'][] = [
  'Build',
  'SpaceshipCreditTerraform',
  'TwilightRangeBuild',
];

const BOARD_CHOICE_ACTIONS: GameAction['type'][] = [
  'TwilightReplayFederationToken',
  'RebellionGainTechTile',
  'EclipseResearchBoost',
];

const MINE_TARGET_ACTIONS: GameAction['type'][] = [
  'Upgrade',
  'FormFederation',
  'RebellionFreeTradingStation',
];

const ACTION_LABELS: Partial<Record<GameAction['type'], string>> = {
  Build: '기본 광산 건설',
  GaiaFormation: '가이아 프로젝트 시작',
  Upgrade: '구조물 업그레이드',
  FormFederation: '연방 형성',
  SpaceshipCreditTerraform: '함선 크레딧 테라포밍',
  TwilightFreeResearchLab: 'Twilight 무료 연구소 업그레이드',
  TwilightReplayFederationToken: 'Twilight 연방 토큰 효과 재사용',
  TwilightRangeBuild: 'Twilight +3 거리 광산 건설',
  RebellionGainTechTile: 'Rebellion 표준 기술 타일 획득',
  RebellionFreeTradingStation: 'Rebellion 무료 교역소 업그레이드',
  RebellionCreditsAndQic: 'Rebellion 크레딧·정보 큐브 획득',
  TFMarsTechBonus: 'T F Mars 기술 점수',
  TFMarsGaiaFormation: 'T F Mars 즉시 가이아포밍',
  EclipsePlanetTypeBonus: 'Eclipse 행성 종류 점수',
  EclipseResearchBoost: 'Eclipse 연구 부스트',
  EclipseAsteroidMine: 'Eclipse 소행성 광산 건설',
};

function actionNeedsPlanet(action: GameAction['type'] | null): boolean {
  return action !== null && PLANET_TARGET_ACTIONS.includes(action);
}

function actionNeedsMine(action: GameAction['type'] | null): boolean {
  return action !== null && MINE_TARGET_ACTIONS.includes(action);
}

function actionSupportsYellowPlanet(action: GameAction['type'] | null): boolean {
  return action !== null && YELLOW_PLANET_ACTIONS.includes(action);
}

function areHexesAdjacent(a: HexCoordinate, b: HexCoordinate): boolean {
  const dq = Math.abs(a.q - b.q);
  const dr = Math.abs(a.r - b.r);
  const ds = Math.abs((a.q + a.r) - (b.q + b.r));
  return Math.max(dq, dr, ds) === 1;
}

function connectedStructureGroups(): InteractiveStructureId[][] {
  const unseen = new Set(INTERACTIVE_STRUCTURES.map(({ id }) => id));
  const groups: InteractiveStructureId[][] = [];

  while (unseen.size > 0) {
    const first = unseen.values().next().value as InteractiveStructureId;
    const group: InteractiveStructureId[] = [];
    const queue = [first];
    unseen.delete(first);

    while (queue.length > 0) {
      const id = queue.shift() as InteractiveStructureId;
      const structure = INTERACTIVE_STRUCTURES.find((candidate) => candidate.id === id);
      if (!structure) continue;
      group.push(id);

      for (const candidate of INTERACTIVE_STRUCTURES) {
        if (unseen.has(candidate.id) && areHexesAdjacent(structure.hex, candidate.hex)) {
          unseen.delete(candidate.id);
          queue.push(candidate.id);
        }
      }
    }

    groups.push(group);
  }

  return groups;
}

const FEDERATION_STRUCTURE_GROUPS = connectedStructureGroups();

function structureGroupFor(id: InteractiveStructureId): InteractiveStructureId[] {
  return FEDERATION_STRUCTURE_GROUPS.find((group) => group.includes(id)) ?? [id];
}

function shortestSatelliteRoutes(
  fromGroup: InteractiveStructureId[],
  toGroup: InteractiveStructureId[],
): SatelliteHexId[][] {
  const fromStructures = INTERACTIVE_STRUCTURES.filter(({ id }) => fromGroup.includes(id));
  const toStructures = INTERACTIVE_STRUCTURES.filter(({ id }) => toGroup.includes(id));
  const queue: SatelliteHexId[][] = FEDERATION_SATELLITE_HEXES
    .filter((candidate) => fromStructures.some((structure) => (
      areHexesAdjacent(structure.hex, candidate.hex)
    )))
    .map(({ id }) => [id]);
  const routes: SatelliteHexId[][] = [];
  let shortestLength = Number.POSITIVE_INFINITY;

  while (queue.length > 0) {
    const path = queue.shift() as SatelliteHexId[];
    if (path.length > shortestLength) continue;
    const last = FEDERATION_SATELLITE_HEXES.find(({ id }) => id === path[path.length - 1]);
    if (!last) continue;

    if (toStructures.some((structure) => areHexesAdjacent(last.hex, structure.hex))) {
      shortestLength = path.length;
      routes.push(path);
      continue;
    }

    for (const candidate of FEDERATION_SATELLITE_HEXES) {
      if (!path.includes(candidate.id) && areHexesAdjacent(last.hex, candidate.hex)) {
        queue.push([...path, candidate.id]);
      }
    }
  }

  const uniqueRoutes = new Map<string, SatelliteHexId[]>();
  for (const route of routes) uniqueRoutes.set([...route].sort().join('|'), route);
  return [...uniqueRoutes.values()];
}

function BoardInteractionPreview() {
  const [context, setContext] = useState<PreviewContext>('idle');
  const [popupAnchor, setPopupAnchor] = useState<PreviewPopupAnchor | null>(null);
  const [selectedAction, setSelectedAction] = useState<GameAction['type'] | null>(null);
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);
  const [selectedPlanetId, setSelectedPlanetId] = useState<PreviewPlanetId | null>(null);
  const [federationTargets, setFederationTargets] = useState<Set<InteractiveStructureId>>(
    () => new Set(),
  );
  const [selectedFederationRoute, setSelectedFederationRoute] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const selectedStructure = INTERACTIVE_STRUCTURES.find(({ id }) => id === selectedTarget) ?? null;
  const selectedPlanet = PREVIEW_PLANET_TARGETS.find(({ id }) => id === selectedPlanetId) ?? null;
  const federationPower = INTERACTIVE_STRUCTURES.reduce(
    (total, structure) => total + (federationTargets.has(structure.id) ? structure.power : 0),
    0,
  );
  const redundantFederationGroups = FEDERATION_STRUCTURE_GROUPS.filter(
    (group) => group.every((id) => federationTargets.has(id)),
  ).filter((group) => {
    const groupPower = INTERACTIVE_STRUCTURES.reduce(
      (total, structure) => total + (group.includes(structure.id) ? structure.power : 0),
      0,
    );
    return federationPower - groupPower >= 7;
  });
  const federationStructureSelectionValid = federationPower >= 7
    && redundantFederationGroups.length === 0;
  const selectedFederationGroups = FEDERATION_STRUCTURE_GROUPS.filter(
    (group) => group.some((id) => federationTargets.has(id)),
  );
  const federationRoutes = selectedFederationGroups.length === 2
    ? shortestSatelliteRoutes(selectedFederationGroups[0], selectedFederationGroups[1])
    : [];
  const automaticallySelectedRoute = federationRoutes.length === 1 ? federationRoutes[0] : null;
  const manuallySelectedRoute = federationRoutes.find(
    (route) => route.join('|') === selectedFederationRoute,
  ) ?? null;
  const activeSatelliteRoute = automaticallySelectedRoute ?? manuallySelectedRoute ?? [];
  const satelliteRouteComplete = federationStructureSelectionValid
    && activeSatelliteRoute.length > 0;
  const activeRouteNodes = activeSatelliteRoute
    .map((id) => FEDERATION_SATELLITE_HEXES.find((candidate) => candidate.id === id))
    .filter((candidate): candidate is (typeof FEDERATION_SATELLITE_HEXES)[number] => Boolean(candidate));
  const federationRouteSegments = activeRouteNodes.length > 0 && selectedFederationGroups.length === 2
    ? (() => {
      const start = INTERACTIVE_STRUCTURES.find((structure) => (
        selectedFederationGroups[0].includes(structure.id)
        && areHexesAdjacent(structure.hex, activeRouteNodes[0].hex)
      ));
      const end = INTERACTIVE_STRUCTURES.find((structure) => (
        selectedFederationGroups[1].includes(structure.id)
        && areHexesAdjacent(structure.hex, activeRouteNodes[activeRouteNodes.length - 1].hex)
      ));
      if (!start || !end) return [];
      const points = [start, ...activeRouteNodes, end];
      return points.slice(0, -1).map((point, index) => ({ from: point, to: points[index + 1] }));
    })()
    : [];
  const upgradeOption = selectedStructure?.id === 'mine'
    ? { label: '교역소로 업그레이드', costs: { ore: 2, credits: 3 } as const }
    : selectedStructure?.id === 'trading-station'
      ? { label: '연구소 또는 행성 의회로 업그레이드', costs: null }
      : selectedStructure?.id === 'research-lab'
        ? { label: '아카데미로 업그레이드', costs: { ore: 3, credits: 6 } as const }
        : null;
  const viewportWidth = typeof window === 'undefined' ? 1440 : window.innerWidth;
  const viewportHeight = typeof window === 'undefined' ? 900 : window.innerHeight;
  const popupWidth = context === 'planet' ? 260 : 330;
  const popupEstimatedHeight = context === 'planet' ? 160 : 360;
  const popupLeft = popupAnchor
    ? Math.max(12, Math.min(popupAnchor.x + 14, viewportWidth - popupWidth - 12))
    : 12;
  const popupTop = popupAnchor
    ? Math.max(12, Math.min(
      popupAnchor.y - 32,
      viewportHeight - popupEstimatedHeight - 12,
    ))
    : 56;
  const popupLabel = selectedStructure?.label
    ?? selectedPlanet?.label
    ?? (selectedAction ? ACTION_LABELS[selectedAction] : null)
    ?? '행동 선택';

  const chooseAction = (action: GameAction['type'], contextAfter: PreviewContext = 'plan') => {
    setSelectedAction(action);
    setContext(contextAfter);
    setFederationTargets(new Set());
    setSelectedFederationRoute(null);
    setNotice(null);
  };

  const beginFederation = () => {
    const adjacentGroup = selectedStructure ? structureGroupFor(selectedStructure.id) : [];
    setSelectedAction('FormFederation');
    setContext('federation');
    setFederationTargets(new Set(adjacentGroup));
    setSelectedFederationRoute(null);
    setNotice(adjacentGroup.length > 1 ? '인접 건물 자동 포함' : null);
  };

  const chooseStructure = (
    id: InteractiveStructureId,
    event?: ReactMouseEvent<HTMLButtonElement>,
  ) => {
    setNotice(null);
    setSelectedTarget(id);
    setSelectedPlanetId(null);
    if (event) setPopupAnchor({ x: event.clientX, y: event.clientY });
    if (
      context === 'federation'
      && selectedAction === 'FormFederation'
    ) {
      const adjacentGroup = structureGroupFor(id);
      const removeGroup = adjacentGroup.every((structureId) => federationTargets.has(structureId));
      setFederationTargets((current) => {
        const next = new Set(current);
        for (const structureId of adjacentGroup) {
          if (removeGroup) next.delete(structureId);
          else next.add(structureId);
        }
        return next;
      });
      setSelectedFederationRoute(null);
      setNotice(adjacentGroup.length > 1
        ? `인접 묶음 ${removeGroup ? '해제' : '포함'} · ${adjacentGroup.length}`
        : null);
      return;
    }
    if (id === 'mine' && actionNeedsMine(selectedAction)) {
      setContext(selectedAction === 'FormFederation' ? 'federation' : 'plan');
      return;
    }
    if (id === 'trading-station' && selectedAction === 'TwilightFreeResearchLab') {
      setContext('plan');
      return;
    }
    if (selectedAction === 'FormFederation') {
      setContext('federation');
      return;
    }
    setSelectedAction(null);
    setFederationTargets(new Set());
    setContext('structure');
  };

  const choosePlanet = (event: ReactMouseEvent<HTMLButtonElement>) => {
    setNotice(null);
    setSelectedTarget('yellow-planet');
    setSelectedPlanetId('empty');
    setPopupAnchor({ x: event.clientX, y: event.clientY });
    setFederationTargets(new Set());
    setSelectedFederationRoute(null);
    setContext(actionNeedsPlanet(selectedAction) ? 'plan' : 'planet');
  };

  const choosePlanetExample = (
    id: PreviewPlanetId,
    event: ReactMouseEvent<HTMLButtonElement>,
  ) => {
    setNotice(null);
    setSelectedAction(null);
    setSelectedTarget(`planet-${id}`);
    setSelectedPlanetId(id);
    setPopupAnchor({ x: event.clientX, y: event.clientY });
    setFederationTargets(new Set());
    setSelectedFederationRoute(null);
    setContext('planet');
  };

  const chooseShipAction = (action: GameAction['type']) => {
    const activeElement = document.activeElement;
    if (activeElement instanceof HTMLElement) {
      const bounds = activeElement.getBoundingClientRect();
      setPopupAnchor({
        x: bounds.left + bounds.width / 2,
        y: bounds.top + bounds.height / 2,
      });
    }
    setSelectedAction(action);
    setSelectedTarget(null);
    setSelectedPlanetId(null);
    setFederationTargets(new Set());
    setSelectedFederationRoute(null);
    setContext('source');
    setNotice(null);
  };

  const resetSelection = () => {
    setContext('idle');
    setPopupAnchor(null);
    setSelectedAction(null);
    setSelectedTarget(null);
    setSelectedPlanetId(null);
    setFederationTargets(new Set());
    setSelectedFederationRoute(null);
    setNotice(null);
  };

  const confirmPreview = () => {
    const label = selectedPlanet?.actionType === selectedAction
      ? selectedPlanet.actionLabel
      : ACTION_LABELS[selectedAction ?? 'Build'] ?? '선택한 행동';
    setNotice(`${label} · 확정`);
  };

  return (
    <section id="action-preview" className="shuttle-preview-interaction" aria-label="보드 직접 조작 미리보기">
      <header className="shuttle-preview-interaction-header">
        <div>
          <span className="interaction-eyebrow">행동 단계 · 내 차례</span>
          <h2>우주에서 바로 행동하세요</h2>
        </div>
        <ResourceTokens
          label="현재 자원"
          values={{ ore: 6, credits: 15, knowledge: 4, qic: 3 }}
        />
      </header>

      <div className="shuttle-preview-interaction-stage">
        <div className="space-sector-interaction-card">
          <div className="interaction-card-heading">
            <strong>우주 섹터 02</strong>
            <span>대상부터 선택</span>
          </div>
          <div className="space-sector-component-preview-board">
            <img
              className="space-sector-component-preview-image"
              src={sectorImageSrc(2) ?? ''}
              alt="상호작용 우주 섹터 02"
            />
            {context === 'federation' && (
                <svg
                  className="federation-adjacency-link"
                  viewBox="0 0 100 100"
                  preserveAspectRatio="none"
                  aria-hidden="true"
                >
                  {federationTargets.has('mine')
                    && federationTargets.has('trading-station') && (
                      <>
                        <line x1="87.6" y1="52.2" x2="68.6" y2="41.1" />
                        <circle cx="87.6" cy="52.2" r="1.1" />
                        <circle cx="68.6" cy="41.1" r="1.1" />
                      </>
                    )}
                  {federationTargets.has('academy')
                    && federationTargets.has('research-lab') && (
                      <>
                        <line x1="31.1" y1="62.8" x2="30.8" y2="81.8" />
                        <circle cx="31.1" cy="62.8" r="1.1" />
                        <circle cx="30.8" cy="81.8" r="1.1" />
                      </>
                    )}
                  {federationRouteSegments.map(({ from, to }, index) => (
                    <line
                      key={`${from.x}-${from.y}-${to.x}-${to.y}`}
                      className="federation-satellite-link"
                      x1={from.x}
                      y1={from.y}
                      x2={to.x}
                      y2={to.y}
                      style={{ animationDelay: `${index * 120}ms` }}
                    />
                  ))}
                </svg>
              )}
            {INTERACTIVE_STRUCTURES.map((structure) => {
              const compatible = selectedAction === null
                || (structure.id === 'mine' && actionNeedsMine(selectedAction))
                || (structure.id === 'trading-station' && selectedAction === 'TwilightFreeResearchLab')
                || selectedAction === 'FormFederation';
              const selected = context === 'federation'
                ? federationTargets.has(structure.id)
                : selectedTarget === structure.id;
              return (
                <button
                  key={structure.id}
                  type="button"
                  className={`sector-action-target sector-action-target--hex sector-action-target--structure${
                    compatible ? ' sector-action-target--available' : ' sector-action-target--dimmed'
                  }${selected ? ' sector-action-target--selected' : ''}`}
                  style={{ left: `${structure.x}%`, top: `${structure.y}%` }}
                  disabled={!compatible}
                  onClick={(event) => chooseStructure(structure.id, event)}
                  aria-label={context === 'federation'
                    ? `${structure.label} — 연방에서 ${selected ? '제외' : '포함'}`
                    : `${structure.label} — 관련 행동 열기`}
                >
                  <img
                    className={`space-sector-component-preview-piece space-sector-component-preview-piece--${structure.asset}`}
                    src={structureImageSrc(structure.color, structure.asset)}
                    alt=""
                    aria-hidden
                  />
                  <span>{structure.label}</span>
                </button>
              );
            })}
            {context === 'federation' && activeSatelliteRoute.map((satelliteId) => {
              const satellite = FEDERATION_SATELLITE_HEXES.find(({ id }) => id === satelliteId);
              if (!satellite) return null;
              return (
                <span
                  key={satellite.id}
                  className="sector-action-target sector-action-target--hex sector-action-target--satellite sector-action-target--selected sector-action-target--automatic"
                  style={{ left: `${satellite.x}%`, top: `${satellite.y}%` }}
                  role="img"
                  aria-label={`${satellite.label} 자동 배치`}
                >
                  <img
                    className="space-sector-component-preview-piece space-sector-component-preview-piece--marker"
                    src={structureImageSrc('blue', 'marker')}
                    alt=""
                    aria-hidden
                  />
                </span>
              );
            })}
            <button
              type="button"
              className={`sector-action-target sector-action-target--hex sector-action-target--planet${
                selectedAction === null || actionSupportsYellowPlanet(selectedAction)
                  ? ' sector-action-target--available'
                  : ' sector-action-target--dimmed'
              }${selectedTarget === 'yellow-planet' ? ' sector-action-target--selected' : ''}`}
              style={{ left: '31.2%', top: '21.5%' }}
              disabled={selectedAction !== null && !actionSupportsYellowPlanet(selectedAction)}
              onClick={choosePlanet}
              aria-label="주황 행성 — 건설 대상"
            >
              <span>건설 가능</span>
            </button>
          </div>
          <div className="planet-action-examples" aria-label="행성 타일 행동 예시">
            {PREVIEW_PLANET_TARGETS.map((target) => (
              <button
                key={target.id}
                type="button"
                className={selectedPlanetId === target.id ? 'planet-action-example--selected' : undefined}
                onClick={(event) => choosePlanetExample(target.id, event)}
                aria-label={`${target.label} — 행동 보기`}
              >
                <svg viewBox="0 0 100 100" aria-hidden="true">
                  <PlanetHex
                    planetType={target.planetType}
                    cx={50}
                    cy={50}
                    size={100}
                    hexKey={`preview-${target.id}`}
                  />
                </svg>
                <span>{target.label}</span>
              </button>
            ))}
          </div>
        </div>

        {context !== 'idle' && popupAnchor && (
          <button
            type="button"
            className="shuttle-preview-popup-scrim"
            tabIndex={-1}
            onClick={resetSelection}
            aria-label="행동 취소"
          />
        )}
        {context !== 'idle' && popupAnchor && (
        <aside
          className={`structure-action-popup shuttle-preview-action-popup${
            context === 'planet' ? ' shuttle-preview-action-popup--planet' : ''
          }`}
          style={{
            left: popupLeft,
            top: popupTop,
            width: popupWidth,
            maxHeight: `calc(100vh - ${popupTop + 12}px)`,
          }}
          role="dialog"
          aria-label={`${popupLabel} 행동 팝업`}
          aria-live="polite"
        >

          {context === 'structure' && selectedStructure && (
            <>
              <div className="interaction-selection-title">
                <span className="interaction-selection-dot" />
                <div><small>선택한 대상</small><h3>{selectedStructure.label}</h3></div>
              </div>
              <div className="interaction-choice-list">
                {upgradeOption && (
                  <button type="button" onClick={() => chooseAction('Upgrade')}>
                    <span>
                      <strong>{upgradeOption.label}</strong>
                      {upgradeOption.costs ? (
                        <ResourceTokens
                          compact
                          label={`비용: 광석 ${upgradeOption.costs.ore}, 크레딧 ${upgradeOption.costs.credits}`}
                          values={upgradeOption.costs}
                        />
                      ) : <small>목적지 선택</small>}
                    </span><b>›</b>
                  </button>
                )}
                <button type="button" onClick={beginFederation}>
                  <span><strong>연방에 포함</strong><small>인접 건물 자동 연결</small></span><b>›</b>
                </button>
              </div>
            </>
          )}

          {context === 'planet' && selectedPlanet && (
            <button
              type="button"
              className="planet-rulebook-action"
              aria-label={selectedPlanet.actionLabel}
              aria-describedby={`planet-help-${selectedPlanet.id}`}
              onClick={() => chooseAction(selectedPlanet.actionType)}
            >
              <span className="planet-rulebook-action__primary">
                <img
                  src={structureImageSrc('blue', selectedPlanet.actionIcon)}
                  alt=""
                  aria-hidden="true"
                />
                <strong>{selectedPlanet.actionLabel}</strong>
              </span>
              <span
                id={`planet-help-${selectedPlanet.id}`}
                className="planet-rulebook-action__help"
                role="tooltip"
              >
                {selectedPlanet.help}
              </span>
            </button>
          )}

          {context === 'source' && selectedAction && (
            <>
              <div className="interaction-selection-title interaction-selection-title--source">
                <span className="interaction-source-icon">✦</span>
                <div><small>선택한 함선 행동</small><h3>{ACTION_LABELS[selectedAction] ?? selectedAction}</h3></div>
              </div>
              {selectedAction === 'TFMarsGaiaFormation' ? (
                <p className="interaction-target-prompt">대상 없음 · 트랜스딤</p>
              ) : selectedAction === 'EclipseAsteroidMine' ? (
                <p className="interaction-target-prompt">대상 없음 · 소행성</p>
              ) : actionNeedsPlanet(selectedAction) ? (
                <p className="interaction-target-prompt">행성 선택</p>
              ) : actionNeedsMine(selectedAction) || selectedAction === 'TwilightFreeResearchLab' ? (
                <p className="interaction-target-prompt">내 건물 선택</p>
              ) : BOARD_CHOICE_ACTIONS.includes(selectedAction) ? (
                <p className="interaction-target-prompt">토큰 · 기술 · 트랙 선택</p>
              ) : (
                <>
                  <p className="interaction-target-prompt">즉시 행동</p>
                  <button type="button" className="interaction-confirm" onClick={confirmPreview}>행동 확정</button>
                </>
              )}
            </>
          )}

          {context === 'plan' && selectedAction && (
            <>
              <div className="interaction-selection-title interaction-selection-title--source">
                <span className="interaction-source-icon">✓</span>
                <div>
                  <small>실행할 행동</small>
                  <h3>
                    {selectedPlanet?.actionType === selectedAction
                      ? selectedPlanet.actionLabel
                      : ACTION_LABELS[selectedAction] ?? selectedAction}
                  </h3>
                </div>
              </div>
              <div className="interaction-costs interaction-costs--tokens">
                {selectedAction === 'SpaceshipCreditTerraform' ? (
                  <>
                    <ResourceTokens
                      label="총비용: 광석 1, 크레딧 5"
                      values={{ ore: 1, credits: 5 }}
                    />
                    <span className="interaction-free-cost">테라포밍 1 무료</span>
                  </>
                ) : selectedAction === 'Build' ? (
                  selectedPlanet?.id === 'asteroid' ? (
                    <span className="interaction-free-cost">가이아포머 1개 영구 소모</span>
                  ) : (
                    <>
                      <ResourceTokens
                        label={`광산 건설비: 광석 1, 크레딧 2${
                          selectedPlanet?.id === 'gaia' ? ', 정보 큐브 1' : ''
                        }`}
                        values={{
                          ore: 1,
                          credits: 2,
                          ...(selectedPlanet?.id === 'gaia' ? { qic: 1 } : {}),
                        }}
                      />
                      {(selectedPlanet?.id === 'empty' || selectedPlanet?.id === 'proto') && (
                        <TerraformingToken steps={selectedPlanet.id === 'proto' ? 3 : 2} />
                      )}
                    </>
                  )
                ) : selectedAction === 'Upgrade' ? (
                  upgradeOption?.costs ? (
                    <ResourceTokens
                      label={`총비용: 광석 ${upgradeOption.costs.ore}, 크레딧 ${upgradeOption.costs.credits}`}
                      values={upgradeOption.costs}
                    />
                  ) : <span>목적지 선택</span>
                ) : (
                  <span>{selectedTarget === 'mine' ? '내 광산' : '선택한 행성'}</span>
                )}
              </div>
              <div className="interaction-resource-note">자원 변환 가능</div>
              <button type="button" className="interaction-confirm" onClick={confirmPreview}>행동 확정</button>
            </>
          )}

          {context === 'federation' && (
            <>
              <div className="interaction-selection-title">
                <span className="interaction-source-icon">⌬</span>
                <div><small>연방 연결</small><h3>연방 형성</h3></div>
              </div>
              <p className="interaction-target-prompt">
                {!federationStructureSelectionValid
                  ? '내 건물 묶음 선택'
                  : federationRoutes.length === 1
                    ? '최단 경로 자동 연결'
                    : federationRoutes.length > 1
                      ? '최단 경로 선택'
                      : '연결 경로 없음'}
              </p>
              <div className="federation-selected-list">
                {selectedFederationGroups.map((group) => {
                  const structures = INTERACTIVE_STRUCTURES.filter(({ id }) => group.includes(id));
                  const groupPower = structures.reduce((total, structure) => total + structure.power, 0);
                  return (
                    <span
                      key={group.join('-')}
                      className={group.length > 1 ? 'federation-selected-group--adjacent' : undefined}
                    >
                      {group.length > 1 && <b>인접 자동</b>}
                      {group.length > 1
                        ? `${structures.map(({ label, power }) => `${label} ${power}`).join(' + ')} = ${groupPower}`
                        : `${structures[0]?.label ?? '내 건물'} · ${groupPower}`}
                    </span>
                  );
                })}
              </div>
              <div className="federation-preview-progress" aria-label={`연방 파워 ${federationPower} / 7`}>
                <span style={{ width: `${Math.min(100, federationPower / 7 * 100)}%` }} />
                <b><small>파워</small><strong>{federationPower} / 7</strong></b>
              </div>
              {redundantFederationGroups.length > 0 && (
                <p className="federation-rule-warning">
                  선택한 인접 건물 묶음 중 하나를 제외해도 파워 7입니다. 규칙상 불필요한 묶음은
                  제외해야 합니다.
                </p>
              )}
              {federationStructureSelectionValid && federationRoutes.length > 1 && (
                <div className="federation-route-options" aria-label="동일한 최단 위성 경로">
                  {federationRoutes.map((route, index) => {
                    const routeKey = route.join('|');
                    return (
                      <button
                        key={routeKey}
                        type="button"
                        aria-pressed={selectedFederationRoute === routeKey}
                        onClick={() => setSelectedFederationRoute(routeKey)}
                      >
                        경로 {index + 1}
                      </button>
                    );
                  })}
                </div>
              )}
              {satelliteRouteComplete && (
                <div className="federation-satellite-cost" aria-label={`위성 ${activeSatelliteRoute.length}, 파워 ${activeSatelliteRoute.length}`}>
                  <div><span>위성</span><strong>{activeSatelliteRoute.length}</strong></div>
                  <div><span>파워</span><strong>{activeSatelliteRoute.length}</strong></div>
                </div>
              )}
              <button
                type="button"
                className="interaction-confirm"
                disabled={!satelliteRouteComplete}
                onClick={confirmPreview}
              >
                {redundantFederationGroups.length > 0
                  ? '불필요한 구조물을 제외하세요'
                  : federationPower < 7
                    ? `건물을 더 선택하세요 (${7 - federationPower})`
                    : federationRoutes.length === 0
                      ? '연결 경로 없음'
                      : federationRoutes.length > 1 && !manuallySelectedRoute
                        ? '최단 경로 선택'
                        : '연방 확정'}
              </button>
            </>
          )}

          {notice && <div className="interaction-notice" role="status">{notice}</div>}
        </aside>
        )}
      </div>

      <div className="spaceship-interaction-preview">
        <div className="interaction-card-heading">
          <strong>함선 액션</strong>
          <span>모든 함선 · 직접 선택</span>
        </div>
        <SpaceshipBoards
          spaceshipBoards={PREVIEW_SHIPS}
          players={PREVIEW_PLAYERS}
          myPlayerId={0}
          isMyTurn
          usedActionIds={[4]}
          selectedAction={selectedAction}
          onActionSelect={chooseShipAction}
        />
      </div>
    </section>
  );
}

export function ShuttlePreview() {
  return (
    <main className="shuttle-preview">
      <h1>보드 상호작용·컴포넌트 미리보기</h1>
      <BoardInteractionPreview />

      <section id="faction-pool-preview" className="shuttle-preview-faction-pool">
        <h2>종족 풀 얼굴 아이콘</h2>
        <div className="faction-pool-list">
          {PREVIEW_FACTIONS.map((faction) => (
            <span key={faction} className="faction-pool-badge">
              <span
                className="faction-pool-portrait"
                role="img"
                aria-label={`${faction} 캐릭터`}
                style={{ backgroundImage: `url(${factionBoardImageSrc(faction)})` }}
              />
              <span>{faction}</span>
            </span>
          ))}
        </div>
      </section>

      <section className="shuttle-preview-faction-board" aria-label="종족 보드 미리보기">
        <h2>자원 마커 겹침 예시</h2>
        <FactionBoard
          faction="Terrans"
          structures={[]}
          resources={{
            ore: 4,
            knowledge: 4,
            qic: 6,
            credits: 19,
            power: { bowl1: 4, bowl2: 4, bowl3: 0, gaia_bowl: 0, gaia_forming: 0 },
            spent_gaia_formers: 0,
          }}
          power={{ bowl1: 4, bowl2: 4, bowl3: 0, gaia_bowl: 0, gaia_forming: 0 }}
          gaiaformersAvailable={3}
          techTiles={[1, 2, 3, 4, 5, 6]}
          advancedTechTiles={[2, 3]}
          coveredTechTiles={[1, 2]}
          federationTokens={[1, 2, 3, 4, 5]}
          grayFederationTokens={[6]}
          booster={3}
          artifacts={[2, 7]}
        />
      </section>

      <section className="shuttle-preview-components" aria-label="업스케일 컴포넌트 모음">
        {COMPONENTS.map(({ asset, label }) => (
          <figure key={asset}>
            <img
              src={asset === 'exploration_shuttle'
                ? explorationShuttleImageSrc('Terrans')
                : structureImageSrc('blue', asset)}
              alt={label}
            />
            <figcaption>{label}</figcaption>
          </figure>
        ))}
      </section>

      <section className="shuttle-preview-exploration">
        <h2>개인 탐사 보드</h2>
        <ExplorationBoard faction="Terrans" shuttlesAvailable={3} />
      </section>
    </main>
  );
}
