import rangeIcon from '../assets/icons/normalized/range.webp';
import powerBadge1 from '../assets/icons/normalized/power_badge_1.webp';
import powerBadge3 from '../assets/icons/normalized/power_badge_3.webp';
import powerBadge4 from '../assets/icons/normalized/power_badge_4.webp';
import { FACTION_STRUCTURE_COLOR, structureImageSrc } from '../assets/structureImages';
import { ResourceToken, type DisplayResource } from './ResourceTokens';
import { GamePieceIcon } from './GamePieceIcon';
import { FREE_ACTIONS, maxFreeActionCount, isFreeActionAvailableToPlayer } from './freeActions';
import type { FreeActionKind, PlayerState, UndoState } from '../types/game';

// What each conversion produces — every `FREE_ACTIONS` entry (BurnPower aside, which gets its
// own bowl-token rendering below) yields exactly 1 unit of one resource, so this only needs to
// name which one for icon lookup. Power-token gains use the shared physical power-piece art.
const RESULT_RESOURCE: Partial<Record<FreeActionKind, DisplayResource>> = {
  CreditsToQic: 'qic',
  CreditsToOre: 'ore',
  CreditsToKnowledge: 'knowledge',
  GaiaformerToQic: 'qic',
  PowerToGaiaKnowledge: 'knowledge',
  PowerToQic: 'qic',
  PowerToOre: 'ore',
  QicToOre: 'ore',
  PowerToKnowledge: 'knowledge',
  PowerToCredit: 'credits',
  KnowledgeToCredit: 'credits',
  OreToCredit: 'credits',
};

// These two conversions produce an actual power token in a bowl (bowl1 and bowl3 respectively).
const POWER_TOKEN_RESULT_KINDS = new Set<FreeActionKind>(['OreToPower', 'OreToPowerBowl3']);

const POWER_COST_BADGE: Partial<Record<number, string>> = {
  1: powerBadge1,
  3: powerBadge3,
  4: powerBadge4,
};

interface SidebarTurnControlsProps {
  player: PlayerState;
  isMyTurn: boolean;
  onFreeAction: (kind: FreeActionKind) => void;
  rangePreviewQic?: number;
  onRangePreviewAdd?: () => void;
  showDevPowerChargeTest?: boolean;
  devPowerChargeTargeting?: boolean;
  onDevPowerChargeToggle?: () => void;
  undoState?: UndoState;
  players?: PlayerState[];
  onUndoFreeAction?: () => void;
  onRequestTurnUndo?: () => void;
  onRespondTurnUndo?: (approve: boolean) => void;
}

export function SidebarTurnControls({
  player,
  isMyTurn,
  onFreeAction,
  rangePreviewQic = 0,
  onRangePreviewAdd,
  showDevPowerChargeTest = false,
  devPowerChargeTargeting = false,
  onDevPowerChargeToggle,
  undoState,
  players = [],
  onUndoFreeAction,
  onRequestTurnUndo,
  onRespondTurnUndo,
}: SidebarTurnControlsProps) {
  const pendingUndo = undoState?.pending_request ?? null;
  const canUndoFreeAction = pendingUndo === null
    && isMyTurn
    && !player.passed
    && (rangePreviewQic > 0 || (
      undoState?.open_turn?.player === player.player_id
      && (undoState.open_turn.free_action_revisions.length ?? 0) > 0
    ));
  const canRequestTurnUndo = pendingUndo === null
    && undoState?.recent_turns.some((turn) => turn.player === player.player_id) === true;
  const requesterName = pendingUndo === null
    ? null
    : players.find((candidate) => candidate.player_id === pendingUndo.requester)?.nickname
      ?? `Player ${pendingUndo.requester}`;
  const mustRespond = pendingUndo?.required_approvals.includes(player.player_id) === true
    && pendingUndo.approvals.includes(player.player_id) === false;
  const controlsDisabled = !isMyTurn || player.passed;
  const bowl2PowerTokens = player.resources.power.bowl2
    + Number(player.resources.power.brainstone === 'Area2');
  const gaiaformerIcon = player.faction
    ? structureImageSrc(FACTION_STRUCTURE_COLOR[player.faction], 'gaiaformer')
    : undefined;
  const availableFreeActions = FREE_ACTIONS.filter(
    (option) => option.kind !== 'BurnPower' && isFreeActionAvailableToPlayer(player, option),
  );
  // The most-used conversions get fixed slots (row 2 and 3 of the grid, right after the burn
  // and range buttons in row 1) so the layout stays predictable turn to turn; everything else
  // (faction-specific conversions, the rarer generic ones) fills in below in whatever order
  // `FREE_ACTIONS` lists them.
  const PRIORITY_ORDER: FreeActionKind[] = ['PowerToQic', 'PowerToKnowledge', 'PowerToOre', 'PowerToCredit'];
  const priorityFreeActions = PRIORITY_ORDER
    .map((kind) => availableFreeActions.find((option) => option.kind === kind))
    .filter((option): option is (typeof availableFreeActions)[number] => option !== undefined);
  const remainingFreeActions = availableFreeActions.filter(
    (option) => !PRIORITY_ORDER.includes(option.kind),
  );

  function renderFreeActionButton(option: (typeof availableFreeActions)[number]) {
    const unavailable = controlsDisabled || maxFreeActionCount(player, option) < 1;
    const resultResource = RESULT_RESOURCE[option.kind];
    const resultIsPowerToken = POWER_TOKEN_RESULT_KINDS.has(option.kind);
    const costIsPower = option.cost.resource === 'bowl2' || option.cost.resource === 'bowl3';
    const powerCostBadge = costIsPower ? POWER_COST_BADGE[option.cost.amount] : undefined;
    const costResource = option.cost.resource === 'ore' || option.cost.resource === 'credits'
      || option.cost.resource === 'knowledge' || option.cost.resource === 'qic'
      ? option.cost.resource
      : undefined;
    return (
      <button
        key={option.kind}
        type="button"
        className="sidebar-power-action"
        aria-label={option.label}
        title={unavailable && !controlsDisabled ? `${option.label} · 자원이 부족합니다.` : option.label}
        disabled={unavailable}
        onClick={() => onFreeAction(option.kind)}
      >
        {powerCostBadge ? (
          <span className="sidebar-power-cost sidebar-power-cost--badge" aria-hidden>
            <img src={powerCostBadge} alt="" />
          </span>
        ) : costIsPower ? (
          <ResourceToken resource="power" value={option.cost.amount} compact />
        ) : costResource ? (
          <ResourceToken resource={costResource} value={option.cost.amount} compact />
        ) : (
          <span className="interaction-resource-token interaction-resource-token--compact" aria-hidden>
            {gaiaformerIcon && <img src={gaiaformerIcon} alt="" />}
            <strong>{option.cost.amount}</strong>
          </span>
        )}
        <span className="sidebar-action-arrow" aria-hidden>→</span>
        {resultIsPowerToken ? (
          <ResourceToken resource="power" value={1} compact />
        ) : (
          resultResource && <ResourceToken resource={resultResource} value={1} compact />
        )}
      </button>
    );
  }

  return (
    <section className="sidebar-turn-controls" aria-label="내 행동 보조 메뉴">
      <div className="sidebar-power-actions">
        <h2>자유 행동</h2>
        <div className="sidebar-power-action-grid">
          {(() => {
            const burnPower = FREE_ACTIONS.find((option) => option.kind === 'BurnPower')!;
            const unavailable = controlsDisabled || bowl2PowerTokens < burnPower.cost.amount;
            return (
              <button
                type="button"
                className="sidebar-power-action"
                aria-label={burnPower.label}
                title={unavailable && !controlsDisabled
                  ? `${burnPower.label} · 2단계 파워가 부족합니다.`
                  : burnPower.label}
                disabled={unavailable}
                onClick={() => onFreeAction('BurnPower')}
              >
                <span className="sidebar-power-bowl-token sidebar-power-bowl-token--two" aria-hidden>
                  <GamePieceIcon kind="power" />
                  <b>II</b><strong>{burnPower.cost.amount}</strong>
                </span>
                <span className="sidebar-action-arrow" aria-hidden>→</span>
                <span className="sidebar-power-bowl-token sidebar-power-bowl-token--three" aria-hidden>
                  <GamePieceIcon kind="power" />
                  <b>III</b><strong>1</strong>
                </span>
              </button>
            );
          })()}
          <button
            type="button"
            className={`sidebar-power-action sidebar-range-rule${rangePreviewQic > 0 ? ' sidebar-range-rule--active' : ''}`}
            aria-label="정보 큐브 1개로 사거리 2 증가 추가"
            title="누를 때마다 다음 원거리 행동에 사용할 정보 큐브 1개와 사거리 2를 추가합니다."
            disabled={controlsDisabled || rangePreviewQic >= player.resources.qic}
            onClick={onRangePreviewAdd}
          >
            <span className="sidebar-power-result" aria-hidden>
              <GamePieceIcon kind="qic" />
              <b>1</b>
            </span>
            <span className="sidebar-action-arrow" aria-hidden>→</span>
            <span className="sidebar-range-result" aria-hidden>
              <img src={rangeIcon} alt="" />
              <b>+2</b>
            </span>
          </button>
          {priorityFreeActions.map(renderFreeActionButton)}
          {remainingFreeActions.map(renderFreeActionButton)}
        </div>
        <p className="sidebar-range-help">
          {rangePreviewQic > 0
            ? `현재 +${rangePreviewQic * 2} 사거리 · 정보 큐브 ${rangePreviewQic}개 선택`
            : '사거리가 부족하면 필요한 만큼 눌러 추가하세요'}
        </p>
        {showDevPowerChargeTest && (
          <div className="sidebar-dev-test-actions">
            <button
              type="button"
              className={`sidebar-dev-power-charge${devPowerChargeTargeting ? ' sidebar-dev-power-charge--active' : ''}`}
              aria-pressed={devPowerChargeTargeting}
              disabled={controlsDisabled}
              onClick={onDevPowerChargeToggle}
            >
              {devPowerChargeTargeting ? '대상 선택 취소' : '내 파워 충전 테스트'}
            </button>
            {devPowerChargeTargeting && (
              <p>내 건물을 클릭하면 그 건물 가치만큼 받을 파워 충전을 확인합니다.</p>
            )}
          </div>
        )}
      </div>
      <div className="sidebar-undo-controls" aria-label="되돌리기">
        <h2>되돌리기</h2>
        {pendingUndo ? (
          <div className="sidebar-undo-request">
            <p>
              {pendingUndo.requester === player.player_id
                ? `다른 플레이어 승인 대기 중 (${pendingUndo.approvals.length}/${pendingUndo.required_approvals.length})`
                : `${requesterName}님의 직전 차례를 되돌릴까요?`}
            </p>
            {mustRespond && (
              <div className="sidebar-undo-response-buttons">
                <button type="button" onClick={() => onRespondTurnUndo?.(true)}>승인</button>
                <button type="button" onClick={() => onRespondTurnUndo?.(false)}>거절</button>
              </div>
            )}
            {!mustRespond && pendingUndo.requester !== player.player_id && (
              <small>응답 완료 · 다른 플레이어를 기다리는 중</small>
            )}
          </div>
        ) : (
          <div className="sidebar-undo-buttons">
            <button
              type="button"
              disabled={!canUndoFreeAction}
              title={canUndoFreeAction
                ? '이번 차례에 수행한 자유행동을 모두 복구하며 현재 행동 기회는 그대로 유지됩니다.'
                : '현재 차례에 되돌릴 자유행동이 없습니다.'}
              onClick={onUndoFreeAction}
            >
              이번 차례 자유행동 전부 되돌리기
            </button>
            <button
              type="button"
              disabled={!canRequestTurnUndo}
              title={canRequestTurnUndo
                ? '다른 플레이어 전원이 승인하면 해당 차례 시작 전으로 돌아갑니다.'
                : '승인을 요청할 수 있는 직전 차례가 없습니다.'}
              onClick={onRequestTurnUndo}
            >
              직전 차례 되돌리기 요청
            </button>
          </div>
        )}
      </div>
    </section>
  );
}
