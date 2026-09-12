import { useState } from 'react';
import { ActionToast } from '../ActionToast';
import { RecentActions } from '../RecentActions';
import { TurnBanner } from '../TurnBanner';
import type { GameLogEntry } from '../GameLog';
import { liveActionEntries, turnStatus } from '../../liveActivity';
import type { BoardState, GameEvent, GameState, PlayerState } from '../../types/game';
import './preview.css';

const PLAYERS = [
  { player_id: 0, nickname: '나' },
  { player_id: 1, nickname: '영희' },
  { player_id: 2, nickname: '철수' },
] as PlayerState[];

/** Real engine events, so the preview shows the wording live play produces, not hand-written text. */
const EVENTS: GameEvent[] = [
  { ResourceChanged: { player: 1, delta: { ore: -1, credits: -2 } } },
  { StructureBuilt: { player: 1, hex: '1,-1', kind: 'Mine' } },
  { ActionLog: { player: 1, action: 'Build', event_count: 2 } },
  { ResourceChanged: { player: 2, delta: { knowledge: -4 } } },
  { ResearchAdvanced: { player: 2, track: 'Navigation', level: 2 } },
  { ActionLog: { player: 2, action: 'ResearchAdvance', event_count: 2 } },
  { PlayerPassed: { player: 0, booster: 7 } },
  { ActionLog: { player: 0, action: 'Pass', event_count: 1 } },
];

/** Enough board for the log to name positions the way the real table does. */
const BOARD = {
  sectors: [{ id: 3, rotation: 0, origin: { q: 0, r: 0 } }],
  hexes: {
    '1,-1': {
      coord: { q: 1, r: -1 },
      planet: { planet_type: 'Volcanic', is_gaia_formed: false, owner: null },
      space_tile_kind: null,
      structures: [],
      satellites: [],
    },
  },
  lost_planet: null,
  spaceship_tiles: {},
} as unknown as BoardState;

function state(phase: GameState['phase']): GameState {
  return { players: PLAYERS, turn_order: [0, 1, 2], phase, round: 2 } as unknown as GameState;
}

const TURN_CASES: { label: string; phase: GameState['phase'] }[] = [
  { label: '내 차례', phase: { ActionPhase: { active_player: 0 } } as GameState['phase'] },
  { label: '상대 차례', phase: { ActionPhase: { active_player: 1 } } as GameState['phase'] },
  {
    label: '파워 충전 선택',
    phase: {
      ChargePowerPending: {
        queue: [{ player: 0, hex: { q: 1, r: -1 }, max_power: 2 }],
        resume_active_player: 1,
      },
    } as unknown as GameState['phase'],
  },
  { label: '수입 단계', phase: 'IncomePhase' as GameState['phase'] },
];

/** Isolated sandbox for the live-activity UI: no room, store, or socket. */
export function LiveActivityPreview() {
  const entries = liveActionEntries(EVENTS, PLAYERS, BOARD);
  const [turnCase, setTurnCase] = useState(0);
  const [toastIndex, setToastIndex] = useState(entries.length - 1);

  const toastEntry: GameLogEntry | null = entries[toastIndex] ?? null;

  return (
    <main className="live-activity-preview">
      <header className="live-activity-preview-header">
        <div>
          <p className="live-activity-preview-eyebrow">LIVE ACTIVITY PREVIEW</p>
          <h1>차례 안내 · 행동 알림 미리보기</h1>
        </div>
        <a className="btn btn-secondary" href="?">첫 화면</a>
      </header>
      <p className="live-activity-preview-description">
        실제 게임과 연결되지 않은 예시입니다. 문구는 게임 로그와 같은 방식으로 만들어집니다.
        실제 화면에서는 차례 안내가 상단 가운데, 행동 알림이 오른쪽 아래에 잠깐 나타납니다.
        위치는 좌표 대신 보드에 인쇄된 대로 "3번 섹터 화산 행성", "심우주 14번 섹터", "인터스페이스 소행성"처럼 표시됩니다.
      </p>

      <section className="live-activity-preview-block" aria-label="차례 안내">
        <h2>1. 차례 안내</h2>
        <div className="live-activity-preview-buttons">
          {TURN_CASES.map((example, index) => (
            <button
              key={example.label}
              type="button"
              className={`btn ${index === turnCase ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setTurnCase(index)}
            >
              {example.label}
            </button>
          ))}
        </div>
        <div className="live-activity-preview-stage">
          <TurnBanner status={turnStatus(state(TURN_CASES[turnCase].phase), 0)} />
        </div>
      </section>

      <section className="live-activity-preview-block" aria-label="행동 알림">
        <h2>2. 방금 일어난 행동 알림</h2>
        <div className="live-activity-preview-buttons">
          {entries.map((entry, index) => (
            <button
              key={entry.index}
              type="button"
              className={`btn ${index === toastIndex ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setToastIndex(index)}
            >
              {entry.text}
            </button>
          ))}
        </div>
        <div className="live-activity-preview-stage live-activity-preview-stage--right">
          <ActionToast entry={toastEntry} myPlayerId={0} />
        </div>
        <p className="live-activity-preview-note">
          실제 게임에서는 행동이 끝날 때마다 7초 동안 나타났다가 사라집니다. 접속 직후에는 지난 기록으로 알림이 뜨지 않습니다.
        </p>
      </section>

      <section className="live-activity-preview-block" aria-label="최근 행동과 안 읽은 표시">
        <h2>3. 최근 행동 · 안 읽은 기록 표시</h2>
        <div className="live-activity-preview-sidebar">
          <div className="game-sidebar-tabs" role="tablist" aria-label="오른쪽 패널 예시">
            <button type="button" role="tab" aria-selected="true" className="is-active">정보</button>
            <button type="button" role="tab" aria-selected="false">
              로그
              <span className="game-sidebar-unread">3</span>
            </button>
          </div>
          <RecentActions entries={[...entries].reverse().slice(0, 3)} onOpenLog={() => {}} />
        </div>
      </section>

      <section className="live-activity-preview-block" aria-label="보드 강조">
        <h2>4. 보드 위 강조</h2>
        <p className="live-activity-preview-note">
          방금 행동이 닿은 칸·연구 트랙·함선·기술 타일이 잠깐 강조됩니다. AI 리플레이가 쓰던 강조 표시를 실제 게임에 연결한 것이라
          이 미리보기에서는 보이지 않고, 실제 게임 화면에서만 확인할 수 있습니다.
        </p>
      </section>
    </main>
  );
}
