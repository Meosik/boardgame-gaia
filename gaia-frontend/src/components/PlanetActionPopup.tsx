import { useState } from 'react';
import { ResourceTokens, type DisplayResource } from './ResourceTokens';
import { TerraformingToken } from './TerraformingToken';
import { structureImageSrc } from '../assets/structureImages';
import type {
  BoardState,
  FactionId,
  GameAction,
  Hex,
  HexCoord,
  PlanetType,
  PlayerState,
} from '../types/game';

const STANDARD_PLANET_RING: PlanetType[] = [
  'Terra', 'Swamp', 'Desert', 'Oxide', 'Titanium', 'Volcanic', 'Ice',
];

const RESOURCE_LABEL: Record<DisplayResource, string> = {
  ore: '광석',
  credits: '크레딧',
  knowledge: '지식',
  qic: '정보 큐브',
  power: '파워',
};

const HOME_PLANET_BY_FACTION: Record<FactionId, PlanetType> = {
  Terrans: 'Terra',
  Lantids: 'Terra',
  Xenos: 'Desert',
  Gleens: 'Desert',
  Taklons: 'Swamp',
  Ambas: 'Swamp',
  HadschHallas: 'Oxide',
  Ivits: 'Oxide',
  Geodens: 'Volcanic',
  BalTaks: 'Volcanic',
  Firaks: 'Titanium',
  Bescods: 'Titanium',
  Nevlas: 'Ice',
  Itars: 'Ice',
  Tinkeroids: 'Asteroid',
  Darkanians: 'Asteroid',
  Moweyds: 'ProtoPlanet',
  SpaceGiants: 'ProtoPlanet',
};

interface Props {
  anchor: { x: number; y: number };
  hex: Hex;
  player: PlayerState;
  players: PlayerState[];
  board: BoardState;
  powerAction?: { id: 2 | 6; freeTerraformingSteps: number };
  suppressTerraformOreConfirmation?: boolean;
  onSuppressTerraformOreConfirmation?: () => void;
  onConfirm: (action: Extract<GameAction, { type: 'Build' | 'GaiaFormation' | 'PowerAction' }>) => void;
  onClose: () => void;
}

function ringDistance(from: PlanetType, to: PlanetType): number | null {
  const fromIndex = STANDARD_PLANET_RING.indexOf(from);
  const toIndex = STANDARD_PLANET_RING.indexOf(to);
  if (fromIndex < 0 || toIndex < 0) return null;
  const direct = Math.abs(fromIndex - toIndex);
  return Math.min(direct, STANDARD_PLANET_RING.length - direct);
}

export function terraformingStepsFor(
  target: PlanetType,
  player: PlayerState,
  players: PlayerState[],
): number | null {
  if (target === 'ProtoPlanet') return 3;
  if (!STANDARD_PLANET_RING.includes(target) || !player.faction) return null;
  if (player.faction === 'Darkanians') return 1;
  if (player.faction === 'SpaceGiants') return 2;
  if (player.faction === 'Tinkeroids' || player.faction === 'Moweyds') {
    const expensive = players
      .filter(({ player_id }) => player_id !== player.player_id)
      .some(({ faction }) => faction !== null && HOME_PLANET_BY_FACTION[faction] === target);
    return expensive ? 3 : 1;
  }
  return ringDistance(HOME_PLANET_BY_FACTION[player.faction], target);
}

function buildResources(target: PlanetType, faction: FactionId | null): Partial<Record<DisplayResource, number>> {
  if (target === 'Asteroid') return {};
  if (target !== 'Gaia') return { ore: 1, credits: 2 };
  if (faction === 'Gleens') return { ore: 2, credits: 2 };
  return {
    ore: 1,
    credits: 2,
    qic: faction === 'Darkanians' || faction === 'SpaceGiants' ? 2 : 1,
  };
}

const NAVIGATION_RANGE = [1, 1, 2, 2, 3, 4] as const;
const HEX_DIRECTIONS = [
  [1, 0], [1, -1], [0, -1], [-1, 0], [-1, 1], [0, 1],
] as const;

function coordKey(coord: HexCoord): string {
  return `${coord.q},${coord.r}`;
}

export function informationCubesNeededForRange(
  board: BoardState,
  player: PlayerState,
  target: HexCoord,
): number | null {
  const starts = player.structures.map(({ hex: coord }) => coord);
  if (board.lost_planet) {
    const lostPlanet = board.hexes[coordKey(board.lost_planet)]?.planet;
    if (lostPlanet?.owner === player.player_id) starts.push(board.lost_planet);
  }
  if (starts.length === 0) return null;

  const queue = starts.map((coord) => ({ coord, distance: 0 }));
  const visited = new Set(queue.map(({ coord }) => coordKey(coord)));
  let distance: number | null = starts.some((coord) => coordKey(coord) === coordKey(target)) ? 0 : null;
  for (let index = 0; index < queue.length && distance === null; index += 1) {
    const current = queue[index];
    for (const [dq, dr] of HEX_DIRECTIONS) {
      const neighbor = { q: current.coord.q + dq, r: current.coord.r + dr };
      const key = coordKey(neighbor);
      if (!(key in board.hexes) || visited.has(key)) continue;
      const nextDistance = current.distance + 1;
      if (key === coordKey(target)) {
        distance = nextDistance;
        break;
      }
      visited.add(key);
      queue.push({ coord: neighbor, distance: nextDistance });
    }
  }
  if (distance === null) return null;

  const basicRange = NAVIGATION_RANGE[
    Math.min(player.research_tracks.navigation, NAVIGATION_RANGE.length - 1)
  ] + Number(Boolean(
    player.tech_tiles?.includes(12) && !player.covered_tech_tiles?.includes(12),
  ));
  return Math.max(0, Math.ceil((distance - basicRange) / 2));
}

export function rangeRequirementNotice(
  informationCubesNeeded: number | null,
  selectedInformationCubes: number,
): string | null {
  if (informationCubesNeeded === null) {
    return '현재 건물에서 이 행성까지의 사거리를 계산할 수 없습니다.';
  }
  if (informationCubesNeeded === 0) return null;
  if (selectedInformationCubes === 0) {
    return `사거리가 부족합니다. 정보 큐브 ${informationCubesNeeded}개가 필요합니다. 먼저 우측에서 사거리를 추가하세요.`;
  }
  if (selectedInformationCubes < informationCubesNeeded) {
    return `선택한 +${selectedInformationCubes * 2} 사거리로도 부족합니다. 정보 큐브를 ${informationCubesNeeded - selectedInformationCubes}개 더 추가하세요.`;
  }
  return null;
}

function availableGaiaformers(player: PlayerState): number {
  return Math.max(
    0,
    player.gaiaformers_total
      - player.gaiaformers_deployed
      - player.resources.spent_gaia_formers
      - (player.gaiaformers_in_gaia_area ?? 0),
  );
}

function terraformingOreCost(steps: number | null, level: number): number {
  if (steps === null) return 0;
  const orePerStep = level <= 1 ? 3 : level === 2 ? 2 : 1;
  return steps * orePerStep;
}

export function PlanetActionPopup({
  anchor,
  hex,
  player,
  players,
  board,
  powerAction,
  suppressTerraformOreConfirmation = false,
  onSuppressTerraformOreConfirmation,
  onConfirm,
  onClose,
}: Props) {
  const [confirming, setConfirming] = useState(false);
  const [confirmingTerraformOre, setConfirmingTerraformOre] = useState(false);
  const [skipTerraformOreConfirmation, setSkipTerraformOreConfirmation] = useState(false);
  const planet = hex.planet;
  if (!planet) return null;

  const target = planet.is_gaia_formed ? 'Gaia' : planet.planet_type;
  const actionType = target === 'Transdim' ? 'GaiaFormation' : 'Build';
  const actionLabel = actionType === 'GaiaFormation' ? '가이아 프로젝트 시작' : '광산 건설';
  const actionIcon = actionType === 'GaiaFormation' || target === 'Asteroid' ? 'gaiaformer' : 'mine';
  const width = 252;
  const left = Math.max(12, Math.min(anchor.x + 14, window.innerWidth - width - 12));
  const top = Math.max(56, Math.min(anchor.y - 32, window.innerHeight - 280));
  const resources = actionType === 'GaiaFormation' ? {} : buildResources(target, player.faction);
  const steps = terraformingStepsFor(target, player, players);
  const terraformingStepsUsed = actionType === 'Build' && steps !== null ? steps : 0;
  const remainingTerraformingSteps = Math.max(
    0,
    terraformingStepsUsed - (powerAction?.freeTerraformingSteps ?? 0),
  );
  const consumesPowerAction = powerAction !== undefined && terraformingStepsUsed > 0;
  const rangeQic = informationCubesNeededForRange(board, player, hex.coord);
  const displayedResources = { ...resources };
  if ((rangeQic ?? 0) > 0) displayedResources.qic = (displayedResources.qic ?? 0) + (rangeQic ?? 0);
  const terraformingOreNeeded = target === 'Gaia' || target === 'Asteroid'
    ? 0
    : terraformingOreCost(remainingTerraformingSteps, player.research_tracks.terraforming);
  const buildOreNeeded = (resources.ore ?? 0) + terraformingOreNeeded;
  const hasMinePiece = player.structures.filter(({ kind }) => kind === 'Mine').length < 8;
  const hasDisplayedResources = player.resources.ore >= buildOreNeeded
    && player.resources.credits >= (resources.credits ?? 0)
    && player.resources.qic >= (displayedResources.qic ?? 0);
  const gaiaPowerCost = [Number.POSITIVE_INFINITY, 6, 6, 4, 3, 3][
    Math.min(player.research_tracks.gaia, 5)
  ];
  const activePower = player.resources.power.bowl1
    + player.resources.power.bowl2
    + player.resources.power.bowl3
    + Number(['Area1', 'Area2', 'Area3'].includes(player.resources.power.brainstone ?? ''));
  const canConfirmGaiaFormation = player.research_tracks.gaia > 0
    && availableGaiaformers(player) > 0
    && rangeQic !== null
    && player.resources.qic >= rangeQic
    && activePower >= gaiaPowerCost;
  const canConfirmBuild = hasMinePiece
    && rangeQic !== null
    && hasDisplayedResources
    && (target !== 'Asteroid' || availableGaiaformers(player) > 0);
  const canConfirm = actionType === 'GaiaFormation' ? canConfirmGaiaFormation : canConfirmBuild;
  const confirmedAction = consumesPowerAction
    ? { type: 'PowerAction' as const, id: powerAction.id, coord: hex.coord }
    : { type: actionType, coord: hex.coord } as Extract<GameAction, { type: 'Build' | 'GaiaFormation' }>;

  function submitAction() {
    if (terraformingOreNeeded > 0 && !suppressTerraformOreConfirmation) {
      setConfirmingTerraformOre(true);
      return;
    }
    onConfirm(confirmedAction);
  }

  function confirmTerraformOreSpend() {
    if (skipTerraformOreConfirmation) onSuppressTerraformOreConfirmation?.();
    onConfirm(confirmedAction);
  }

  const costSummary = (
    <div className="planet-action-cost-summary">
      {Object.keys(displayedResources).length > 0 && (
        <ResourceTokens
          compact
          label={`필요 자원: ${Object.entries(displayedResources)
            .map(([resource, amount]) => `${RESOURCE_LABEL[resource as DisplayResource]} ${amount}`)
            .join(', ')}`}
          values={displayedResources}
        />
      )}
      {remainingTerraformingSteps > 0 && <TerraformingToken steps={remainingTerraformingSteps} />}
      {consumesPowerAction && (
        <span className="planet-action-power-terraforming">
          무료 테라포밍 {Math.min(terraformingStepsUsed, powerAction.freeTerraformingSteps)}
        </span>
      )}
      {(actionType === 'GaiaFormation' || target === 'Asteroid') && (
        <span className="planet-action-gaiaformer-cost">
          <img src={structureImageSrc('blue', 'gaiaformer')} alt="" />
          <strong>1</strong>
        </span>
      )}
    </div>
  );

  return (
    <>
      <button
        type="button"
        className="board-context-popup-scrim"
        aria-label="행동 취소"
        onClick={onClose}
      />
      <aside
        className="structure-action-popup planet-action-popup"
        style={{ left, top, width }}
        role="dialog"
        aria-label={`${actionLabel} 행동 팝업`}
      >
        {confirmingTerraformOre ? (
          <div className="terraform-ore-confirmation">
            <strong>테라포밍 광석 사용 확인</strong>
            <p>
              테라포밍 {remainingTerraformingSteps}단계에 광석 {terraformingOreNeeded}개를 추가로 사용합니다.
            </p>
            <label>
              <input
                type="checkbox"
                checked={skipTerraformOreConfirmation}
                onChange={(event) => setSkipTerraformOreConfirmation(event.target.checked)}
              />
              이 게임 동안 다시 보지 않기
            </label>
            <div className="terraform-ore-confirmation__actions">
              <button type="button" onClick={() => setConfirmingTerraformOre(false)}>돌아가기</button>
              <button type="button" className="interaction-confirm" onClick={confirmTerraformOreSpend}>
                광석 {terraformingOreNeeded}개 사용 확인
              </button>
            </div>
          </div>
        ) : !confirming ? (
          <button
            type="button"
            className="planet-rulebook-action"
            aria-label={actionLabel}
            onClick={() => setConfirming(true)}
          >
            <span className="planet-rulebook-action__primary">
              <img src={structureImageSrc('blue', actionIcon)} alt="" aria-hidden="true" />
              <strong>{actionLabel}</strong>
            </span>
            {costSummary}
          </button>
        ) : (
          <>
            <div className="interaction-selection-title interaction-selection-title--source">
              <span className="interaction-source-icon">✓</span>
              <div><small>실행할 행동</small><h3>{actionLabel}</h3></div>
            </div>
            <div className="interaction-costs interaction-costs--tokens">
              {target === 'Asteroid' ? (
                <span className="planet-special-cost">
                  <img src={structureImageSrc('blue', 'gaiaformer')} alt="" />
                  <strong>1개 영구 소모</strong>
                </span>
              ) : actionType === 'GaiaFormation' ? (
                <span className="planet-special-cost">
                  <img src={structureImageSrc('blue', 'gaiaformer')} alt="" />
                  <strong>가이아포머 1개</strong>
                  <small>필요 파워는 가이아 연구 단계 적용</small>
                </span>
              ) : (
                <>
                  <ResourceTokens
                    label={`광산 건설비: ${Object.entries(displayedResources)
                      .map(([resource, amount]) => `${RESOURCE_LABEL[resource as DisplayResource]} ${amount}`)
                      .join(', ')}`}
                    values={displayedResources}
                  />
                  {remainingTerraformingSteps > 0 && (
                    <TerraformingToken steps={remainingTerraformingSteps} />
                  )}
                  {consumesPowerAction && (
                    <span className="planet-action-power-terraforming">
                      파워 행동 무료 테라포밍 {Math.min(
                        terraformingStepsUsed,
                        powerAction.freeTerraformingSteps,
                      )}단계 적용
                    </span>
                  )}
                </>
              )}
            </div>
            <button
              type="button"
              className="interaction-confirm"
              disabled={!canConfirm}
              title={!canConfirm ? '필요 자원, 가이아포머 또는 사거리가 부족합니다.' : undefined}
              onClick={submitAction}
            >
              {canConfirm ? '행동 확정' : '필요 자원 부족'}
            </button>
          </>
        )}
      </aside>
    </>
  );
}
