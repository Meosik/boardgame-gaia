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
] as const;

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
  const targets = intro ? '' : tutorialTargets(state).join('|');
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
        const ownPower = !key.startsWith('power:') || !['power:I', 'power:II', 'power:III'].includes(key)
          || !!node.closest('.game-table-player-card--me');
        node.classList.toggle('tutorial-highlight', wanted.has(key) && ownPower);
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
    const panel = tourPage === boardTour.length - 1
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
              <p>이번 연습은 자원과 연구를 미리 받습니다. 실제 게임과 다른 시작 조건은 아래에서 확인할 수 있습니다.</p>
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
          <ul className="round-one-timings" aria-label="효과 적용 시점">
            {step.timings.map(timing => <li key={timing}>{timing}</li>)}
          </ul>
          {step.action.type === 'Pass' && (
            <p>
              고급 기술 7: 연구소 {player.structures.filter(s => s.kind === 'ResearchLab').length}개 × 3점.
              부스터 8을 반납하고 부스터 1을 선택합니다. 이번 패스로 마지막 순서가 됩니다.
            </p>
          )}
          {step.action.type === 'ChargePower' && charge && (
            <figure className="tutorial-power-flow" aria-label="파워 충전 전후">
              <div className="tutorial-power-bowls">
                <span>1구역<br />{power.bowl1} → {power.bowl1 - moveToTwo}</span>
                <b>→<small>{moveToTwo}개 이동</small></b>
                <span>2구역<br />{power.bowl2} → {power.bowl2 + moveToTwo - moveToThree}</span>
                <b>→<small>{moveToThree}개 이동</small></b>
                <span>3구역<br />{power.bowl3} → {power.bowl3 + moveToThree}</span>
              </div>
              <figcaption>
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
          <p>수입을 받았고 (0, -3)의 가이아 행성이 완성됐습니다. 테란 의회의 자원 전환은 생략했습니다.</p>
          <h2>{total} / {total} · 지금 게임이 끝난다면</h2>
          <p>라운드 점수는 매 라운드 목표 타일로 바로 받습니다. 아래는 현재 상태의 계산이며 게임을 끝내지 않습니다.</p>
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
                  <li key={row.source}>
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
