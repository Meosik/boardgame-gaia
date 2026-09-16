import { useReplayHighlight } from '../replay/highlight';
import { factionBoardImageSrc } from '../assets/factionBoardImages';
import { explorationBoardImageSrc } from '../assets/explorationBoardImages';
import { ADVANCED_TECH_TILE_LABELS } from './advancedTechDescriptions';
import { roundBoosterImageSrc } from '../assets/roundBoosterImages';
import { tinkeringTileImageSrc } from '../assets/tinkeringTileImages';
import { ActionCrop, type ActionCropId } from './ActionCrop';
import { GamePieceIcon } from './GamePieceIcon';
import { academyActionReward } from './academyAction';
import { advancedTechTileImageSrc, standardTechTileImageSrc } from '../assets/techTileImages';
import {
  federationTokenBackImageSrc,
  federationTokenImageSrc,
} from '../assets/federationTokenImages';
import type { GameAction, PlayerState } from '../types/game';

const STANDARD_SPECIAL_ACTION_TILES = new Set([10]);
const ADVANCED_SPECIAL_ACTION_TILES = new Set([20, 21, 22]);

interface Props {
  id?: string;
  player: PlayerState;
  isMyTurn: boolean;
  mainActionLocked?: boolean;
  federationSelectionMode?: boolean;
  selectedFederationKind?: number | null;
  onSelectFederationKind?: (kind: number) => void;
  onAction: (action: GameAction) => void;
  onSelectExplorationAction?: (action: 'GleensBuildMine' | 'SpaceGiantsBuildMine') => void;
  onSelectTinkeringTile?: () => void;
  onSelectBescodsResearch?: () => void;
  onSelectFactionAction?: (action: 'FiraksDowngradeResearchLab' | 'IvitsPlaceSpaceStation') => void;
  onSelectBoosterAction?: (booster: 5 | 8 | 12) => void;
}

interface ActionTile {
  key: string;
  label: string;
  imageSrc: string;
  cropId?: ActionCropId;
  used: boolean;
  action?: GameAction;
  factionAction?: 'FiraksDowngradeResearchLab' | 'IvitsPlaceSpaceStation';
}

export function PlayerActionShelf({
  id,
  player,
  isMyTurn,
  mainActionLocked = false,
  federationSelectionMode = false,
  selectedFederationKind = null,
  onSelectFederationKind,
  onAction,
  onSelectExplorationAction,
  onSelectTinkeringTile,
  onSelectBescodsResearch,
  onSelectFactionAction,
  onSelectBoosterAction,
}: Props) {
  const replay = useReplayHighlight();
  const coveredTiles = new Set(player.covered_tech_tiles ?? []);
  const actionTiles: ActionTile[] = [];

  for (const tile of player.tech_tiles ?? []) {
    if (!STANDARD_SPECIAL_ACTION_TILES.has(tile) || coveredTiles.has(tile)) continue;
    const imageSrc = standardTechTileImageSrc(tile);
    if (!imageSrc) continue;
    actionTiles.push({
      key: `standard-${tile}`,
      cropId: `standard-${tile}` as ActionCropId,
      label: tile === 10 ? '기술 타일 · 파워 4 충전' : `일반 기술 타일 ${tile} 행동`,
      imageSrc,
      used: player.tech_tile_special_actions_used_this_round?.includes(tile) ?? false,
      action: { type: 'TechTileSpecialAction', tile: { pool: 'Standard', tile } },
    });
  }

  for (const tile of player.advanced_tech_tiles ?? []) {
    if (!ADVANCED_SPECIAL_ACTION_TILES.has(tile)) continue;
    const imageSrc = advancedTechTileImageSrc(tile);
    if (!imageSrc) continue;
    actionTiles.push({
      key: `advanced-${tile}`,
      cropId: `advanced-${tile}` as ActionCropId,
      label: `고급 기술 타일 ${tile} 행동 · ${ADVANCED_TECH_TILE_LABELS[tile]}`,
      imageSrc,
      used: player.advanced_tech_tile_special_actions_used_this_round?.includes(tile) ?? false,
      action: { type: 'TechTileSpecialAction', tile: { pool: 'Advanced', tile } },
    });
  }

  if (player.booster === 5 || player.booster === 8 || player.booster === 12) {
    const imageSrc = roundBoosterImageSrc(player.booster);
    if (imageSrc) actionTiles.push({
      key: 'booster',
      label: player.booster === 5 ? '부스터 · 즉시 가이아포밍' : player.booster === 12 ? '부스터 · 테라포밍 1단계 무료 (광산 비용 별도)' : '부스터 · 사거리 +3',
      imageSrc,
      cropId: `booster-${player.booster}`,
      used: player.round_booster_special_action_used_this_round ?? false,
    });
  }

  const tinkeringTile = player.tinkeroids_selected_tile;
  if (player.faction === 'Tinkeroids' && tinkeringTile != null
    && !player.faction_special_action_used_this_round
    && !player.tinkeroids_tiles_used?.includes(tinkeringTile)) {
    const imageSrc = tinkeringTileImageSrc(tinkeringTile);
    if (imageSrc) actionTiles.push({
      key: 'tinkering', label: `팅커로이드 타일 ${tinkeringTile} 사용`, imageSrc, used: false,
      action: { type: 'TinkeroidsUseTile', tile: tinkeringTile, coord: null },
    });
  }

  if (player.faction === 'Gleens' || player.faction === 'SpaceGiants') {
    const gleens = player.faction === 'Gleens';
    const imageSrc = explorationBoardImageSrc(player.faction);
    if (imageSrc) actionTiles.push({
      key: 'exploration',
      label: gleens ? '글린 · 사거리 +2 행동' : '스페이스자이언트 · 테라포밍 2단계 무료 광산 행동',
      imageSrc,
      cropId: gleens ? 'exploration-Gleens-range' : 'exploration-SpaceGiants-build-mine',
      used: gleens ? player.gleens_special_action_used_this_round : player.space_giants_special_action_used_this_round,
    });
  }

  if ((player.faction === 'Firaks' || player.faction === 'Ivits')
    && player.structures.some(({ kind }) => kind === 'PlanetaryInstitute')) {
    const firaks = player.faction === 'Firaks';
    const imageSrc = factionBoardImageSrc(player.faction);
    if (imageSrc) actionTiles.push({
      key: 'faction-pi',
      label: firaks ? '파이락 연구소 강등 + 무료 연구' : '하이브 우주정거장 배치',
      imageSrc,
      cropId: firaks ? 'faction-Firaks-downgrade' : 'faction-Ivits-space-station',
      used: player.faction_special_action_used_this_round ?? false,
      factionAction: firaks ? 'FiraksDowngradeResearchLab' : 'IvitsPlaceSpaceStation',
    });
  }

  if (player.faction === 'Bescods') {
    const imageSrc = factionBoardImageSrc(player.faction);
    if (imageSrc) actionTiles.push({
      key: 'bescods-research',
      label: '매드 안드로이드 최저 연구 무료 상승',
      imageSrc,
      cropId: 'faction-Bescods-research',
      used: player.faction_special_action_used_this_round ?? false,
    });
  }

  const hasQicAcademy = player.structures.some(
    ({ kind }) => typeof kind === 'object' && 'Academy' in kind && kind.Academy === 'Qic',
  );
  if (hasQicAcademy && player.faction) {
    const reward = academyActionReward(player.faction);
    const credits = reward.resource === 'credits';
    const imageSrc = factionBoardImageSrc(credits ? player.faction : 'HadschHallas');
    if (imageSrc) actionTiles.push({
      key: 'academy-qic',
      label: credits ? `${reward.label} 아카데미 행동 · ${reward.label} ${reward.amount}` : '정보 큐브 아카데미 행동',
      imageSrc,
      cropId: player.faction === 'Geodens' ? 'faction-Geodens-credit-academy'
        : player.faction === 'BalTaks' ? 'faction-BalTaks-credit-academy' : 'academy-qic',
      used: player.academy_qic_action_used_this_round,
      action: { type: 'AcademyQicAction' },
    });
  }

  const ownedFederationTokens = [
    ...player.federation_tokens.map((kind, index) => ({ kind, index, flipped: false })),
    ...(player.gray_federation_tokens ?? []).map((kind, index) => ({
      kind,
      index,
      flipped: true,
    })),
  ];
  const canSelectFederation = federationSelectionMode && isMyTurn && !!onSelectFederationKind;

  return (
    <section id={id} className="player-action-shelf" aria-label="내 행동 타일">
      <h3>내 행동 타일</h3>
      <div className="player-action-shelf-sections">
        <div className="player-action-shelf-actions">
          {actionTiles.length > 0 ? (
            <div className="player-action-shelf-grid">
              {actionTiles.map((tile) => (
                <button
                  key={tile.key}
                  type="button"
                  className="player-action-tile"
                  data-replay-highlight={replay?.player === player.player_id && (
                    tile.key.startsWith('standard-') ? replay.standardTech.has(Number(tile.key.slice(9)))
                    : tile.key.startsWith('advanced-') ? replay.advancedTech.has(Number(tile.key.slice(9)))
                    : tile.factionAction ? tile.factionAction === replay.actionType
                    : tile.action ? tile.action.type === replay.actionType
                    : tile.key === 'booster' ? replay.actionType.startsWith('RoundBooster')
                    : tile.key === 'bescods-research' ? replay.actionType === 'BescodsLowestResearchAdvance'
                    : tile.key === 'exploration' ? ['GleensBuildMine', 'SpaceGiantsBuildMine'].includes(replay.actionType)
                    : false
                  ) || undefined}
                  aria-label={`${tile.label}${tile.used ? ' · 이번 라운드 사용됨' : ''}`}
                  title={tile.label}
                  disabled={!isMyTurn || mainActionLocked || tile.used || (!!tile.factionAction && !onSelectFactionAction) || (tile.key === 'bescods-research' && !onSelectBescodsResearch) || (tile.key === 'exploration' && !onSelectExplorationAction) || (tile.key === 'booster' && !onSelectBoosterAction) || (tile.key === 'tinkering' && (tinkeringTile === 1 || tinkeringTile === 5) && !onSelectTinkeringTile)}
                  onClick={() => {
                    if (tile.factionAction) {
                      onSelectFactionAction?.(tile.factionAction);
                    } else if (tile.key === 'bescods-research') {
                      onSelectBescodsResearch?.();
                    } else if (tile.key === 'exploration') {
                      onSelectExplorationAction?.(player.faction === 'Gleens' ? 'GleensBuildMine' : 'SpaceGiantsBuildMine');
                    } else if (tile.key === 'booster' && (player.booster === 5 || player.booster === 8 || player.booster === 12)) {
                      onSelectBoosterAction?.(player.booster);
                    } else if (tile.key === 'tinkering' && (tinkeringTile === 1 || tinkeringTile === 5)) {
                      onSelectTinkeringTile?.();
                    } else if (tile.action) onAction(tile.action);
                  }}
                >
                  {tile.cropId ? (
                    <ActionCrop id={tile.cropId} src={tile.imageSrc} used={tile.used} />
                  ) : (
                    <>
                      <img src={tile.imageSrc} alt="" />
                      {tile.used && <GamePieceIcon kind="action-used" className="action-crop-closed" />}
                    </>
                  )}
                </button>
              ))}
            </div>
          ) : (
            <p>사용할 수 있는 개인 행동 타일이 여기에 표시됩니다.</p>
          )}
        </div>

        <section
          className={`player-owned-federations${federationSelectionMode ? ' is-selecting' : ''}`}
          aria-label="내 연방"
        >
          <header>
            <h4>내 연방</h4>
            {federationSelectionMode && <span>복사할 토큰을 누르세요</span>}
          </header>
          {ownedFederationTokens.length > 0 ? (
            <div className="player-owned-federation-list">
              {ownedFederationTokens.map(({ kind, index, flipped }) => {
                const src = flipped
                  ? federationTokenBackImageSrc(kind)
                  : federationTokenImageSrc(kind);
                if (!src) return null;
                const selected = federationSelectionMode && selectedFederationKind === kind;
                return (
                  <button
                    key={`${flipped ? 'gray' : 'green'}-${kind}-${index}`}
                    type="button"
                    className={`player-owned-federation-token${selected ? ' is-selected' : ''}`}
                    aria-label={`연방 토큰 ${kind}${flipped ? ' 회색면' : ''}${
                      federationSelectionMode ? ' · 효과 복사 선택' : ''
                    }`}
                    aria-pressed={federationSelectionMode ? selected : undefined}
                    disabled={!canSelectFederation}
                    onClick={() => onSelectFederationKind?.(kind)}
                  >
                    <img src={src} alt="" />
                  </button>
                );
              })}
            </div>
          ) : (
            <p>아직 획득한 연방 토큰이 없습니다.</p>
          )}
        </section>
      </div>
    </section>
  );
}
