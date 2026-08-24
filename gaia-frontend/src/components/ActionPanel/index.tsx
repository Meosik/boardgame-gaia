import { useState } from 'react';
import { clsx } from 'clsx';
import { useGameStore } from '../../store/gameStore';
import type {
  GameAction,
  GameState,
  PlayerId,
  QicActionKind,
  ResearchTrack,
  StructureType,
} from '../../types/game';

interface Props {
  gameState: GameState;
  myPlayerId: PlayerId;
}

type ActionKind = GameAction['type'];

const ACTION_BUTTONS: { label: string; actionType: ActionKind; shortcut?: string }[] = [
  { label: '광산 건설', actionType: 'Build', shortcut: 'M' },
  { label: '구조물 업그레이드', actionType: 'Upgrade', shortcut: 'U' },
  { label: '연구', actionType: 'ResearchAdvance', shortcut: 'R' },
  { label: '연방 형성', actionType: 'FormFederation', shortcut: 'F' },
  { label: '파워 액션', actionType: 'PowerAction', shortcut: 'P' },
  { label: '가이아 프로젝트', actionType: 'GaiaFormation', shortcut: 'G' },
  { label: 'QIC 액션', actionType: 'QicAction', shortcut: 'Q' },
  { label: '특수 능력', actionType: 'SpecialAction', shortcut: 'S' },
];

const TRACK_LABELS: Record<ResearchTrack, string> = {
  Terraforming: '테라포밍',
  Navigation: '항법',
  ArtificialIntelligence: '인공지능',
  GaiaProject: '가이아 프로젝트',
  Economy: '경제',
  Science: '과학',
};

const UPGRADE_TARGETS: { label: string; to: StructureType }[] = [
  { label: '교역소', to: 'TradingStation' },
  { label: '연구소', to: 'ResearchLab' },
  { label: '행성의회', to: 'PlanetaryInstitute' },
  { label: '아카데미(과학)', to: { Academy: 'Science' } },
  { label: '아카데미(QIC)', to: { Academy: 'Qic' } },
];

// Rulebook power-action board slots 1-7 (gaia-engine `power_action_cost`/
// `apply_power_effect`): cost in bowl3 power → effect.
const POWER_ACTIONS: { id: number; label: string }[] = [
  { id: 1, label: '파워 3 → 광석 3' },
  { id: 2, label: '파워 4 → 광석 2' },
  { id: 3, label: '파워 4 → 지식 2' },
  { id: 4, label: '파워 4 → 크레딧 7' },
  { id: 5, label: '파워 4 → 광석 1' },
  { id: 6, label: '파워 6 → QIC 2' },
  { id: 7, label: '파워 4 → 파워 2단계 충전' },
];

// Slot id matches gaia-engine's `qic_action_slot_id` — identifies the
// shared board slot regardless of a variant's coord payload.
const QIC_ACTIONS: { label: string; kind: QicActionKind; needsCoord: boolean; slotId: number }[] = [
  { label: 'QIC 1 → 광석 1', kind: 'GainOre', needsCoord: false, slotId: 1 },
  { label: 'QIC 1 → 연구 1단계', kind: 'ResearchStep', needsCoord: false, slotId: 2 },
  {
    label: 'QIC 3 → 위성 건설',
    kind: { BuildSatellite: { coord: { q: 0, r: 0 } } },
    needsCoord: true,
    slotId: 3,
  },
  {
    label: 'QIC 2 → 잃어버린 행성 개척',
    kind: { ColoniseLostPlanet: { coord: { q: 0, r: 0 } } },
    needsCoord: true,
    slotId: 4,
  },
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

export function ActionPanel({ gameState, myPlayerId }: Props) {
  const { selectedAction, activePlanet, selectedHexes, actions } = useGameStore((s) => ({
    selectedAction: s.selectedAction,
    activePlanet: s.activePlanet,
    selectedHexes: s.selectedHexes,
    actions: s.actions,
  }));

  const [upgradeTarget, setUpgradeTarget] = useState<StructureType | null>(null);
  const [qicActionKind, setQicActionKind] = useState<QicActionKind | null>(null);
  const [passBoosterId, setPassBoosterId] = useState<number | null>(null);

  const phase = gameState.phase;

  // ── Passive-action phase pauses take over the whole panel ────────────────

  if (typeof phase === 'object' && 'ChargePowerPending' in phase) {
    const entry = phase.ChargePowerPending.queue[0];
    if (!entry) return <WaitingPanel text="파워 충전 대기열 처리 중..." />;
    if (entry.player !== myPlayerId) {
      const name = gameState.players.find((p) => p.player_id === entry.player)?.nickname ?? '상대';
      return <WaitingPanel text={`${name}님이 파워 충전 여부를 결정 중입니다...`} />;
    }
    return (
      <div className="action-panel">
        <h3 className="action-panel-title">파워 충전</h3>
        <p className="action-hint">
          최대 {entry.max_power}까지 충전할 수 있습니다 ({entry.max_power - 1} VP 소모). 충전하시겠습니까?
        </p>
        <button
          className="btn btn-primary confirm-btn"
          onClick={() => actions.sendAction({ type: 'ChargePower', accept: true })}
        >
          충전 ({entry.max_power})
        </button>
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

  const isMyTurn =
    typeof phase === 'object' &&
    'ActionPhase' in phase &&
    phase.ActionPhase.active_player === myPlayerId;

  if (!isMyTurn) {
    const activeIdx =
      typeof phase === 'object' && 'ActionPhase' in phase ? phase.ActionPhase.active_player : null;
    const activeName =
      activeIdx !== null
        ? (gameState.players[activeIdx]?.nickname ?? `Player ${activeIdx}`)
        : '?';
    return <WaitingPanel text={`${activeName}의 턴입니다...`} />;
  }

  function resetSubSelection() {
    setUpgradeTarget(null);
    setQicActionKind(null);
  }

  function handleActionSelect(actionType: ActionKind) {
    resetSubSelection();
    actions.selectAction(actionType === selectedAction ? null : actionType);
  }

  function handlePass() {
    actions.sendAction({ type: 'Pass', booster_id: passBoosterId });
  }

  function handleAcademyQicAction() {
    actions.sendAction({ type: 'AcademyQicAction' });
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
      case 'Upgrade':
        if (activePlanet && upgradeTarget) {
          actions.sendAction({ type: 'Upgrade', coord: activePlanet, to: upgradeTarget });
        }
        break;
      case 'ResearchAdvance':
        // handled per-track-button below (no separate confirm step)
        break;
      case 'FormFederation':
        if (selectedHexes.length > 0) {
          actions.sendAction({ type: 'FormFederation', hexes: selectedHexes });
        }
        break;
      case 'PowerAction':
        // handled per-id-button below
        break;
      case 'SpecialAction':
        actions.sendAction({ type: 'SpecialAction', id: 1 });
        break;
      case 'QicAction':
        if (qicActionKind) {
          const kind: QicActionKind =
            typeof qicActionKind === 'object' && activePlanet
              ? ('BuildSatellite' in qicActionKind
                  ? { BuildSatellite: { coord: activePlanet } }
                  : { ColoniseLostPlanet: { coord: activePlanet } })
              : qicActionKind;
          actions.sendAction({ type: 'QicAction', kind });
        }
        break;
      default:
        break;
    }
  }

  const needsCoord = selectedAction === 'Build' || selectedAction === 'GaiaFormation' || selectedAction === 'Upgrade';
  const qicNeedsCoord =
    selectedAction === 'QicAction' &&
    qicActionKind !== null &&
    typeof qicActionKind === 'object';

  const canConfirm =
    (selectedAction === 'Build' && !!activePlanet) ||
    (selectedAction === 'GaiaFormation' && !!activePlanet) ||
    (selectedAction === 'Upgrade' && !!activePlanet && !!upgradeTarget) ||
    (selectedAction === 'FormFederation' && selectedHexes.length > 0) ||
    (selectedAction === 'SpecialAction') ||
    (selectedAction === 'QicAction' && !!qicActionKind && (!qicNeedsCoord || !!activePlanet));

  return (
    <div className="action-panel">
      <h3 className="action-panel-title">내 턴</h3>
      <div className="action-buttons">
        {ACTION_BUTTONS.map(({ label, actionType, shortcut }) => (
          <button
            key={actionType}
            className={clsx('btn action-btn', selectedAction === actionType && 'action-btn--selected')}
            onClick={() => handleActionSelect(actionType)}
          >
            <span className="action-label">{label}</span>
            {shortcut && <kbd className="action-shortcut">{shortcut}</kbd>}
          </button>
        ))}
      </div>

      {selectedAction === 'ResearchAdvance' && (
        <div className="action-buttons">
          {(Object.keys(TRACK_LABELS) as ResearchTrack[]).map((track) => (
            <button
              key={track}
              className="btn action-btn"
              onClick={() => actions.sendAction({ type: 'ResearchAdvance', track })}
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

      {selectedAction === 'PowerAction' && (
        <div className="action-buttons">
          {POWER_ACTIONS.map(({ id, label }) => {
            const taken = gameState.used_power_actions.includes(id);
            return (
              <button
                key={id}
                className="btn action-btn"
                disabled={taken}
                onClick={() => actions.sendAction({ type: 'PowerAction', id })}
              >
                {taken ? `${label} (이번 라운드 사용됨)` : label}
              </button>
            );
          })}
        </div>
      )}

      {selectedAction === 'QicAction' && (
        <div className="action-buttons">
          {QIC_ACTIONS.map(({ label, kind, slotId }) => {
            const taken = gameState.used_qic_action_slots.includes(slotId);
            return (
              <button
                key={label}
                className={clsx(
                  'btn action-btn',
                  qicActionKind &&
                    JSON.stringify(qicActionKind) === JSON.stringify(kind) &&
                    'action-btn--selected',
                )}
                disabled={taken}
                onClick={() => setQicActionKind(kind)}
              >
                {taken ? `${label} (이번 라운드 사용됨)` : label}
              </button>
            );
          })}
        </div>
      )}

      {selectedAction === 'FormFederation' && (
        <p className="action-hint">
          연방을 이룰 헥스를 보드에서 여러 개 선택하세요 ({selectedHexes.length}개 선택됨)
        </p>
      )}

      {(needsCoord || qicNeedsCoord) && !activePlanet && (
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

      {hasAcademyQic(gameState, myPlayerId) && (
        <button
          className="btn btn-secondary confirm-btn"
          disabled={academyQicActionUsedThisRound(gameState, myPlayerId)}
          onClick={handleAcademyQicAction}
        >
          {academyQicActionUsedThisRound(gameState, myPlayerId)
            ? '아카데미(QIC) 행동 — 이번 라운드 사용 완료'
            : '아카데미(QIC) 행동 — QIC 획득'}
        </button>
      )}

      {gameState.boosters.length > 0 && (
        <div className="action-buttons">
          {gameState.boosters.map((id) => (
            <button
              key={id}
              className={clsx('btn action-btn', passBoosterId === id && 'action-btn--selected')}
              onClick={() => setPassBoosterId(passBoosterId === id ? null : id)}
            >
              라운드 부스터 #{id}
            </button>
          ))}
        </div>
      )}
      <button className="btn btn-ghost pass-btn" onClick={handlePass}>
        패스
      </button>
    </div>
  );
}

function WaitingPanel({ text }: { text: string }) {
  return (
    <div className="action-panel action-panel--waiting">
      <p className="waiting-msg">{text}</p>
    </div>
  );
}
