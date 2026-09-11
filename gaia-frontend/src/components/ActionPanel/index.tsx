import { ADVANCED_TECH_TILE_LABELS } from '../advancedTechDescriptions';
import { ARTIFACT_LABELS } from '../artifactDescriptions';
import { ActionCrop } from '../ActionCrop';
import { useEffect, useState } from 'react';
import { clsx } from 'clsx';
import { shallow } from 'zustand/shallow';
import { useGameStore } from '../../store/gameStore';
import { hexKey } from '../GameBoard/hex-utils';
import { validateFederationSelection } from '../federationSelection';
import { roundBoosterImageSrc } from '../../assets/roundBoosterImages';
import { tinkeringTileImageSrc } from '../../assets/tinkeringTileImages';
import rangeIcon from '../../assets/icons/normalized/range.webp';
import {
  FREE_ACTIONS,
  maxFreeActionCount,
  isFreeActionAvailableToPlayer,
} from '../freeActions';
import {
  REQUIRED_SPACESHIP_BY_ACTION,
  SPACESHIP_ACTION_SLOT_BY_TYPE,
} from '../boardActionSpaces';
import type {
  FederationTokenChoice,
  FreeActionKind,
  GameAction,
  GameState,
  PlayerId,
  ResearchTrack,
  ResearchTracks,
  SpaceshipId,
  StructureType,
  TechTileChoice,
} from '../../types/game';
import { activeActionPlayerId } from '../../types/game';

interface Props {
  gameState: GameState;
  myPlayerId: PlayerId;
  /** Shows only the details for an action already selected on the board. */
  focusedAction?: boolean;
  /** Preselects an artifact clicked directly on the Twilight board. */
  initialArtifactId?: number | null;
  /** Optional board-controlled Federation token selection. */
  federationTokenChoice?: FederationTokenChoice | null;
  onFederationTokenChoice?: (choice: FederationTokenChoice | null) => void;
  hideFederationTokenChoices?: boolean;
  /** Board-driven follow-up for Federation token kind 12 (gain a Standard Tech tile). */
  federationBonusCoord?: { q: number; r: number } | null;
  onFederationBonusCoord?: (coord: { q: number; r: number } | null) => void;
  federationBonusTechTile?: number | null;
  federationBonusResearchTrack?: ResearchTrack | null;
  hideFederationTechPicker?: boolean;
  /** Optional board-controlled Federation token effect selection for Twilight's replay action. */
  replayFederationKind?: number | null;
  onReplayFederationKind?: (kind: number | null) => void;
  hideReplayFederationChoices?: boolean;
}

type ActionKind = GameAction['type'];

const ACTION_BUTTONS: { label: string; actionType: ActionKind; shortcut?: string }[] = [
  { label: '광산 건설', actionType: 'Build', shortcut: 'M' },
  { label: '연구', actionType: 'ResearchAdvance', shortcut: 'R' },
  { label: '연방 형성', actionType: 'FormFederation', shortcut: 'F' },
  { label: '공용 파워 액션', actionType: 'PowerAction', shortcut: 'P' },
  { label: '가이아 프로젝트', actionType: 'GaiaFormation', shortcut: 'G' },
  { label: '부스터 즉시 가이아포밍', actionType: 'RoundBoosterImmediateGaiaFormation' },
  { label: '부스터 +3 사거리 광산 건설', actionType: 'RoundBoosterRangeBuild' },
  { label: '부스터 +3 사거리 가이아 프로젝트', actionType: 'RoundBoosterRangeGaiaFormation' },
  { label: '부스터 +3 사거리 함선 탐사', actionType: 'RoundBoosterRangeExploreSpaceship' },
  { label: '스페이스자이언트 행성의회: 기술 타일 획득', actionType: 'SpecialAction', shortcut: 'S' },
  { label: '앰바스 행성의회 ↔ 광산 교환', actionType: 'AmbasSwapPlanetaryInstitute' },
  { label: '파이락 연구소 강등 + 무료 연구', actionType: 'FiraksDowngradeResearchLab' },
  { label: '매드 안드로이드 최저 연구 무료 상승', actionType: 'BescodsLowestResearchAdvance' },
  { label: '하이브 우주 정거장 건설', actionType: 'IvitsPlaceSpaceStation' },
  { label: '팅커로이드 팅커링 타일 사용', actionType: 'TinkeroidsUseTile' },
  { label: '모웨이드 파워 링 설치', actionType: 'MoweydsPlacePowerRing' },
  { label: '함선 탐사', actionType: 'ExploreSpaceship', shortcut: 'X' },
  { label: '아티팩트 조사', actionType: 'ExamineArtifact', shortcut: 'A' },
  { label: '함선 크레딧 액션 (테라포밍 1단계 무료)', actionType: 'SpaceshipCreditTerraform' },
  { label: '트와일라잇 무료 업그레이드 (교역소→연구소)', actionType: 'TwilightFreeResearchLab' },
  { label: '트와일라잇 연방 토큰 효과 재사용 (정보 큐브 3)', actionType: 'TwilightReplayFederationToken' },
  { label: '트와일라잇 +3 사거리 광산 건설 (지식 1)', actionType: 'TwilightRangeBuild' },
  { label: '트와일라잇 +3 사거리 가이아 프로젝트 (지식 1)', actionType: 'TwilightRangeGaiaFormation' },
  { label: '트와일라잇 +3 사거리 함선 탐사 (지식 1)', actionType: 'TwilightRangeExploreSpaceship' },
  { label: '리벨리온 무료 업그레이드 (광산→교역소)', actionType: 'RebellionFreeTradingStation' },
  { label: '리벨리온 지식 액션 (지식 2 → 크레딧 2 + 정보 큐브 1)', actionType: 'RebellionCreditsAndQic' },
  { label: '리벨리온 표준 기술 타일 획득 (정보 큐브 3)', actionType: 'RebellionGainTechTile' },
  { label: 'T F 마스 정보 큐브 액션 (정보 큐브 2 → 2 + 기술 타일당 1점)', actionType: 'TFMarsTechBonus' },
  { label: 'T F 마스 즉시 가이아포밍 (파워 2)', actionType: 'TFMarsGaiaFormation' },
  { label: '이클립스 정보 큐브 액션 (정보 큐브 2 → 2 + 행성 종류당 1점)', actionType: 'EclipsePlanetTypeBonus' },
  { label: '이클립스 연구 부스트 (파워 3 + 지식 2)', actionType: 'EclipseResearchBoost' },
  { label: '이클립스 소행성 광산 (크레딧 6)', actionType: 'EclipseAsteroidMine' },
  { label: '글린 특수 능력: 광산 건설 (+2 사거리)', actionType: 'GleensBuildMine' },
  { label: '글린 특수 능력: 가이아 프로젝트 (+2 사거리)', actionType: 'GleensGaiaFormation' },
  { label: '글린 특수 능력: 함선 탐사 (+2 사거리)', actionType: 'GleensExploreSpaceship' },
  { label: '스페이스자이언트 특수 능력: 광산 건설 (테라포밍 2단계 무료)', actionType: 'SpaceGiantsBuildMine' },
];

const PRIMARY_ACTION_TYPES = new Set<ActionKind>([
  'Build',
  'ResearchAdvance',
  'FormFederation',
  'PowerAction',
  'GaiaFormation',
]);

// Lost Fleet Exploration Board special action (`GP_Exp_Rule_EN_V1_Web.pdf` p.10): the Gleens'
// three action modes share one once-per-round flag (`PlayerState.gleens_special_action_used_this_round`),
// distinct from `GameState.used_spaceship_actions`'s shared numeric-slot pool used by every
// spaceship-tied action above.
const GLEENS_SPECIAL_ACTION_TYPES: ActionKind[] = [
  'GleensBuildMine',
  'GleensGaiaFormation',
  'GleensExploreSpaceship',
];

const REQUIRED_FACTION_BY_ACTION: Partial<
  Record<ActionKind, GameState['players'][number]['faction']>
> = {
  AmbasSwapPlanetaryInstitute: 'Ambas',
  FiraksDowngradeResearchLab: 'Firaks',
  BescodsLowestResearchAdvance: 'Bescods',
  IvitsPlaceSpaceStation: 'Ivits',
  TinkeroidsUseTile: 'Tinkeroids',
  MoweydsPlacePowerRing: 'Moweyds',
};

// Tinkeroids Tinkering tiles (`GameAction::TinkeroidsUseTile`) — ids 1-3 usable only in rounds
// 1-3, 4-6 only in rounds 4-6; each usable at most once per game. Tiles 1 and 5 build a mine
// with free terraforming steps and need a board hex; the rest are flat resource gains.
const TINKEROIDS_TILE_LABELS: Record<number, string> = {
  1: '광산 건설 (테라포밍 1단계 무료)',
  2: '정보 큐브 1 획득',
  3: '파워 4 충전',
  4: '정보 큐브 2 획득',
  5: '광산 건설 (테라포밍 3단계 무료)',
  6: '지식 3 획득',
};

// Tech tiles (`GameAction::Upgrade`'s `tech_tile_choice` and `GameAction::TechTileSpecialAction`)
// — ids match `rules::engine`'s `tech_tile_*`/`advanced_tech_tile_*` match tables. Standard ids
// 2-10 are the base game's 9 tiles; 11-13 are the Lost Fleet spaceship tile additions.
// Advanced ids are 1-22, minus 18 (no scan exists for it).
const TRACK_ORDER: ResearchTrack[] = [
  'Terraforming',
  'Navigation',
  'ArtificialIntelligence',
  'GaiaProject',
  'Economy',
  'Science',
];

const TECH_TILE_LABELS: Record<number, string> = {
  2: '수입: 광석 1 + 파워 충전 1',
  3: '수입: 크레딧 4',
  4: '즉시: 광석 1 + 정보 큐브 1',
  5: '수입: 지식 1 + 크레딧 1',
  6: '행성의회/아카데미 파워 가치 +1',
  7: '즉시: 7점',
  8: '가이아 행성에 광산 건설 시 +3점',
  9: '즉시: 행성 종류당 지식 1',
  10: '특수 능력: 파워 4 충전',
  11: '즉시: 광산 비용 및 테라포밍 2단계 무료',
  12: '기본 사거리 +1',
  13: '즉시: 광석 1 + 지식 3',
};

const TECH_TILE_SPECIAL_ACTION_IDS = new Set([10]);
const ADVANCED_TECH_TILE_SPECIAL_ACTION_IDS = new Set([20, 21, 22]);

function tinkeroidsTileNeedsCoord(tile: number): boolean {
  return tile === 1 || tile === 5;
}

function tinkeroidsAvailableTiles(
  round: number,
  tilesUsed: number[] | undefined,
): number[] {
  const candidates = round <= 3 ? [1, 2, 3] : [4, 5, 6];
  return candidates.filter((tile) => !tilesUsed?.includes(tile));
}

const REQUIRED_ROUND_BOOSTER_BY_ACTION: Partial<Record<ActionKind, number>> = {
  RoundBoosterImmediateGaiaFormation: 5,
  RoundBoosterRangeBuild: 8,
  RoundBoosterRangeGaiaFormation: 8,
  RoundBoosterRangeExploreSpaceship: 8,
};

const TERRANS_GAIA_CONVERSIONS: {
  kind: Extract<FreeActionKind, 'PowerToQic' | 'PowerToOre' | 'PowerToKnowledge' | 'PowerToCredit'>;
  cost: number;
  label: string;
}[] = [
  { kind: 'PowerToQic', cost: 4, label: '가이아 파워 4 → 정보 큐브 1' },
  { kind: 'PowerToOre', cost: 3, label: '가이아 파워 3 → 광석 1' },
  { kind: 'PowerToKnowledge', cost: 4, label: '가이아 파워 4 → 지식 1' },
  { kind: 'PowerToCredit', cost: 1, label: '가이아 파워 1 → 크레딧 1' },
];

// Lost Fleet expansion — the 4 spaceship boards (docs/GP_Exp_Rule_EN_V1_Web.pdf,
// "Lost Fleet Spaceships").
const SPACESHIPS: { id: SpaceshipId; label: string }[] = [
  { id: 'Twilight', label: '트와일라잇' },
  { id: 'Rebellion', label: '리벨리온' },
  { id: 'TFMars', label: 'T F 마스' },
  { id: 'Eclipse', label: '이클립스' },
];

// Federation token kinds (base rulebook p.2 components + Lost Fleet's 8 spaceship-tied tokens,
// confirmed against the physical components by the user — each of the 8 is a distinct token, not
// 2 copies of 4 kinds) — matches `federation_token_kind` in `gaia-engine/src/rules/engine.rs`.
// Ids 14 and 15 grant a follow-up free Build a Mine (needs `bonus_build_coord`); id 12 grants a
// Standard Tech tile of choice (needs `bonus_tech_tile`).
const FEDERATION_TOKEN_LABELS: Record<number, string> = {
  1: '12점',
  2: '8점 + 정보 큐브 1',
  3: '8점 + 파워 2',
  4: '7점 + 광석 2',
  5: '7점 + 크레딧 6',
  6: '6점 + 지식 2',
  7: '광석 1 + 지식 1 + 크레딧 2',
  8: '[함선] 8점 + 크레딧 8',
  9: '[함선] 12점',
  10: '[함선] 4점 + 지식 4',
  11: '[함선] 4점 + 광석 2 + 정보 큐브 1',
  12: '[함선] 기술 타일 1개 선택',
  13: '[함선] 7점 + 파워 2 (Area III 신규)',
  14: '[함선] 자유 테라포밍 3단계 무료 광산 건설',
  15: '[함선] 무제한 사거리 무료 광산 건설',
  16: '[글린] 광석 1 + 지식 1 + 크레딧 2',
};

// Lost Fleet Artifacts (expansion Appendix VII) — matches `artifact_effect` in
// `gaia-engine/src/rules/engine.rs`. Id 10 needs `copy_federation_token_kind` (and, depending on
// the copied token's own kind, the same `bonus_*` follow-up fields `TwilightReplayFederationToken`
// uses).


const TRACK_LABELS: Record<ResearchTrack, string> = {
  Terraforming: '테라포밍',
  Navigation: '항법',
  ArtificialIntelligence: '인공지능',
  GaiaProject: '가이아 프로젝트',
  Economy: '경제',
  Science: '과학',
};

function researchTrackLevel(tracks: ResearchTracks, track: ResearchTrack): number {
  switch (track) {
    case 'Terraforming':
      return tracks.terraforming;
    case 'Navigation':
      return tracks.navigation;
    case 'ArtificialIntelligence':
      return tracks.ai;
    case 'GaiaProject':
      return tracks.gaia;
    case 'Economy':
      return tracks.economy;
    case 'Science':
      return tracks.science;
  }
}

const UPGRADE_TARGETS: { label: string; to: StructureType }[] = [
  { label: '교역소', to: 'TradingStation' },
  { label: '연구소', to: 'ResearchLab' },
  { label: '행성의회', to: 'PlanetaryInstitute' },
  { label: '아카데미(과학)', to: { Academy: 'Science' } },
  { label: '아카데미(정보 큐브)', to: { Academy: 'Qic' } },
];

// Rulebook p.15 free-action conversions — unlike every other action here,
// these don't consume the turn, so the panel renders them as a persistent
// list (always visible on the player's turn) rather than a selectable
// action that needs a confirm step. Shared with SidebarTurnControls via
// '../freeActions' so the two panels can't drift apart on cost/faction logic.

// Rulebook Appendix III power-action board slots 1-7 (confirmed against
// gaia-frontend/src/assets/boards/research_board.jpg — the rulebook prose
// doesn't print these). Ids 2 and 6 immediately perform a "build a mine"
// action with free terraforming steps instead of a plain resource gain, so
// they need a target hex like Build/Upgrade/GaiaFormation do.
const POWER_ACTIONS: { id: number; label: string; needsCoord: boolean }[] = [
  { id: 1, label: '파워 7 → 지식 3', needsCoord: false },
  { id: 2, label: '파워 5 → 광산 건설 (테라포밍 2단계 무료)', needsCoord: true },
  { id: 3, label: '파워 4 → 광석 2', needsCoord: false },
  { id: 4, label: '파워 4 → 크레딧 7', needsCoord: false },
  { id: 5, label: '파워 4 → 지식 2', needsCoord: false },
  { id: 6, label: '파워 3 → 광산 건설 (테라포밍 1단계 무료)', needsCoord: true },
  { id: 7, label: '파워 3 → 파워토큰 2개 (1단계)', needsCoord: false },
];

function hasAcademyQic(gameState: GameState, myPlayerId: PlayerId): boolean {
  const player = gameState.players.find((p) => p.player_id === myPlayerId);
  return (
    player?.structures.some(
      (s) => typeof s.kind === 'object' && 'Academy' in s.kind && s.kind.Academy === 'Qic',
    ) ?? false
  );
}

function academyQicActionUsedThisRound(gameState: GameState, myPlayerId: PlayerId): boolean {
  return (
    gameState.players.find((p) => p.player_id === myPlayerId)
      ?.academy_qic_action_used_this_round ?? false
  );
}

/** Resolves a `FederationTokenChoice` to the kind id it refers to (see `federation_token_kind`
 * in `rules/engine.rs`), or `null` if it doesn't currently resolve (e.g. the ship's token was
 * already claimed). */
function resolveFederationTokenKind(
  gameState: GameState,
  choice: FederationTokenChoice | null,
): number | null {
  if (!choice) return null;
  if (choice.source === 'Supply') return choice.kind;
  const board = gameState.spaceship_boards.find((b) => b.id === choice.ship);
  return board?.federation_token ?? null;
}

/** Ships the player has explored and whose own Federation token hasn't been claimed yet. */
function availableSpaceshipFederationTokens(
  gameState: GameState,
  myPlayerId: PlayerId,
): { ship: SpaceshipId; kind: number }[] {
  const player = gameState.players.find((p) => p.player_id === myPlayerId);
  if (!player) return [];
  const exploredShipIndexes = new Set(player.explored_ships ?? []);
  const shipIndex: Record<SpaceshipId, number> = {
    Twilight: 0,
    Rebellion: 1,
    TFMars: 2,
    Eclipse: 3,
  };
  return gameState.spaceship_boards
    .filter((b) =>
      (b.explorers.includes(myPlayerId) || exploredShipIndexes.has(shipIndex[b.id]))
      && b.federation_token !== null,
    )
    .map((b) => ({ ship: b.id, kind: b.federation_token as number }));
}

export function ActionPanel({
  gameState,
  myPlayerId,
  focusedAction = false,
  initialArtifactId = null,
  federationTokenChoice,
  onFederationTokenChoice,
  hideFederationTokenChoices = false,
  federationBonusCoord: controlledFederationBonusCoord,
  onFederationBonusCoord,
  federationBonusTechTile: controlledFederationBonusTechTile,
  federationBonusResearchTrack: controlledFederationBonusResearchTrack,
  hideFederationTechPicker = false,
  replayFederationKind: controlledReplayFederationKind,
  onReplayFederationKind,
  hideReplayFederationChoices = false,
}: Props) {
  const { selectedAction, selectedPowerActionId, activePlanet, selectedHexes, actions } = useGameStore(
    (s) => ({
      selectedAction: s.selectedAction,
      selectedPowerActionId: s.selectedPowerActionId,
      activePlanet: s.activePlanet,
      selectedHexes: s.selectedHexes,
      actions: s.actions,
    }),
    shallow,
  );

  const [upgradeTarget, setUpgradeTarget] = useState<StructureType | null>(null);
  const [passBoosterId, setPassBoosterId] = useState<number | null>(null);
  const [spaceshipId, setSpaceshipId] = useState<SpaceshipId | null>(null);
  const [localReplayFederationKind, setLocalReplayFederationKind] = useState<number | null>(null);
  const replayFederationKind = controlledReplayFederationKind === undefined
    ? localReplayFederationKind
    : controlledReplayFederationKind;
  const setReplayFederationKind = onReplayFederationKind ?? setLocalReplayFederationKind;
  const [examineArtifactId, setExamineArtifactId] = useState<number | null>(initialArtifactId);
  const [selectedResearchTrack, setSelectedResearchTrack] = useState<ResearchTrack | null>(null);
  const [localFederationToken, setLocalFederationToken] = useState<FederationTokenChoice | null>(null);
  const federationToken = federationTokenChoice === undefined
    ? localFederationToken
    : federationTokenChoice;
  const setFederationToken = onFederationTokenChoice ?? setLocalFederationToken;
  const [federationBonusCoord, setFederationBonusCoord] = useState<{ q: number; r: number } | null>(
    null,
  );
  const [federationBonusTechTile, setFederationBonusTechTile] = useState<number | null>(null);
  const resolvedFederationBonusCoord = controlledFederationBonusCoord === undefined
    ? federationBonusCoord
    : controlledFederationBonusCoord;
  const resolvedFederationBonusTechTile = controlledFederationBonusTechTile === undefined
    ? federationBonusTechTile
    : controlledFederationBonusTechTile;
  const resolvedFederationBonusResearchTrack = controlledFederationBonusResearchTrack === undefined
    ? selectedResearchTrack
    : controlledFederationBonusResearchTrack;
  const updateFederationBonusCoord = onFederationBonusCoord ?? setFederationBonusCoord;
  const [upgradeTechTile, setUpgradeTechTile] = useState<
    | { kind: 'Standard'; tile: number }
    | { kind: 'Advanced'; track: ResearchTrack }
    | { kind: 'LostFleetAdvanced' }
    | null
  >(null);
  const [upgradeAdvanceTrack, setUpgradeAdvanceTrack] = useState<ResearchTrack | null>(null);
  const [upgradeBonusCoord, setUpgradeBonusCoord] = useState<{ q: number; r: number } | null>(
    null,
  );
  const [upgradeCoveredTile, setUpgradeCoveredTile] = useState<number | null>(null);
  const [freeActionCounts, setFreeActionCounts] = useState<
    Partial<Record<FreeActionKind, number>>
  >({});
  const currentPlayer = gameState.players.find((player) => player.player_id === myPlayerId);
  const ownedFederationKinds = Array.from(new Set([
    ...(currentPlayer?.federation_tokens ?? []),
    ...(currentPlayer?.gray_federation_tokens ?? []),
  ]));
  const greenFederationTokenCount = currentPlayer?.federation_tokens.length ?? 0;
  const uncoveredStandardTechTiles = (currentPlayer?.tech_tiles ?? []).filter(
    (tile) => !(currentPlayer?.covered_tech_tiles ?? []).includes(tile),
  );
  const hasSpaceGiantsPi =
    currentPlayer?.faction === 'SpaceGiants' &&
    currentPlayer.structures.some((structure) => structure.kind === 'PlanetaryInstitute');
  const exploredShipIndexes = new Set(currentPlayer?.explored_ships ?? []);
  const shipIndex: Record<SpaceshipId, number> = {
    Twilight: 0,
    Rebellion: 1,
    TFMars: 2,
    Eclipse: 3,
  };
  const availableStandardTechTiles = Array.from(new Set([
    ...gameState.research_board.tech_tiles,
    ...gameState.spaceship_boards.flatMap((board) =>
      exploredShipIndexes.has(shipIndex[board.id]) ? (board.tech_tiles ?? []) : [],
    ),
  ]));
  const hasUnownedStandardTechTile = availableStandardTechTiles.some(
    (tile) => !(currentPlayer?.tech_tiles ?? []).includes(tile),
  );
  const requiresBoosterChoice = gameState.round < 6 && currentPlayer?.booster != null;

  function renderTechTilePicker(allowSkip: boolean) {
    if (!currentPlayer) return null;
    return (
        <>
          <h4 className="action-panel-subtitle">
            기술 타일 선택 {allowSkip ? '(선택사항)' : '(필수)'}
          </h4>
          <div className="action-buttons">
            {allowSkip && (
              <button
                className={clsx('btn action-btn', upgradeTechTile === null && 'action-btn--selected')}
                onClick={() => setUpgradeTechTile(null)}
              >
                타일 선택 안 함
              </button>
            )}
            {availableStandardTechTiles
              .filter((tile) => !currentPlayer.tech_tiles?.includes(tile))
              .map((tile) => (
                <button
                  key={`std-${tile}`}
                  className={clsx(
                    'btn action-btn',
                    upgradeTechTile?.kind === 'Standard' &&
                      upgradeTechTile.tile === tile &&
                      'action-btn--selected',
                  )}
                  onClick={() => setUpgradeTechTile({ kind: 'Standard', tile })}
                >
                  {TECH_TILE_LABELS[tile] ?? `표준 타일 ${tile}`}
                </button>
              ))}
            {TRACK_ORDER.filter((track, index) => {
              const tileId = gameState.research_board.advanced_tech_tiles[index];
              return greenFederationTokenCount > 0
                && uncoveredStandardTechTiles.length > 0
                && tileId !== null
                && researchTrackLevel(currentPlayer.research_tracks, track) >= 4;
            }).map((track) => {
              const tileId = gameState.research_board.advanced_tech_tiles[TRACK_ORDER.indexOf(track)];
              return (
                <button
                  key={`adv-${track}`}
                  className={clsx(
                    'btn action-btn',
                    upgradeTechTile?.kind === 'Advanced' &&
                      upgradeTechTile.track === track &&
                      'action-btn--selected',
                  )}
                  onClick={() => setUpgradeTechTile({ kind: 'Advanced', track })}
                >
                  [{TRACK_LABELS[track]}]{' '}
                  {tileId !== null ? (ADVANCED_TECH_TILE_LABELS[tileId] ?? `고급 타일 ${tileId}`) : ''}
                </button>
              );
            })}
            {gameState.research_board.lost_fleet_advanced_tech_tile != null &&
              greenFederationTokenCount > 0 &&
              uncoveredStandardTechTiles.length > 0 &&
              (gameState.research_board.lost_fleet_advanced_tech_requirement === '25-vp'
                ? currentPlayer.vp >= 25
                : new Set(currentPlayer.explored_ships).size >= 3) && (
                <button
                  className={clsx(
                    'btn action-btn',
                    upgradeTechTile?.kind === 'LostFleetAdvanced' && 'action-btn--selected',
                  )}
                  onClick={() => setUpgradeTechTile({ kind: 'LostFleetAdvanced' })}
                >
                  종료 목표 보드 고급 타일{' '}
                  {ADVANCED_TECH_TILE_LABELS[
                    gameState.research_board.lost_fleet_advanced_tech_tile
                  ] ?? `#${gameState.research_board.lost_fleet_advanced_tech_tile}`}
                </button>
              )}
          </div>
          {(upgradeTechTile?.kind === 'Advanced' ||
            upgradeTechTile?.kind === 'LostFleetAdvanced') && currentPlayer && (
            <>
              <h4 className="action-panel-subtitle">
                덮을 표준 타일 선택 (필수 — 고급 타일이 그 위에 놓입니다)
              </h4>
              <div className="action-buttons">
                {(currentPlayer.tech_tiles ?? [])
                  .filter((tile) => !(currentPlayer.covered_tech_tiles ?? []).includes(tile))
                  .map((tile) => (
                    <button
                      key={`cover-${tile}`}
                      className={clsx(
                        'btn action-btn',
                        upgradeCoveredTile === tile && 'action-btn--selected',
                      )}
                      onClick={() => setUpgradeCoveredTile(tile)}
                    >
                      {TECH_TILE_LABELS[tile] ?? `표준 타일 ${tile}`}
                    </button>
                  ))}
              </div>
            </>
          )}
          {upgradeTechTile && (
            <>
              <h4 className="action-panel-subtitle">연구 트랙 상승 (선택사항)</h4>
              <div className="action-buttons">
                <button
                  className={clsx(
                    'btn action-btn',
                    upgradeAdvanceTrack === null && 'action-btn--selected',
                  )}
                  onClick={() => setUpgradeAdvanceTrack(null)}
                >
                  상승 안 함
                </button>
                {(Object.keys(TRACK_LABELS) as ResearchTrack[]).map((track) => {
                  const selectable = canAdvanceFromTechTile(
                    track,
                    upgradeTechTile.kind === 'Advanced'
                      || upgradeTechTile.kind === 'LostFleetAdvanced',
                  );
                  return (
                    <button
                      key={track}
                      className={clsx(
                        'btn action-btn',
                        upgradeAdvanceTrack === track && 'action-btn--selected',
                      )}
                      disabled={!selectable}
                      onClick={() => setUpgradeAdvanceTrack(track)}
                    >
                      {TRACK_LABELS[track]}
                    </button>
                  );
                })}
              </div>
            </>
          )}
          {upgradeTechTile?.kind === 'Standard' && upgradeTechTile.tile === 11 && (
            <div className="federation-bonus-coord">
              <label>
                무료 광산 좌표 q
                <input
                  type="number"
                  aria-label="무료 광산 좌표 q"
                  value={upgradeBonusCoord?.q ?? ''}
                  onChange={(e) =>
                    setUpgradeBonusCoord({
                      q: Number(e.target.value),
                      r: upgradeBonusCoord?.r ?? 0,
                    })
                  }
                />
              </label>
              <label>
                r
                <input
                  type="number"
                  aria-label="무료 광산 좌표 r"
                  value={upgradeBonusCoord?.r ?? ''}
                  onChange={(e) =>
                    setUpgradeBonusCoord({
                      q: upgradeBonusCoord?.q ?? 0,
                      r: Number(e.target.value),
                    })
                  }
                />
              </label>
            </div>
          )}
        </>
    );
  }

  function canAdvanceFromTechTile(track: ResearchTrack, advancedTile: boolean) {
    if (!currentPlayer) return false;
    const level = researchTrackLevel(currentPlayer.research_tracks, track);
    if (level >= 5) return false;
    if (
      currentPlayer.faction === 'BalTaks'
      && track === 'Navigation'
      && !currentPlayer.structures.some(({ kind }) => kind === 'PlanetaryInstitute')
    ) return false;
    if (level < 4) return true;
    const requiredGreenTokens = advancedTile ? 2 : 1;
    return greenFederationTokenCount >= requiredGreenTokens
      && !gameState.players.some(
        (player) => player.player_id !== myPlayerId
          && researchTrackLevel(player.research_tracks, track) >= 5,
      );
  }

  useEffect(() => {
    setUpgradeTarget(null);
    setSpaceshipId(null);
    setReplayFederationKind(null);
    setExamineArtifactId(selectedAction === 'ExamineArtifact' ? initialArtifactId : null);
    setSelectedResearchTrack(null);
    setLocalFederationToken(null);
    setFederationBonusCoord(null);
    setFederationBonusTechTile(null);
    setUpgradeTechTile(null);
    setUpgradeAdvanceTrack(null);
    setUpgradeBonusCoord(null);
    setUpgradeCoveredTile(null);
  }, [initialArtifactId, selectedAction]);

  useEffect(() => {
    setFederationBonusTechTile(null);
    setSelectedResearchTrack(null);
  }, [replayFederationKind]);

  const federationSelectionKey = selectedHexes
    .map(({ q, r }) => hexKey(q, r))
    .sort()
    .join('|');
  useEffect(() => {
    if (selectedAction !== 'FormFederation') return;
    setLocalFederationToken(null);
    setFederationBonusCoord(null);
    setFederationBonusTechTile(null);
    setSelectedResearchTrack(null);
  }, [federationSelectionKey, selectedAction]);

  const phase = gameState.phase;
  const selectedTinkeringTile = currentPlayer?.tinkeroids_selected_tile ?? null;
  const federationSelection = validateFederationSelection(gameState, myPlayerId, selectedHexes);
  const federationSatelliteHexKeys = new Set(
    federationSelection.satelliteHexes.map((coord) => hexKey(coord.q, coord.r)),
  );

  // ── Passive-action phase pauses take over the whole panel ────────────────

  if (typeof phase === 'object' && 'TinkeroidsTileSelectionPending' in phase) {
    const { player, round } = phase.TinkeroidsTileSelectionPending;
    if (player !== myPlayerId) {
      const name = gameState.players.find((candidate) => candidate.player_id === player)?.nickname ?? '상대';
      return <WaitingPanel text={`${name}님이 팅커링 타일을 선택 중입니다...`} />;
    }
    return (
      <div className="action-panel">
        <h3 className="action-panel-title">라운드 {round} · 팅커링 타일 선택</h3>
        <p className="action-hint">
          이번 라운드에 사용할 타일 하나를 선택하세요. 사용하지 않아도 라운드 종료 시 제거됩니다.
        </p>
        <div className="action-buttons">
          {tinkeroidsAvailableTiles(round, currentPlayer?.tinkeroids_tiles_used).map((tile) => (
            <button
              key={tile}
              className="btn action-btn tinkering-tile-btn"
              onClick={() => actions.sendAction({ type: 'SelectTinkeringTile', tile })}
            >
              <img
                className="tinkering-tile-image"
                src={tinkeringTileImageSrc(tile)}
                alt={`팅커링 타일 ${tile}`}
              />
              <span>{TINKEROIDS_TILE_LABELS[tile]}</span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (typeof phase === 'object' && 'LostPlanetPlacementPending' in phase) {
    const pendingPlayer = phase.LostPlanetPlacementPending.player;
    if (pendingPlayer !== myPlayerId) {
      const name = gameState.players.find((p) => p.player_id === pendingPlayer)?.nickname ?? '상대';
      return <WaitingPanel text={`${name}님이 검은 행성 위치를 선택 중입니다...`} />;
    }
    return (
      <div className="action-panel">
        <h3 className="action-panel-title">항해술 5단계 — 검은 행성</h3>
        <p className="action-hint">
          맵에서 비어 있는 칸을 선택하세요. 기본 사거리는 4이며 부족한 사거리는 필요한 만큼의
          정보 큐브가 자동 사용됩니다. 배치된 검은 행성은 광산과 새로운 행성 종류로 계산됩니다.
        </p>
        {activePlanet && (
          <p className="action-hint">
            선택 좌표: ({activePlanet.q}, {activePlanet.r})
          </p>
        )}
        <button
          className="btn btn-primary confirm-btn"
          disabled={!activePlanet}
          onClick={() => {
            if (activePlanet) actions.sendAction({ type: 'PlaceLostPlanet', coord: activePlanet });
          }}
        >
          이 위치에 검은 행성 배치
        </button>
      </div>
    );
  }

  const chargeQueue =
    typeof phase === 'object' && 'ChargePowerPending' in phase
      ? phase.ChargePowerPending.queue
      : typeof phase === 'object' && 'LostPlanetChargePowerPending' in phase
        ? phase.LostPlanetChargePowerPending.queue
        : null;
  if (chargeQueue) {
    const entry = chargeQueue[0];
    if (!entry) return <WaitingPanel text="파워 충전 대기열 처리 중..." />;
    if (entry.player !== myPlayerId) {
      const name = gameState.players.find((p) => p.player_id === entry.player)?.nickname ?? '상대';
      return <WaitingPanel text={`${name}님이 파워 충전 여부를 결정 중입니다...`} />;
    }
    const hasTaklonsPi =
      currentPlayer?.faction === 'Taklons' &&
      currentPlayer.structures.some((structure) => structure.kind === 'PlanetaryInstitute');
    return (
      <div className="action-panel">
        <h3 className="action-panel-title">파워 충전</h3>
        <p className="action-hint">
          최대 {entry.max_power}까지 충전할 수 있습니다 (승점 {entry.max_power - 1}점 소모). 충전하시겠습니까?
        </p>
        {hasTaklonsPi ? (
          <>
            <button
              className="btn btn-primary confirm-btn"
              onClick={() =>
                actions.sendAction({ type: 'TaklonsChargePower', gain_before: true })
              }
            >
              파워 토큰을 먼저 받고 충전
            </button>
            <button
              className="btn btn-secondary confirm-btn"
              onClick={() =>
                actions.sendAction({ type: 'TaklonsChargePower', gain_before: false })
              }
            >
              충전 후 파워 토큰 받기
            </button>
          </>
        ) : (
          <button
            className="btn btn-primary confirm-btn"
            onClick={() => actions.sendAction({ type: 'ChargePower', accept: true })}
          >
            충전 ({entry.max_power})
          </button>
        )}
        <button
          className="btn btn-ghost pass-btn"
          onClick={() => actions.sendAction({ type: 'ChargePower', accept: false })}
        >
          거절
        </button>
      </div>
    );
  }

  if (typeof phase === 'object' && 'IncomeOrderPending' in phase) {
    const entry = phase.IncomeOrderPending.queue[0];
    if (!entry) return <WaitingPanel text="수입 순서 결정 대기열 처리 중..." />;
    if (entry.player !== myPlayerId) {
      const name = gameState.players.find((p) => p.player_id === entry.player)?.nickname ?? '상대';
      return <WaitingPanel text={`${name}님이 수입 순서를 결정 중입니다...`} />;
    }
    return (
      <div className="action-panel">
        <h3 className="action-panel-title">행성의회 수입 순서</h3>
        <p className="action-hint">
          파워 {entry.charge_amount} 충전과 보너스 파워토큰 {entry.bonus_tokens}개 중 무엇을 먼저
          받으시겠습니까? (충전을 먼저 받으면 새 토큰이 충전에 함께 휩쓸려 2단계로 갈 수 있습니다)
        </p>
        <button
          className="btn btn-primary confirm-btn"
          onClick={() => actions.sendAction({ type: 'ChooseIncomeOrder', charge_first: true })}
        >
          충전 먼저
        </button>
        <button
          className="btn btn-secondary confirm-btn"
          onClick={() => actions.sendAction({ type: 'ChooseIncomeOrder', charge_first: false })}
        >
          토큰 먼저
        </button>
      </div>
    );
  }

  if (typeof phase === 'object' && 'GaiaDecisionPending' in phase) {
    const entry = phase.GaiaDecisionPending.queue[0];
    if (!entry) return <WaitingPanel text="가이아 단계 선택 대기열 처리 중..." />;
    if (entry.player !== myPlayerId) {
      const name = gameState.players.find((p) => p.player_id === entry.player)?.nickname ?? '상대';
      return <WaitingPanel text={`${name}님이 가이아 단계 능력을 처리 중입니다...`} />;
    }

    const gaiaPower = entry.remaining_power;
    if (entry.kind === 'TerransPowerConversion') {
      return (
        <div className="action-panel">
          <h3 className="action-panel-title">테란 행성의회 — 가이아 파워 교환</h3>
          <p className="action-hint">
            가이아 구역 파워 {gaiaPower}개를 자유행동 비율로 자원과 교환할 수 있습니다.
            남은 파워는 완료 시 2구역으로 이동합니다.
          </p>
          <div className="action-buttons">
            {TERRANS_GAIA_CONVERSIONS.map(({ kind, cost, label }) => (
              <button
                key={kind}
                className="btn action-btn"
                disabled={gaiaPower < cost}
                onClick={() =>
                  actions.sendAction({ type: 'TerransGaiaConversion', kind, count: 1 })
                }
              >
                {label}
              </button>
            ))}
          </div>
          <button
            className="btn btn-primary confirm-btn"
            onClick={() => actions.sendAction({ type: 'FinishGaiaDecision' })}
          >
            가이아 단계 완료
          </button>
        </div>
      );
    }

    return (
      <div className="action-panel">
        <h3 className="action-panel-title">이타르 행성의회 — 기술 타일 획득</h3>
        <p className="action-hint">
          가이아 구역 파워 {gaiaPower}개 중 4개를 버리고 일반 또는 고급 기술 타일을 획득할 수 있습니다.
          감당할 수 있는 동안 반복 가능합니다.
        </p>
        {renderTechTilePicker(false)}
        <button
          className="btn btn-secondary confirm-btn"
          disabled={gaiaPower < 4 || !upgradeTechTile
            || (upgradeTechTile.kind !== 'Standard' && upgradeCoveredTile === null)
            || (upgradeTechTile.kind === 'Standard' && upgradeTechTile.tile === 11 && !upgradeBonusCoord)
            || (upgradeAdvanceTrack !== null && !canAdvanceFromTechTile(upgradeAdvanceTrack, upgradeTechTile.kind !== 'Standard'))}
          onClick={() => {
            const choice = selectedTechTileChoice();
            if (choice) actions.sendAction({ type: 'ItarsGaiaTechChoice', choice });
          }}
        >
          파워 4로 기술 타일 획득
        </button>
        <button
          className="btn btn-primary confirm-btn"
          onClick={() => actions.sendAction({ type: 'FinishGaiaDecision' })}
        >
          가이아 단계 완료
        </button>
      </div>
    );
  }

  const activePlayerId = activeActionPlayerId(gameState);
  const isMyTurn = activePlayerId === myPlayerId;

  if (!isMyTurn) {
    const activeName =
      activePlayerId !== null
        ? (gameState.players.find((player) => player.player_id === activePlayerId)?.nickname ??
          `Player ${activePlayerId}`)
        : '?';
    return <WaitingPanel text={`${activeName}의 턴입니다...`} />;
  }

  function handleActionSelect(actionType: ActionKind) {
    actions.selectAction(actionType === selectedAction ? null : actionType);
  }

  function handlePass() {
    actions.sendAction({ type: 'Pass', booster_id: passBoosterId });
  }

  function handleAcademyQicAction() {
    actions.sendAction({ type: 'AcademyQicAction' });
  }

  function handleFreeAction(kind: FreeActionKind, count: number) {
    actions.sendAction({ type: 'FreeAction', kind, count });
  }

  function selectedTechTileChoice(): TechTileChoice | undefined {
    if (!upgradeTechTile) return undefined;
    if (upgradeTechTile.kind === 'Standard') {
      return {
        kind: 'Standard',
        tile: upgradeTechTile.tile,
        advance_track: upgradeAdvanceTrack,
        bonus_build_coord: upgradeTechTile.tile === 11 ? upgradeBonusCoord : null,
      };
    }
    if (upgradeTechTile.kind === 'Advanced') {
      return {
        kind: 'Advanced',
        track: upgradeTechTile.track,
        covered_tile: upgradeCoveredTile ?? 0,
        advance_track: upgradeAdvanceTrack,
      };
    }
    return {
      kind: 'LostFleetAdvanced',
      covered_tile: upgradeCoveredTile ?? 0,
      advance_track: upgradeAdvanceTrack,
    };
  }

  function handleConfirm() {
    if (!selectedAction) return;
    switch (selectedAction) {
      case 'Build':
        if (activePlanet) actions.sendAction({ type: 'Build', coord: activePlanet });
        break;
      case 'GaiaFormation':
        if (activePlanet) actions.sendAction({ type: 'GaiaFormation', coord: activePlanet });
        break;
      case 'RoundBoosterImmediateGaiaFormation':
        if (activePlanet) {
          actions.sendAction({ type: 'RoundBoosterImmediateGaiaFormation', coord: activePlanet });
        }
        break;
      case 'RoundBoosterRangeBuild':
        if (activePlanet) {
          actions.sendAction({ type: 'RoundBoosterRangeBuild', coord: activePlanet });
        }
        break;
      case 'RoundBoosterRangeGaiaFormation':
        if (activePlanet) {
          actions.sendAction({ type: 'RoundBoosterRangeGaiaFormation', coord: activePlanet });
        }
        break;
      case 'RoundBoosterRangeExploreSpaceship':
        if (spaceshipId) {
          actions.sendAction({ type: 'RoundBoosterRangeExploreSpaceship', ship: spaceshipId });
        }
        break;
      case 'Upgrade':
        if (activePlanet && upgradeTarget) {
          actions.sendAction({
            type: 'Upgrade',
            coord: activePlanet,
            to: upgradeTarget,
            tech_tile_choice: selectedTechTileChoice(),
          });
        }
        break;
      case 'ResearchAdvance':
        // handled per-track-button below (no separate confirm step)
        break;
      case 'FormFederation':
        if (federationSelection.valid && federationToken) {
          actions.sendAction({
            type: 'FormFederation',
            hexes: federationSelection.planetHexes,
            satellite_hexes: federationSelection.satelliteHexes,
            token: federationToken,
            bonus_build_coord: resolvedFederationBonusCoord,
            bonus_tech_tile: resolvedFederationBonusTechTile,
            bonus_research_track: resolvedFederationBonusResearchTrack,
          });
        }
        break;
      case 'PowerAction':
        // Only the two coord-taking slots (2, 6) reach this confirm step —
        // the rest send immediately when clicked, see POWER_ACTIONS below.
        if (selectedPowerActionId !== null && activePlanet) {
          actions.sendAction({ type: 'PowerAction', id: selectedPowerActionId, coord: activePlanet });
        }
        break;
      case 'SpecialAction':
        if (currentPlayer?.faction === 'SpaceGiants') {
          const choice = selectedTechTileChoice();
          if (choice) actions.sendAction({ type: 'SpaceGiantsGainTechTile', choice });
        } else {
          actions.sendAction({ type: 'SpecialAction', id: 1 });
        }
        break;
      case 'AmbasSwapPlanetaryInstitute':
        if (activePlanet) {
          actions.sendAction({ type: 'AmbasSwapPlanetaryInstitute', mine_coord: activePlanet });
        }
        break;
      case 'FiraksDowngradeResearchLab':
        if (activePlanet && selectedResearchTrack) {
          actions.sendAction({
            type: 'FiraksDowngradeResearchLab',
            coord: activePlanet,
            track: selectedResearchTrack,
          });
        }
        break;
      case 'BescodsLowestResearchAdvance':
        // handled by the per-track buttons below
        break;
      case 'IvitsPlaceSpaceStation':
        if (activePlanet) {
          actions.sendAction({ type: 'IvitsPlaceSpaceStation', coord: activePlanet });
        }
        break;
      case 'TinkeroidsUseTile':
        // Resource tiles (no coord needed) dispatch directly from their picker button below;
        // this only fires for the two "Build a Mine" tiles once a board hex is also selected.
        if (selectedTinkeringTile !== null && activePlanet) {
          actions.sendAction({
            type: 'TinkeroidsUseTile',
            tile: selectedTinkeringTile,
            coord: activePlanet,
          });
        }
        break;
      case 'MoweydsPlacePowerRing':
        if (activePlanet) {
          actions.sendAction({ type: 'MoweydsPlacePowerRing', coord: activePlanet });
        }
        break;
      case 'ExploreSpaceship':
        if (spaceshipId) actions.sendAction({ type: 'ExploreSpaceship', ship: spaceshipId });
        break;
      case 'ExamineArtifact':
        if (examineArtifactId !== null) {
          actions.sendAction({
            type: 'ExamineArtifact',
            artifact: examineArtifactId,
            copy_federation_token_kind: examineArtifactId === 10 ? replayFederationKind : null,
            bonus_build_coord:
              examineArtifactId === 10 &&
              (replayFederationKind === 14 ||
                replayFederationKind === 15 ||
                (replayFederationKind === 12 && federationBonusTechTile === 11))
                ? activePlanet
                : null,
            bonus_tech_tile:
              examineArtifactId === 10 && replayFederationKind === 12
                ? federationBonusTechTile
                : null,
            bonus_research_track:
              examineArtifactId === 10 && replayFederationKind === 12 ? selectedResearchTrack : null,
          });
        }
        break;
      case 'SpaceshipCreditTerraform':
        if (activePlanet) {
          actions.sendAction({ type: 'SpaceshipCreditTerraform', coord: activePlanet });
        }
        break;
      case 'TwilightFreeResearchLab':
        if (activePlanet) {
          actions.sendAction({ type: 'TwilightFreeResearchLab', coord: activePlanet });
        }
        break;
      case 'TwilightReplayFederationToken':
        if (replayFederationKind !== null) {
          actions.sendAction({
            type: 'TwilightReplayFederationToken',
            token_kind: replayFederationKind,
            bonus_build_coord:
              replayFederationKind === 14 ||
              replayFederationKind === 15 ||
              (replayFederationKind === 12 && federationBonusTechTile === 11)
                ? activePlanet
                : null,
            bonus_tech_tile: replayFederationKind === 12 ? federationBonusTechTile : null,
            bonus_research_track:
              replayFederationKind === 12 ? selectedResearchTrack : null,
          });
        }
        break;
      case 'TwilightRangeBuild':
        if (activePlanet) actions.sendAction({ type: 'TwilightRangeBuild', coord: activePlanet });
        break;
      case 'TwilightRangeGaiaFormation':
        if (activePlanet) {
          actions.sendAction({ type: 'TwilightRangeGaiaFormation', coord: activePlanet });
        }
        break;
      case 'TwilightRangeExploreSpaceship':
        if (spaceshipId) {
          actions.sendAction({ type: 'TwilightRangeExploreSpaceship', ship: spaceshipId });
        }
        break;
      case 'RebellionFreeTradingStation':
        if (activePlanet) {
          actions.sendAction({ type: 'RebellionFreeTradingStation', coord: activePlanet });
        }
        break;
      case 'RebellionCreditsAndQic':
        actions.sendAction({ type: 'RebellionCreditsAndQic' });
        break;
      case 'RebellionGainTechTile':
        if (federationBonusTechTile !== null && selectedResearchTrack) {
          actions.sendAction({
            type: 'RebellionGainTechTile',
            tile: federationBonusTechTile,
            track: selectedResearchTrack,
            bonus_build_coord: federationBonusTechTile === 11 ? activePlanet : null,
          });
        }
        break;
      case 'TFMarsTechBonus':
        actions.sendAction({ type: 'TFMarsTechBonus' });
        break;
      case 'TFMarsGaiaFormation':
        if (activePlanet) {
          actions.sendAction({ type: 'TFMarsGaiaFormation', coord: activePlanet });
        }
        break;
      case 'EclipsePlanetTypeBonus':
        actions.sendAction({ type: 'EclipsePlanetTypeBonus' });
        break;
      case 'EclipseResearchBoost':
        // handled per-track-button below (no separate confirm step), same as ResearchAdvance
        break;
      case 'EclipseAsteroidMine':
        if (activePlanet) {
          actions.sendAction({ type: 'EclipseAsteroidMine', coord: activePlanet });
        }
        break;
      case 'GleensBuildMine':
        if (activePlanet) actions.sendAction({ type: 'GleensBuildMine', coord: activePlanet });
        break;
      case 'GleensGaiaFormation':
        if (activePlanet) {
          actions.sendAction({ type: 'GleensGaiaFormation', coord: activePlanet });
        }
        break;
      case 'GleensExploreSpaceship':
        if (spaceshipId) {
          actions.sendAction({ type: 'GleensExploreSpaceship', ship: spaceshipId });
        }
        break;
      case 'SpaceGiantsBuildMine':
        if (activePlanet) {
          actions.sendAction({ type: 'SpaceGiantsBuildMine', coord: activePlanet });
        }
        break;
      default:
        break;
    }
  }

  const selectedPowerActionNeedsCoord =
    selectedAction === 'PowerAction' &&
    selectedPowerActionId !== null &&
    (POWER_ACTIONS.find((a) => a.id === selectedPowerActionId)?.needsCoord ?? false);

  // Artifact 10 ("copy the effect of a Federation Token you own") reuses the same
  // `replayFederationKind`/follow-up state as `TwilightReplayFederationToken` below, since it's
  // the same underlying replay mechanism.
  const examiningArtifact10 = selectedAction === 'ExamineArtifact' && examineArtifactId === 10;

  const needsCoord =
    selectedAction === 'Build' ||
    selectedAction === 'GaiaFormation' ||
    selectedAction === 'RoundBoosterImmediateGaiaFormation' ||
    selectedAction === 'RoundBoosterRangeBuild' ||
    selectedAction === 'RoundBoosterRangeGaiaFormation' ||
    selectedAction === 'Upgrade' ||
    selectedAction === 'AmbasSwapPlanetaryInstitute' ||
    selectedAction === 'FiraksDowngradeResearchLab' ||
    selectedAction === 'SpaceshipCreditTerraform' ||
    selectedAction === 'TwilightFreeResearchLab' ||
    selectedAction === 'TwilightRangeBuild' ||
    selectedAction === 'TwilightRangeGaiaFormation' ||
    (selectedAction === 'TwilightReplayFederationToken' &&
      (replayFederationKind === 14 ||
        replayFederationKind === 15 ||
        (replayFederationKind === 12 && federationBonusTechTile === 11))) ||
    selectedAction === 'RebellionFreeTradingStation' ||
    selectedAction === 'TFMarsGaiaFormation' ||
    selectedAction === 'EclipseAsteroidMine' ||
    selectedAction === 'GleensBuildMine' ||
    selectedAction === 'GleensGaiaFormation' ||
    selectedAction === 'SpaceGiantsBuildMine' ||
    (examiningArtifact10 &&
      (replayFederationKind === 14 ||
        replayFederationKind === 15 ||
        (replayFederationKind === 12 && federationBonusTechTile === 11))) ||
    selectedPowerActionNeedsCoord;

  const replayNeedsBuildCoord =
    (selectedAction === 'TwilightReplayFederationToken' || examiningArtifact10) &&
    (replayFederationKind === 14 ||
      replayFederationKind === 15 ||
      (replayFederationKind === 12 && federationBonusTechTile === 11));
  const replayNeedsTechTile =
    (selectedAction === 'TwilightReplayFederationToken' || examiningArtifact10) &&
    replayFederationKind === 12;
  const replayReady =
    replayFederationKind !== null &&
    (!replayNeedsBuildCoord || !!activePlanet) &&
    (!replayNeedsTechTile || (federationBonusTechTile !== null && !!selectedResearchTrack));

  const federationKind = resolveFederationTokenKind(gameState, federationToken);
  const federationNeedsBuildCoord =
    federationKind === 14 ||
    federationKind === 15 ||
    (federationKind === 12 && resolvedFederationBonusTechTile === 11);
  const federationNeedsTechTile = federationKind === 12;
  const federationReady =
    federationSelection.valid &&
    federationKind !== null &&
    (!federationNeedsBuildCoord || !!resolvedFederationBonusCoord) &&
    (!federationNeedsTechTile ||
      resolvedFederationBonusTechTile !== null ||
      !hasUnownedStandardTechTile);

  const advancedTechSelected = upgradeTechTile?.kind === 'Advanced'
    || upgradeTechTile?.kind === 'LostFleetAdvanced';
  const upgradeAdvanceTrackValid = upgradeAdvanceTrack === null
    || canAdvanceFromTechTile(upgradeAdvanceTrack, advancedTechSelected);

  const canConfirm =
    (selectedAction === 'Build' && !!activePlanet) ||
    (selectedAction === 'GaiaFormation' && !!activePlanet) ||
    (selectedAction === 'RoundBoosterImmediateGaiaFormation' && !!activePlanet) ||
    (selectedAction === 'RoundBoosterRangeBuild' && !!activePlanet) ||
    (selectedAction === 'RoundBoosterRangeGaiaFormation' && !!activePlanet) ||
    (selectedAction === 'RoundBoosterRangeExploreSpaceship' && !!spaceshipId) ||
    (selectedAction === 'Upgrade' &&
      !!activePlanet &&
      !!upgradeTarget &&
      (!(upgradeTarget === 'PlanetaryInstitute' && currentPlayer?.faction === 'SpaceGiants') || upgradeTechTile !== null) &&
      (upgradeTechTile?.kind !== 'Standard' ||
        upgradeTechTile.tile !== 11 ||
        !!upgradeBonusCoord) &&
      (upgradeTechTile?.kind === 'Standard' ||
        upgradeTechTile === null ||
        upgradeCoveredTile !== null) &&
      upgradeAdvanceTrackValid) ||
    (selectedAction === 'FormFederation' && federationReady) ||
    (selectedAction === 'SpecialAction' &&
      upgradeTechTile !== null &&
      (upgradeTechTile.kind !== 'Standard' ||
        upgradeTechTile.tile !== 11 ||
        !!upgradeBonusCoord) &&
      (upgradeTechTile.kind === 'Standard' || upgradeCoveredTile !== null) &&
      upgradeAdvanceTrackValid) ||
    (selectedAction === 'AmbasSwapPlanetaryInstitute' && !!activePlanet) ||
    (selectedAction === 'FiraksDowngradeResearchLab' &&
      !!activePlanet &&
      !!selectedResearchTrack) ||
    (selectedAction === 'IvitsPlaceSpaceStation' && !!activePlanet) ||
    (selectedAction === 'TinkeroidsUseTile' &&
      selectedTinkeringTile !== null &&
      tinkeroidsTileNeedsCoord(selectedTinkeringTile) &&
      !!activePlanet) ||
    (selectedAction === 'MoweydsPlacePowerRing' && !!activePlanet) ||
    (selectedAction === 'ExamineArtifact' &&
      examineArtifactId !== null &&
      (!examiningArtifact10 || replayReady)) ||
    selectedAction === 'RebellionCreditsAndQic' ||
    selectedAction === 'TFMarsTechBonus' ||
    selectedAction === 'EclipsePlanetTypeBonus' ||
    (selectedAction === 'ExploreSpaceship' && !!spaceshipId) ||
    (selectedAction === 'SpaceshipCreditTerraform' && !!activePlanet) ||
    (selectedAction === 'TwilightFreeResearchLab' && !!activePlanet) ||
    (selectedAction === 'TwilightReplayFederationToken' && replayReady) ||
    (selectedAction === 'TwilightRangeBuild' && !!activePlanet) ||
    (selectedAction === 'TwilightRangeGaiaFormation' && !!activePlanet) ||
    (selectedAction === 'TwilightRangeExploreSpaceship' && !!spaceshipId) ||
    (selectedAction === 'RebellionFreeTradingStation' && !!activePlanet) ||
    (selectedAction === 'RebellionGainTechTile' &&
      federationBonusTechTile !== null &&
      !!selectedResearchTrack &&
      (federationBonusTechTile !== 11 || !!activePlanet)) ||
    (selectedAction === 'TFMarsGaiaFormation' && !!activePlanet) ||
    (selectedAction === 'EclipseAsteroidMine' && !!activePlanet) ||
    (selectedAction === 'GleensBuildMine' && !!activePlanet) ||
    (selectedAction === 'GleensGaiaFormation' && !!activePlanet) ||
    (selectedAction === 'GleensExploreSpaceship' && !!spaceshipId) ||
    (selectedAction === 'SpaceGiantsBuildMine' && !!activePlanet) ||
    (selectedPowerActionNeedsCoord && !!activePlanet);

  const availableActionButtons = ACTION_BUTTONS.filter(
    ({ actionType }) =>
      (actionType !== 'TinkeroidsUseTile' || (selectedTinkeringTile !== null
        && !currentPlayer?.faction_special_action_used_this_round
        && !currentPlayer?.tinkeroids_tiles_used?.includes(selectedTinkeringTile))) &&
      (actionType !== 'SpecialAction' || currentPlayer?.faction === 'SpaceGiants') &&
      (REQUIRED_FACTION_BY_ACTION[actionType] === undefined ||
        currentPlayer?.faction === REQUIRED_FACTION_BY_ACTION[actionType]) &&
      (!GLEENS_SPECIAL_ACTION_TYPES.includes(actionType) || currentPlayer?.faction === 'Gleens') &&
      (actionType !== 'SpaceGiantsBuildMine' || currentPlayer?.faction === 'SpaceGiants') &&
      (REQUIRED_ROUND_BOOSTER_BY_ACTION[actionType] === undefined ||
        currentPlayer?.booster === REQUIRED_ROUND_BOOSTER_BY_ACTION[actionType]),
  );
  const primaryActionButtons = availableActionButtons.filter(({ actionType }) =>
    PRIMARY_ACTION_TYPES.has(actionType),
  );
  const specialActionButtons = availableActionButtons.filter(
    ({ actionType }) => !PRIMARY_ACTION_TYPES.has(actionType),
  );
  const selectedActionLabel =
    ACTION_BUTTONS.find(({ actionType }) => actionType === selectedAction)?.label ?? selectedAction;
  const selectedPowerActionLabel = selectedPowerActionId === null
    ? null
    : POWER_ACTIONS.find(({ id }) => id === selectedPowerActionId)?.label ?? null;
  const focusedActionTitle = selectedAction === 'FormFederation'
    ? '연방 구축'
    : selectedAction === 'PowerAction' && selectedPowerActionLabel
      ? selectedPowerActionLabel
      : selectedActionLabel;
  const actionInstruction = !selectedAction
    ? '1. 필요하면 무료 행동으로 자원을 준비한 뒤, 할 주 행동을 선택하세요.'
    : needsCoord && !activePlanet
      ? '2. 게임 보드에서 대상 헥스를 선택하세요.'
      : canConfirm
        ? '3. 선택 내용을 확인한 뒤 실행하세요.'
        : '2. 아래에서 세부 옵션을 선택하세요.';

  function renderLabelWithRangeIcon(label: string) {
    const pattern = /\+(\d+) 사거리/g;
    const nodes: (string | JSX.Element)[] = [];
    let lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = pattern.exec(label)) !== null) {
      if (match.index > lastIndex) nodes.push(label.slice(lastIndex, match.index));
      nodes.push(
        <span className="inline-range-badge" key={match.index}>
          <img src={rangeIcon} alt="사거리" />+{match[1]}
        </span>,
      );
      lastIndex = match.index + match[0].length;
    }
    nodes.push(label.slice(lastIndex));
    return nodes;
  }

  function renderActionButton({ label, actionType, shortcut }: (typeof ACTION_BUTTONS)[number]) {
    const spaceshipSlot = SPACESHIP_ACTION_SLOT_BY_TYPE[actionType];
    const requiredSpaceship = REQUIRED_SPACESHIP_BY_ACTION[actionType];
    const requiredSpaceshipBoard = gameState.spaceship_boards.find(
      (board) => board.id === requiredSpaceship,
    );
    const lacksSpaceshipAccess =
      requiredSpaceshipBoard !== undefined &&
      !requiredSpaceshipBoard.explorers.includes(myPlayerId) &&
      !exploredShipIndexes.has(shipIndex[requiredSpaceshipBoard.id]);
    const usedThisRound =
      (spaceshipSlot !== undefined && gameState.used_spaceship_actions.includes(spaceshipSlot)) ||
      (GLEENS_SPECIAL_ACTION_TYPES.includes(actionType) &&
        !!currentPlayer?.gleens_special_action_used_this_round) ||
      (actionType === 'SpaceGiantsBuildMine' &&
        !!currentPlayer?.space_giants_special_action_used_this_round) ||
      (REQUIRED_FACTION_BY_ACTION[actionType] !== undefined &&
        !!currentPlayer?.faction_special_action_used_this_round) ||
      (REQUIRED_ROUND_BOOSTER_BY_ACTION[actionType] !== undefined &&
        !!currentPlayer?.round_booster_special_action_used_this_round);
    const needsTinkeringTile =
      actionType === 'TinkeroidsUseTile' && selectedTinkeringTile === null;
    const spaceGiantsPiUnavailable =
      actionType === 'SpecialAction' &&
      (!hasSpaceGiantsPi || !!currentPlayer?.pi_ability_used);
    const unavailableReason = usedThisRound
      ? '이번 라운드 사용됨'
      : spaceGiantsPiUnavailable
        ? currentPlayer?.pi_ability_used
          ? '이번 게임 사용됨'
          : '행성의회 필요'
      : needsTinkeringTile
        ? '이번 라운드 타일 선택 필요'
      : lacksSpaceshipAccess
        ? `${requiredSpaceship} 함선 진입 필요`
        : null;

    return (
      <button
        key={actionType}
        className={clsx(
          'btn action-btn',
          unavailableReason ? 'action-btn--unavailable' : 'action-btn--available',
          selectedAction === actionType && 'action-btn--selected',
        )}
        disabled={usedThisRound || lacksSpaceshipAccess || needsTinkeringTile}
        title={unavailableReason ?? undefined}
        onClick={() => handleActionSelect(actionType)}
      >
        {REQUIRED_ROUND_BOOSTER_BY_ACTION[actionType] !== undefined && (() => {
          const boosterId = REQUIRED_ROUND_BOOSTER_BY_ACTION[actionType]!;
          const src = roundBoosterImageSrc(boosterId);
          return src ? <ActionCrop id={boosterId === 5 ? 'booster-5' : 'booster-8'} src={src} used={usedThisRound} /> : null;
        })()}
        <span className="action-label">
          {unavailableReason ? `${label} (${unavailableReason})` : renderLabelWithRangeIcon(label)}
        </span>
        {shortcut && <kbd className="action-shortcut">{shortcut}</kbd>}
      </button>
    );
  }

  return (
    <div className="action-panel">
      <h3 className="action-panel-title">
        {focusedAction && focusedActionTitle ? focusedActionTitle : '내 턴 · 행동'}
      </h3>
      {!focusedAction && (
        <div className="action-guide" aria-live="polite">
          {selectedActionLabel && <strong>{selectedActionLabel} 선택됨</strong>}
          <p>{actionInstruction}</p>
          <span>빛나는 버튼은 현재 선택할 수 있습니다.</span>
        </div>
      )}
      {selectedAction && !focusedAction ? (
        <button className="btn btn-ghost action-change-btn" onClick={() => actions.selectAction(null)}>
          다른 행동 선택
        </button>
      ) : !selectedAction ? (
        <>
          <h4 className="action-panel-subtitle">기본 행동</h4>
          <div className="action-buttons">{primaryActionButtons.map(renderActionButton)}</div>
          {specialActionButtons.length > 0 && (
            <details className="action-more">
              <summary>특수·확장 행동 ({specialActionButtons.length})</summary>
              <div className="action-buttons">{specialActionButtons.map(renderActionButton)}</div>
            </details>
          )}
        </>
      ) : null}

      {!focusedAction && !selectedAction && currentPlayer &&
        ((currentPlayer.tech_tiles ?? []).some((t) => TECH_TILE_SPECIAL_ACTION_IDS.has(t)) ||
          (currentPlayer.advanced_tech_tiles ?? []).some((t) =>
            ADVANCED_TECH_TILE_SPECIAL_ACTION_IDS.has(t),
          )) && (
          <div className="action-buttons">
            {(currentPlayer.tech_tiles ?? [])
              .filter((tile) => TECH_TILE_SPECIAL_ACTION_IDS.has(tile))
              .map((tile) => {
                const usedThisRound =
                  currentPlayer.tech_tile_special_actions_used_this_round?.includes(tile) ?? false;
                return (
                  <button
                    key={`tech-special-std-${tile}`}
                    className="btn action-btn"
                    disabled={usedThisRound}
                    onClick={() =>
                      actions.sendAction({
                        type: 'TechTileSpecialAction',
                        tile: { pool: 'Standard', tile },
                      })
                    }
                  >
                    {usedThisRound
                      ? `${TECH_TILE_LABELS[tile] ?? `표준 타일 ${tile}`} (이번 라운드 사용됨)`
                      : (TECH_TILE_LABELS[tile] ?? `표준 타일 ${tile}`)}
                  </button>
                );
              })}
            {(currentPlayer.advanced_tech_tiles ?? [])
              .filter((tile) => ADVANCED_TECH_TILE_SPECIAL_ACTION_IDS.has(tile))
              .map((tile) => {
                const usedThisRound =
                  currentPlayer.advanced_tech_tile_special_actions_used_this_round?.includes(
                    tile,
                  ) ?? false;
                return (
                  <button
                    key={`tech-special-adv-${tile}`}
                    className="btn action-btn"
                    disabled={usedThisRound}
                    onClick={() =>
                      actions.sendAction({
                        type: 'TechTileSpecialAction',
                        tile: { pool: 'Advanced', tile },
                      })
                    }
                  >
                    {usedThisRound
                      ? `${ADVANCED_TECH_TILE_LABELS[tile] ?? `고급 타일 ${tile}`} (이번 라운드 사용됨)`
                      : (ADVANCED_TECH_TILE_LABELS[tile] ?? `고급 타일 ${tile}`)}
                  </button>
                );
              })}
          </div>
        )}

      {selectedAction === 'ResearchAdvance' && (
        <div className="action-buttons">
          {(Object.keys(TRACK_LABELS) as ResearchTrack[]).map((track) => (
            <button
              key={track}
              className="btn action-btn"
              disabled={
                currentPlayer?.faction === 'BalTaks' &&
                track === 'Navigation' &&
                !currentPlayer.structures.some(
                  (structure) => structure.kind === 'PlanetaryInstitute',
                )
              }
              onClick={() => actions.sendAction({ type: 'ResearchAdvance', track })}
            >
              {TRACK_LABELS[track]}
            </button>
          ))}
        </div>
      )}

      {selectedAction === 'FiraksDowngradeResearchLab' && (
        <div className="action-buttons">
          {(Object.keys(TRACK_LABELS) as ResearchTrack[]).map((track) => (
            <button
              key={track}
              className={clsx(
                'btn action-btn',
                selectedResearchTrack === track && 'action-btn--selected',
              )}
              onClick={() => setSelectedResearchTrack(track)}
            >
              {TRACK_LABELS[track]}
            </button>
          ))}
        </div>
      )}

      {selectedAction === 'BescodsLowestResearchAdvance' && currentPlayer && (
        <div className="action-buttons">
          {(Object.keys(TRACK_LABELS) as ResearchTrack[]).map((track) => {
            const lowestLevel = Math.min(...Object.values(currentPlayer.research_tracks));
            const isLowest = researchTrackLevel(currentPlayer.research_tracks, track) === lowestLevel;
            return (
              <button
                key={track}
                className="btn action-btn"
                disabled={!isLowest}
                onClick={() =>
                  actions.sendAction({ type: 'BescodsLowestResearchAdvance', track })
                }
              >
                {TRACK_LABELS[track]}
              </button>
            );
          })}
        </div>
      )}

      {selectedAction === 'TinkeroidsUseTile' && currentPlayer && !currentPlayer.faction_special_action_used_this_round && !currentPlayer.tinkeroids_tiles_used?.includes(selectedTinkeringTile ?? -1) && (
        <>
          <div className="action-buttons">
            {selectedTinkeringTile !== null && (
                <button
                  className="btn action-btn tinkering-tile-btn action-btn--selected"
                  onClick={() => {
                    if (!tinkeroidsTileNeedsCoord(selectedTinkeringTile)) {
                      actions.sendAction({
                        type: 'TinkeroidsUseTile',
                        tile: selectedTinkeringTile,
                        coord: null,
                      });
                    }
                  }}
                >
                  <img
                    className="tinkering-tile-image"
                    src={tinkeringTileImageSrc(selectedTinkeringTile)}
                    alt={`팅커링 타일 ${selectedTinkeringTile}`}
                  />
                  <span>{TINKEROIDS_TILE_LABELS[selectedTinkeringTile]}</span>
                </button>
            )}
          </div>
          {selectedTinkeringTile !== null && tinkeroidsTileNeedsCoord(selectedTinkeringTile) && (
            <p className="action-hint">보드에서 광산을 건설할 헥스를 선택한 뒤 확인을 누르세요.</p>
          )}
        </>
      )}

      {selectedAction === 'EclipseResearchBoost' && (
        <div className="action-buttons">
          {(Object.keys(TRACK_LABELS) as ResearchTrack[]).map((track) => (
            <button
              key={track}
              className="btn action-btn"
              onClick={() => actions.sendAction({ type: 'EclipseResearchBoost', track })}
            >
              {TRACK_LABELS[track]}
            </button>
          ))}
        </div>
      )}

      {selectedAction === 'Upgrade' && (
        <div className="action-buttons">
          {UPGRADE_TARGETS.map(({ label, to }) => (
            <button
              key={label}
              className={clsx(
                'btn action-btn',
                upgradeTarget && JSON.stringify(upgradeTarget) === JSON.stringify(to) && 'action-btn--selected',
              )}
              onClick={() => setUpgradeTarget(to)}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {currentPlayer &&
        ((selectedAction === 'Upgrade' &&
          upgradeTarget &&
          (upgradeTarget === 'ResearchLab' || typeof upgradeTarget === 'object'
            || (upgradeTarget === 'PlanetaryInstitute' && currentPlayer.faction === 'SpaceGiants'))) ||
          selectedAction === 'SpecialAction') && (
        renderTechTilePicker(selectedAction === 'Upgrade' && !(upgradeTarget === 'PlanetaryInstitute' && currentPlayer.faction === 'SpaceGiants'))
      )}

      {selectedAction === 'PowerAction' && (
        <div className="action-buttons">
          {POWER_ACTIONS
            .filter(({ id }) => !focusedAction || selectedPowerActionId === null || id === selectedPowerActionId)
            .map(({ id, label, needsCoord: idNeedsCoord }) => {
            const taken = gameState.used_power_actions.includes(id);
            return (
              <button
                key={id}
                className={clsx(
                  'btn action-btn',
                  selectedPowerActionId === id && 'action-btn--selected',
                )}
                disabled={taken}
                onClick={() => {
                  if (idNeedsCoord) {
                    actions.selectPowerAction(id);
                  } else {
                    actions.sendAction({ type: 'PowerAction', id, coord: null });
                  }
                }}
              >
                {taken ? `${label} (이번 라운드 사용됨)` : label}
              </button>
            );
          })}
        </div>
      )}

      {(selectedAction === 'ExploreSpaceship' ||
        selectedAction === 'TwilightRangeExploreSpaceship' ||
        selectedAction === 'GleensExploreSpaceship' ||
        selectedAction === 'RoundBoosterRangeExploreSpaceship') && (
        <div className="action-buttons">
          {SPACESHIPS.map(({ id, label }) => {
            const board = gameState.spaceship_boards.find((b) => b.id === id);
            const alreadyExplored = (board?.explorers.includes(myPlayerId) ?? false)
              || exploredShipIndexes.has(shipIndex[id]);
            const full = board ? board.explorers.every((e) => e !== null) : false;
            return (
              <button
                key={id}
                className={clsx('btn action-btn', spaceshipId === id && 'action-btn--selected')}
                disabled={alreadyExplored || full}
                onClick={() => setSpaceshipId(id)}
              >
                {alreadyExplored ? `${label} (탐사 완료)` : full ? `${label} (자리 없음)` : label}
              </button>
            );
          })}
        </div>
      )}

      {selectedAction === 'ExamineArtifact' && (
        <>
          <p className="action-hint">
            함선에 남은 아티팩트 중 하나를 선택해 가져갑니다 (파워 6 소모).
          </p>
          <div className="action-buttons">
            {(
              gameState.spaceship_boards.find((b) => b.id === 'Twilight')?.artifact_pool ?? []
            ).map((artifactId, index) => (
              <button
                key={`${artifactId}-${index}`}
                className={clsx(
                  'btn action-btn',
                  examineArtifactId === artifactId && 'action-btn--selected',
                )}
                onClick={() => {
                  setExamineArtifactId(artifactId);
                  setReplayFederationKind(null);
                  setFederationBonusTechTile(null);
                  setSelectedResearchTrack(null);
                }}
              >
                {ARTIFACT_LABELS[artifactId] ?? `아티팩트 ${artifactId}`}
              </button>
            ))}
          </div>
        </>
      )}

      {(selectedAction === 'TwilightReplayFederationToken' || examiningArtifact10) && (
        <>
          <p className="action-hint">
            {hideReplayFederationChoices
              ? '위의 ‘내 연방’ 영역에서 복사할 토큰 이미지를 누르세요.'
              : '이미 보유한 연방 토큰 하나의 즉시 효과를 다시 받습니다.'}
          </p>
          {!hideReplayFederationChoices && (
            <div className="action-buttons">
              {ownedFederationKinds.map((kind) => (
                <button
                  key={kind}
                  className={clsx(
                    'btn action-btn',
                    replayFederationKind === kind && 'action-btn--selected',
                  )}
                  onClick={() => {
                    setReplayFederationKind(kind);
                    setFederationBonusTechTile(null);
                    setSelectedResearchTrack(null);
                  }}
                >
                  {FEDERATION_TOKEN_LABELS[kind] ?? `토큰 ${kind}`}
                </button>
              ))}
            </div>
          )}
          {replayFederationKind === 12 && (
            <TechTileAndTrackPicker
              gameState={gameState}
              tiles={availableStandardTechTiles}
              selectedTile={federationBonusTechTile}
              selectedTrack={selectedResearchTrack}
              onSelectTile={setFederationBonusTechTile}
              onSelectTrack={setSelectedResearchTrack}
            />
          )}
        </>
      )}

      {selectedAction === 'RebellionGainTechTile' && (
        <TechTileAndTrackPicker
          gameState={gameState}
          tiles={availableStandardTechTiles}
          selectedTile={federationBonusTechTile}
          selectedTrack={selectedResearchTrack}
          onSelectTile={setFederationBonusTechTile}
          onSelectTrack={setSelectedResearchTrack}
        />
      )}

      {selectedAction === 'FormFederation' && (
        <>
          <p className="action-hint">
            연방을 이룰 헥스를 보드에서 여러 개 선택하세요 ({selectedHexes.length}개 선택됨). 서로
            인접하지 않은 행성을 연결하려면 그 사이 빈 우주 헥스도 선택하세요. 빈 우주는 위성으로
            자동 분류됩니다 (위성 1개당 {currentPlayer?.faction === 'Ivits' ? '정보 큐브 1개' : '파워 토큰 1개'} 소모, 다른 연방에 재사용 불가).
          </p>
          {currentPlayer?.faction === 'Ivits' && (currentPlayer.federated_hexes?.length ?? 0) > 0 && (
            <p className="action-hint">
              하이브는 하나의 연방만 계속 확장합니다: 새로 선택한 헥스는 기존 연방과 연결되어야
              하며, 누적 파워가 7 × (보유 연방 토큰 수 + 1) 이상이어야 합니다. 이번 확장에 쓰는
              위성은 파워 대신 정보 큐브 1개씩 소모합니다.
            </p>
          )}
          {selectedHexes.length > 0 && (
            <div className="action-buttons">
              {selectedHexes.map((h) => {
                const key = hexKey(h.q, h.r);
                const isSatellite = federationSatelliteHexKeys.has(key);
                return (
                  <span
                    key={key}
                    className={clsx('federation-selected-hex', isSatellite && 'is-satellite')}
                  >
                    ({h.q}, {h.r}) {isSatellite ? '위성' : '내 건물'}
                  </span>
                );
              })}
            </div>
          )}
          <p
            className={clsx(
              'federation-validation-status',
              federationSelection.valid && 'is-valid',
            )}
            role="status"
          >
            파워 {federationSelection.power}/{federationSelection.minimumPower}
            {' · '}위성 {federationSelection.satelliteHexes.length}개
            {' · '}{federationSelection.reason}
          </p>
          {federationSelection.valid && !hideFederationTokenChoices && (
            <>
              <h4 className="action-panel-subtitle">획득할 연방 토큰</h4>
              <div className="action-buttons">
                {Array.from(new Set(gameState.research_board.federation_tokens))
                  .filter((kind) => kind !== 7)
                  .map((kind) => (
                  <button
                    key={`supply-${kind}`}
                    className={clsx(
                      'btn action-btn',
                      federationToken?.source === 'Supply' &&
                        federationToken.kind === kind &&
                        'action-btn--selected',
                    )}
                    onClick={() => {
                      setFederationToken({ source: 'Supply', kind });
                      setFederationBonusCoord(null);
                      setFederationBonusTechTile(null);
                      setSelectedResearchTrack(null);
                    }}
                  >
                    {FEDERATION_TOKEN_LABELS[kind] ?? `토큰 ${kind}`}
                  </button>
                  ))}
                {availableSpaceshipFederationTokens(gameState, myPlayerId).map(({ ship, kind }) => (
                  <button
                    key={`ship-${ship}`}
                    className={clsx(
                      'btn action-btn',
                      federationToken?.source === 'Spaceship' &&
                        federationToken.ship === ship &&
                        'action-btn--selected',
                    )}
                    onClick={() => {
                      setFederationToken({ source: 'Spaceship', ship });
                      setFederationBonusCoord(null);
                      setFederationBonusTechTile(null);
                      setSelectedResearchTrack(null);
                    }}
                  >
                    {ship}: {FEDERATION_TOKEN_LABELS[kind] ?? `토큰 ${kind}`}
                  </button>
                ))}
              </div>
            </>
          )}
          {federationSelection.valid && hideFederationTokenChoices && !federationToken && (
            <p className="action-hint">이동한 연방 토큰 보급에서 받을 토큰 이미지를 누르세요.</p>
          )}

          {federationNeedsBuildCoord && (
            <div className="federation-bonus-coord">
              <label>
                보너스 광산 좌표 q
                <input
                  type="number"
                  aria-label="보너스 광산 좌표 q"
                  value={resolvedFederationBonusCoord?.q ?? ''}
                  onChange={(e) =>
                    updateFederationBonusCoord({
                      q: Number(e.target.value),
                      r: resolvedFederationBonusCoord?.r ?? 0,
                    })
                  }
                />
              </label>
              <label>
                r
                <input
                  type="number"
                  aria-label="보너스 광산 좌표 r"
                  value={resolvedFederationBonusCoord?.r ?? ''}
                  onChange={(e) =>
                    updateFederationBonusCoord({
                      q: resolvedFederationBonusCoord?.q ?? 0,
                      r: Number(e.target.value),
                    })
                  }
                />
              </label>
            </div>
          )}

          {federationNeedsTechTile && !hideFederationTechPicker && (
            <TechTileAndTrackPicker
              gameState={gameState}
              tiles={availableStandardTechTiles}
              selectedTile={resolvedFederationBonusTechTile}
              selectedTrack={resolvedFederationBonusResearchTrack}
              onSelectTile={setFederationBonusTechTile}
              onSelectTrack={setSelectedResearchTrack}
            />
          )}
        </>
      )}

      {needsCoord && !activePlanet && (
        <p className="action-hint">보드에서 대상 헥스를 선택하세요</p>
      )}
      {needsCoord && activePlanet && (
        <p className="action-hint">
          선택된 헥스: ({activePlanet.q}, {activePlanet.r})
        </p>
      )}

      {selectedAction && canConfirm && (
        <button className="btn btn-primary confirm-btn" onClick={handleConfirm}>
          확인
        </button>
      )}

      {!focusedAction && hasAcademyQic(gameState, myPlayerId) && (
        <button
          className="btn btn-secondary confirm-btn"
          disabled={academyQicActionUsedThisRound(gameState, myPlayerId)}
          onClick={handleAcademyQicAction}
        >
          {academyQicActionUsedThisRound(gameState, myPlayerId)
            ? '아카데미(정보 큐브) 행동 — 이번 라운드 사용 완료'
            : '아카데미(정보 큐브) 행동 — 정보 큐브 획득'}
        </button>
      )}

      {!focusedAction && <div className="free-actions">
        <h4 className="action-panel-subtitle">무료 행동 · 주 행동 전/중 사용 가능</h4>
        <div className="action-buttons">
          {FREE_ACTIONS.filter((option) =>
            isFreeActionAvailableToPlayer(currentPlayer, option),
          ).map((option) => {
            const maxCount = maxFreeActionCount(currentPlayer, option);
            const count = Math.min(freeActionCounts[option.kind] ?? 1, Math.max(maxCount, 1));
            return (
              <div className="free-action-row" key={option.kind}>
                <button
                  className="btn btn-small action-btn"
                  disabled={maxCount === 0}
                  title={maxCount === 0 ? '필요한 자원이 부족합니다.' : undefined}
                  onClick={() => handleFreeAction(option.kind, count)}
                >
                  {option.label}
                </button>
                <input
                  className="free-action-count"
                  aria-label={`${option.label} 수량`}
                  type="number"
                  min={1}
                  max={Math.max(maxCount, 1)}
                  disabled={maxCount === 0}
                  value={count}
                  onChange={(event) => {
                    const next = Math.max(1, Math.min(maxCount, Number(event.target.value) || 1));
                    setFreeActionCounts((counts) => ({ ...counts, [option.kind]: next }));
                  }}
                />
              </div>
            );
          })}
        </div>
      </div>}

      {!focusedAction && currentPlayer?.booster != null && (
        <div className="action-hint current-booster">
          <span>현재 라운드 부스터:</span>
          {roundBoosterImageSrc(currentPlayer.booster) && (
            <img
              className="current-booster-image"
              src={roundBoosterImageSrc(currentPlayer.booster)}
              alt={`라운드 부스터 ${currentPlayer.booster}`}
            />
          )}
        </div>
      )}
      {!focusedAction && gameState.round < 6 && gameState.boosters.length > 0 && (
        <div className="action-buttons booster-picker">
          {gameState.boosters.map((id) => (
            <button
              key={id}
              className={clsx('btn booster-picker-btn', passBoosterId === id && 'action-btn--selected')}
              onClick={() => setPassBoosterId(passBoosterId === id ? null : id)}
            >
              {roundBoosterImageSrc(id) ? (
                <img src={roundBoosterImageSrc(id)} alt={`라운드 부스터 ${id}`} />
              ) : (
                `라운드 부스터 #${id}`
              )}
            </button>
          ))}
        </div>
      )}
      {!focusedAction && (
        <button
          className="btn btn-ghost pass-btn"
          disabled={requiresBoosterChoice && passBoosterId === null}
          onClick={handlePass}
        >
          {requiresBoosterChoice && passBoosterId === null ? '새 부스터를 선택하세요' : '패스'}
        </button>
      )}
    </div>
  );
}

function TechTileAndTrackPicker({
  gameState,
  tiles,
  selectedTile,
  selectedTrack,
  onSelectTile,
  onSelectTrack,
}: {
  gameState: GameState;
  tiles?: number[];
  selectedTile: number | null;
  selectedTrack: ResearchTrack | null;
  onSelectTile: (tile: number) => void;
  onSelectTrack: (track: ResearchTrack) => void;
}) {
  return (
    <>
      <h4 className="action-panel-subtitle">표준 기술 타일</h4>
      <div className="action-buttons">
        {(tiles ?? gameState.research_board.tech_tiles).map((tileId) => (
          <button
            key={tileId}
            className={clsx('btn action-btn', selectedTile === tileId && 'action-btn--selected')}
            onClick={() => onSelectTile(tileId)}
          >
            기술 타일 #{tileId}
          </button>
        ))}
      </div>
      <h4 className="action-panel-subtitle">진보할 연구 트랙</h4>
      <div className="action-buttons">
        {(Object.keys(TRACK_LABELS) as ResearchTrack[]).map((track) => (
          <button
            key={track}
            className={clsx('btn action-btn', selectedTrack === track && 'action-btn--selected')}
            onClick={() => onSelectTrack(track)}
          >
            {TRACK_LABELS[track]}
          </button>
        ))}
      </div>
    </>
  );
}

function WaitingPanel({ text }: { text: string }) {
  return (
    <div className="action-panel action-panel--waiting">
      <p className="waiting-msg">{text}</p>
    </div>
  );
}
