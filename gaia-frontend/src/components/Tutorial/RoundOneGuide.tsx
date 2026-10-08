import { useEffect, useState } from 'react';
import type { GameState } from '../../types/game';
import { currentTutorialStep, tutorialTargets } from '../../tutorial/round1';
import { useRoomStore } from '../../store/roomStore';
import { useGameStore } from '../../store/gameStore';
import { forgetRecentRoom } from '../../store/recentRoom';
import './roundOne.css';

const boardTour = [
  {
    title: '라운드 목표와 부스터',
    panel: 'game-overview',
    description: '맨 위에는 이번 라운드에 점수를 얻는 방법과 게임 종료 목표가 있습니다. 부스터는 이번 라운드의 능력이며, 패스할 때 다음 부스터를 고릅니다.',
    cue: '점수 타일과 부스터가 있는 맨 위 영역을 보세요.',
  },
  {
    title: '우주 지도',
    panel: 'game-map',
    description: '행성을 눌러 광산을 짓거나 가이아 프로젝트를 시작합니다. 함선도 이 지도에서 선택합니다. 이번 연습에서 눌러야 할 칸은 노란색으로 표시됩니다.',
    cue: '가운데 우주 지도에서 행성과 함선의 위치를 확인하세요.',
  },
  {
    title: '연구·기술·함선 행동',
    panel: 'game-research-section',
    description: '연구 트랙은 지식을 써서 올립니다. 기술 타일과 공용 파워 행동, 함선 행동은 이 아래쪽 영역에서 사용합니다.',
    cue: '연구판과 행동 칸이 있는 영역을 보세요.',
  },
  {
    title: '내 종족판과 자원',
    panel: 'game-factions',
    description: '내 종족판에서 건물과 자원, 파워 토큰의 위치를 봅니다. 오른쪽 정보 패널에는 자유 행동과 자원 변환이 있습니다.',
    cue: '「나」라고 적힌 종족판을 찾아보세요.',
  },
  {
    title: '자원 트랙·파워 순환·교환',
    panel: 'game-factions',
    description: '자원은 광석·크레딧·지식·QIC입니다. 광석·크레딧·지식은 종족판 위 트랙, QIC는 옆 보관 랙에 있습니다. 파워는 보라색 토큰이며 1→2→3구역으로 충전됩니다. 3구역 토큰만 쓸 수 있고, 쓴 토큰은 1구역으로 돌아갑니다.',
    cue: '급할 때 자유 행동으로 자원을 교환할 수 있지만 비율이 비쌉니다. 파워 3 → 광석 1, 공용 행동은 파워 4 → 광석 2입니다.',
  },
  {
    title: '한 라운드의 네 단계',
    panel: 'game-overview',
    description: '게임은 6라운드입니다. 매 라운드 수입 → 가이아 → 행동 → 마무리 순서로 진행됩니다. 행동 단계에는 광산·가이아 프로젝트, 업그레이드, 연방, 연구, 파워·QIC 행동, 특수 행동, 패스를 고릅니다.',
    cue: '지금은 1라운드 수입부터 시작합니다. 모두 패스하면 다음 라운드로 넘어갑니다.',
  },
] as const;

const tourTargets = [[], [], [], [], ['resource:track', 'resource:qic', 'power:I', 'power:II', 'power:III'], []] as const;

const incomeLabels = ['광석', '크레딧', '지식', 'QIC', '충전', '새 토큰', '점수'] as const;

function describeIncome(amounts: number[]): string {
  return amounts.flatMap((amount, index) => amount === 0 ? [] : [`${incomeLabels[index]} ${amount}`]).join(' · ') || '이번에는 없음';
}

export function RoundOneGuide({ state }: { state: GameState }) {
  const tutorial = state.tutorial!;
  const step = currentTutorialStep(tutorial);
  const [intro, setIntro] = useState(tutorial.step === 1);
  const [tourPage, setTourPage] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const notice = useRoomStore(s => s.lastError);
  const targets = intro ? tourTargets[tourPage].join('|') : tutorialTargets(state).join('|');
  const total = tutorial.steps.length + 2;
  const player = state.players[0];
  const charge = typeof state.phase === 'object' && 'ChargePowerPending' in state.phase
    ? state.phase.ChargePowerPending.queue.find(item => item.player === player.player_id)
    : undefined;
  const power = player.resources.power;
  const amount = charge ? Math.min(charge.max_power, power.bowl1 * 2 + power.bowl2, player.vp + 1) : 0;
  const moveToTwo = Math.min(power.bowl1, amount);
  const moveToThree = amount - moveToTwo;

  useEffect(() => {
    const wanted = new Set(targets.split('|'));
    function highlight() {
      document.querySelectorAll<HTMLElement | SVGElement>('[data-tutorial-target]').forEach(node => {
        const key = node.dataset.tutorialTarget ?? '';
        const personal = key === 'resource:track' || key === 'resource:qic' || key === 'income:building' || key === 'income:booster'
          || key.startsWith('cost:') || ['power:I', 'power:II', 'power:III', 'power:G'].includes(key);
        const ownBoard = !personal || !!node.closest('.game-table-player-card--me');
        node.classList.toggle('tutorial-highlight', wanted.has(key) && ownBoard);
      });
    }
    highlight();
    const observer = new MutationObserver(highlight);
    observer.observe(document.body, { childList: true, subtree: true });

    return () => {
      observer.disconnect();
      document.querySelectorAll('.tutorial-highlight').forEach(node => node.classList.remove('tutorial-highlight'));
    };
  }, [targets]);

  useEffect(() => {
    if (!intro) return;
    const section = document.getElementById(boardTour[tourPage].panel);
    const panel = boardTour[tourPage].panel === 'game-factions'
      ? section?.querySelector<HTMLElement>('.game-table-player-card--me') ?? section
      : section;
    if (!panel) return;
    panel.classList.add('tutorial-tour-highlight');
    panel.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
    return () => panel.classList.remove('tutorial-tour-highlight');
  }, [intro, tourPage]);

  function quit() {
    const room = useRoomStore.getState();
    if (room.roomCode) forgetRecentRoom(room.roomCode);
    useGameStore.getState().wsClient?.disconnect();
    useGameStore.getState().actions.reset();
    room.actions.reset();
    window.location.assign(window.location.pathname);
  }

  async function restart() {
    setBusy(true);
    setError('');
    try {
      await useRoomStore.getState().actions.createTutorialGame();
    } catch (e) {
      setError(e instanceof Error ? e.message : '다시 시작하지 못했습니다');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={`round-one-guide${intro ? ' round-one-guide--tour' : ''}${!step && !intro ? ' round-one-guide--complete' : ''}`} aria-label="1라운드 따라 하기">
      <div className="round-one-controls">
        <strong>1라운드 따라 하기</strong>
        <button type="button" disabled={busy} onClick={() => void restart()}>
          처음부터 다시
        </button>
        <button type="button" onClick={quit}>그만하기</button>
      </div>
      <progress className="round-one-progress" value={intro ? 0 : Math.min(tutorial.step, total)} max={total} aria-label="튜토리얼 진행률" />
      {error && <p role="alert">{error}</p>}
      {intro ? (
        <div className="round-one-tour">
          <h2>0 / {total} · 판과 목표</h2>
          <p className="round-one-kicker">판 둘러보기 {tourPage + 1} / {boardTour.length}</p>
          <h3>{boardTour[tourPage].title}</h3>
          <p className="round-one-instruction">{boardTour[tourPage].description}</p>
          <p className="round-one-cue">{boardTour[tourPage].cue}</p>
          {tourPage === boardTour.length - 1 && (
            <>
              <p>연습이라 자원·건물·연구를 미리 받았습니다.</p>
              <details className="round-one-extra">
                <summary>이번 연습의 특별 설정과 시작 자원</summary>
                <ul>{tutorial.introduction.map(line => <li key={line}>{line}</li>)}</ul>
              </details>
            </>
          )}
          <div className="round-one-tour-actions">
            {tourPage > 0 && <button type="button" className="round-one-secondary" onClick={() => setTourPage(page => page - 1)}>이전 영역</button>}
            {tourPage < boardTour.length - 1 ? (
              <button type="button" className="round-one-primary" onClick={() => setTourPage(page => page + 1)}>다음 영역</button>
            ) : (
              <button type="button" className="round-one-primary" onClick={() => setIntro(false)}>첫 수입 받기</button>
            )}
          </div>
        </div>
      ) : step ? (
        <>
          <h2>{tutorial.step} / {total} · {step.title}</h2>
          {tutorial.step > 1 && (
            <p className="round-one-success" role="status">
              ✓ 잘했어요 · {tutorial.steps[tutorial.step - 2].title}
            </p>
          )}
          <p className="round-one-instruction">{step.instruction}</p>
          {tutorial.step === 1 ? (
            <button
              className="round-one-primary"
              type="button"
              data-tutorial-target="tutorial:income"
              onClick={() => useGameStore.getState().actions.sendAction(step.action)}
            >
              수입 받기
            </button>
          ) : (
            <p className="round-one-cue">노란 테두리로 표시된 곳을 눌러 진행하세요.</p>
          )}
          <p className="round-one-reason">{step.reason}</p>
          {tutorial.step === 2 && <p className="round-one-rule" aria-label="광산 비용 설명">① 삽: 얼음 행성 1단계 × 광석 3 = 광석 3. ② 거리: 내 건물에서 2칸, 항법 기본 거리 1이라 QIC 1개로 2칸 늘립니다. ③ 건설: 광석 1·크레딧 2. 합계 광석 4·크레딧 2·QIC 1.</p>}
          {tutorial.step === 3 && <p className="round-one-rule">상대 A가 (-2, 0)에 광산을 지었습니다. 내 (-1, -1) 교역소까지 1칸(허용 2칸)이므로 내 교역소 파워값 2만큼 충전할 수 있습니다.</p>}
          {tutorial.step === 4 && <p className="round-one-rule">광산 → 교역소 비용은 광석 2·크레딧 6입니다. 상대 광산까지 1칸이라 2칸 이내 할인으로 크레딧 3만 냅니다. 종족판 왼쪽 교역소 비용을 보세요.</p>}
          {tutorial.step === 5 && <p className="round-one-rule">파워를 쓰면 3구역 토큰이 1구역으로 돌아갑니다. 자유 행동은 차례를 넘기지 않지만 비싼 교환입니다.</p>}
          {tutorial.step === 5 && <figure className="tutorial-power-flow" aria-label="파워 사용 순환"><div className="tutorial-power-bowls"><span>1구역<strong>{power.bowl1} → {power.bowl1 + 1}</strong></span><span>2구역<strong>{power.bowl2} → {power.bowl2}</strong></span><span>3구역<strong>{power.bowl3} → {power.bowl3 - 1}</strong></span></div><figcaption>3구역의 토큰 1개를 써서 1구역으로 되돌립니다.</figcaption></figure>}
          {tutorial.step === 6 && <p className="round-one-rule">교역소 → 연구소: 광석 3·크레딧 5. 표준 기술은 바로 위 연구 트랙만 올라갑니다. 아래 줄 3장의 표준 기술은 원하는 트랙을 고릅니다. 이 파워 4 충전 기술(10)은 경제 아래라 경제가 오릅니다.</p>}
          {tutorial.step === 8 && <p className="round-one-rule">가이아포머를 보내며 파워 토큰을 가이아 구역으로 옮깁니다. 이번 라운드에는 쓸 수 없고 다음 가이아 단계에 돌아옵니다. 테란은 2구역으로 돌아옵니다.</p>}
          {tutorial.step === 11 && <p className="round-one-rule">파워 3 → 광석 1은 급할 때만 쓰는 교환입니다. 바로 다음 공용 칸은 파워 4 → 광석 2라 더 효율적입니다. 오른쪽 자유 행동 목록에서 나머지 비율도 확인하세요.</p>}
          {tutorial.step === 12 && <p className="round-one-rule">공용 칸의 파워 4 → 광석 2를 쓰세요. 파워 3 → 광석 1인 자유 교환보다 효율적이며, 한 라운드에 한 명만 쓸 수 있습니다.</p>}
          {tutorial.step === 13 && <aside className="round-one-rule" aria-label="연방 먼저 알아보기">연방은 내 건물의 파워값 합이 7 이상인 연결된 집합입니다. 떨어진 건물은 위성으로 잇고, 연방 토큰을 받으면 초록 면이 보입니다. 지금은 연습 시작 때 받은 초록 토큰을 고급 기술에 사용합니다. 24단계에서 직접 연방을 만듭니다.</aside>}
          {(tutorial.step === 13 || tutorial.step === 26) && <p className="round-one-rule">고급 기술 조건 3가지: 해당 연구 트랙 4단계 이상, 초록 연방 토큰을 회색으로 뒤집기, 덮을 표준 기술 보유. 고급 기술을 받으면 덮은 타일과 무관하게 원하는 연구 트랙을 올릴 수 있습니다.</p>}
          {tutorial.step === 15 && <p className="round-one-rule">(3, -5)의 내 건물에서 목표 (5, -6)까지 2칸입니다. 항법 기본 거리 1이라 QIC 1개로 거리 2칸을 늘립니다. 광산 기본 비용 광석 1·크레딧 2도 냅니다.</p>}
          {tutorial.step === 16 && <p className="round-one-rule">교역소 → 의회: 광석 4·크레딧 6. 의회를 지으면 테란의 종족 능력을 사용할 수 있습니다.</p>}
          {tutorial.step === 17 && <p className="round-one-rule">연구소 → 아카데미: 광석 6·크레딧 6. 즉시 광석 1·QIC 1을 주는 기술(4)을 받고, 아카데미의 라운드당 1회 QIC 행동이 열립니다.</p>}
          {tutorial.step === 24 && <p className="round-one-rule">연방은 내 건물의 파워값 합 7 이상이어야 합니다. 떨어진 건물을 위성 2개로 이어 한 덩어리로 만들고, 위성마다 파워 토큰 1개를 버립니다. 초록 연방 토큰을 받습니다.</p>}
          <ul className="round-one-timings" aria-label="효과 적용 시점">
            {step.timings.map(timing => <li key={timing}>{timing}</li>)}
          </ul>
          {step.action.type === 'Pass' && (
            <p>
              연구소마다 패스 3점 기술(7): 연구소 {player.structures.filter(s => s.kind === 'ResearchLab').length}개 × 3점.
              +3 거리 탐사 부스터(8)를 반납하고 지식 1 수입 부스터(1)를 선택합니다. 이번 패스로 마지막 순서가 됩니다.
            </p>
          )}
          {step.action.type === 'ChargePower' && charge && (
            <figure className="tutorial-power-flow" aria-label="파워 충전 전후">
              <div className="tutorial-power-bowls">
                <span>1구역<strong>{power.bowl1} → {power.bowl1 - moveToTwo}</strong></span>
                <span>2구역<strong>{power.bowl2} → {power.bowl2 + moveToTwo - moveToThree}</strong></span>
                <span>3구역<strong>{power.bowl3} → {power.bowl3 + moveToThree}</strong></span>
              </div>
              <figcaption>
                충전 = 토큰을 1→2→3구역으로 옮김. 3구역에 온 토큰만 쓸 수 있습니다.<br />
                충전 {amount} − 1 = {Math.max(0, amount - 1)} VP 지불
                <br />1구역을 먼저 비운 다음 2→3구역으로 옮깁니다.
                <br />충전은 기존 토큰의 이동이고, 토큰 획득은 새 토큰을 1구역에 추가합니다.
              </figcaption>
            </figure>
          )}
        </>
      ) : (
        <>
          <p className="round-one-success">✓ 잘했어요 · 1라운드를 마쳤습니다</p>
          <h2>{total - 1} / {total} · 2라운드 수입과 가이아</h2>
          <p>수입을 받았고 (0, -3)의 가이아 행성이 완성됐습니다. 테란 의회의 자원 전환은 생략했습니다. 일곱 색 행성은 종족 고향색과의 거리에 따라 테라포밍하고, 초차원 행성은 가이아 프로젝트 뒤에 광산을 짓습니다.</p>
          <h2>{total} / {total} · 지금 게임이 끝난다면</h2>
          <p>라운드 목표 타일은 그 라운드에 조건을 달성할 때 바로 점수를 줍니다. 최종 점수 타일 2개는 6라운드 뒤 순위로 계산합니다. 아래에는 연구 점수와 남은 자원 환산도 더한 현재 예상 점수가 보입니다. 게임을 끝내지 않습니다.</p>
          <div className="round-one-table-scroll">
          <table>
            <caption>종료 점수 미리보기 · 최종 점수 타일 2개 포함</caption>
            <thead>
              <tr>
                <th>항목</th>
                {tutorial.final_scores?.map(score => (
                  <th key={score.player_id}>
                    {state.players.find(p => p.player_id === score.player_id)?.nickname}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {([
                ['현재 점수', 'gameplay_vp'],
                ['최종 타일 합계', 'final_tile_vp'],
                ['연구 트랙', 'research_vp'],
                ['자원 환산', 'resource_vp'],
                ['종족 보너스', 'faction_vp'],
                ['비딩 차감', 'bid_penalty_vp'],
                ['합계', 'total_vp'],
              ] as const).map(([label, key]) => (
                <tr key={key}>
                  <th>{label}</th>
                  {tutorial.final_scores?.map(score => (
                    <td key={score.player_id}>{score[key]}</td>
                  ))}
                </tr>
              ))}
              {tutorial.final_tiles.map((tile, index) => (
                <tr key={tile.tile_id}>
                  <th>최종 타일 {index + 1} (#{tile.tile_id})</th>
                  {tutorial.final_scores?.map(score => (
                    <td key={score.player_id}>
                      {tile.scores.find(([id]) => id === score.player_id)?.[1]}
                    </td>
                  ))}
                </tr>
              ))}
              <tr>
                <th>순위</th>
                {tutorial.final_scores?.map(score => (
                  <td key={score.player_id}>
                    {1 + tutorial.final_scores!.filter(other => other.total_vp > score.total_vp).length}위
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
          </div>
          <p>다음에 배울 것: 함선별 나머지 보상, 항법 5단계의 잃어버린 행성, 연구 5단계의 토큰 뒤집기, 테란 의회의 가이아 자원 전환, 다른 인원수의 확장 고급 기술 25점 조건.</p>
          <a href="?tutorial=1">행동 설명 보기</a>
          {' · '}
          <button type="button" onClick={quit}>로비로</button>
        </>
      )}
      {!intro && (
        <>
          {tutorial.feedback.scores.length > 0 && (
            <ul aria-label="점수 출처" role="status">
              {tutorial.feedback.scores.map((score, index) => (
                <li key={index}>
                  {score.amount > 0 ? '+' : ''}{score.amount}점 · {score.source}
                </li>
              ))}
            </ul>
          )}
          {tutorial.feedback.pass.length > 0 && (
            <ul aria-label="패스 계산 내역">
              {tutorial.feedback.pass.map(line => <li key={line}>{line}</li>)}
            </ul>
          )}
          {tutorial.income.filter(income => income.round === state.round).map(income => (
            <details key={income.round} open>
              <summary>{income.round}라운드 수입 내역 · 수입 때마다</summary>
              <p className="round-one-income-note">충전은 인쇄된 충전량입니다.</p>
              <ul className="round-one-income-rows">
                {income.rows.filter(row => row.amounts.some(amount => amount !== 0)).map(row => (
                  <li key={row.source} className={`round-one-income-source--${row.source.startsWith('건물') ? 'building' : row.source.startsWith('연구') ? 'research' : row.source.startsWith('부스터') ? 'booster' : 'faction'}`}>
                    <strong>{row.source}</strong>
                    <span>{describeIncome(row.amounts)}</span>
                  </li>
                ))}
                <li className="round-one-income-total">
                  <strong>합계</strong>
                  <span>{describeIncome(incomeLabels.map((_, index) => income.rows.reduce((sum, row) => sum + row.amounts[index], 0)))}</span>
                </li>
              </ul>
            </details>
          ))}
        </>
      )}
      {!intro && tutorial.opponents.length > 0 && (
        <details open>
          <summary>방금 진행한 상대 수와 자동 처리</summary>
          <ul>
            {tutorial.opponents.map((move, index) => <li key={index}>{move.description}</li>)}
          </ul>
        </details>
      )}
      {notice?.code === 'TutorialStepMismatch' && <p role="alert">{notice.message}</p>}
    </section>
  );
}
