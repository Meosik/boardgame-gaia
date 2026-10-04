import { useEffect, useState } from 'react';
import type { GameState } from '../../types/game';
import { currentTutorialStep, tutorialTargets } from '../../tutorial/round1';
import { useRoomStore } from '../../store/roomStore';
import { useGameStore } from '../../store/gameStore';
import { forgetRecentRoom } from '../../store/recentRoom';
import './roundOne.css';

export function RoundOneGuide({ state }: { state: GameState }) {
  const tutorial = state.tutorial!;
  const step = currentTutorialStep(tutorial);
  const [intro, setIntro] = useState(tutorial.step === 1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const notice = useRoomStore(s => s.lastError);
  const targets = tutorialTargets(state).join('|');
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
    <section className="round-one-guide" aria-label="1라운드 따라 하기">
      <div className="round-one-controls">
        <strong>1라운드 따라 하기</strong>
        <button type="button" disabled={busy} onClick={() => void restart()}>
          처음부터 다시
        </button>
        <button type="button" onClick={quit}>그만하기</button>
      </div>
      {error && <p role="alert">{error}</p>}
      {intro ? (
        <>
          <h2>0 / {total} · 판과 목표</h2>
          <ul>
            {tutorial.introduction.map(line => <li key={line}>{line}</li>)}
          </ul>
          <button type="button" onClick={() => setIntro(false)}>첫 광산 짓기</button>
        </>
      ) : step ? (
        <>
          <h2>{tutorial.step} / {total} · {step.title}</h2>
          {tutorial.step > 1 && (
            <p className="round-one-success" role="status">
              ✓ 잘했어요 · {tutorial.steps[tutorial.step - 2].title}
            </p>
          )}
          <p><strong>{step.instruction}</strong></p>
          <p>{step.reason}</p>
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
          <p>다음에 배울 것: 함선별 나머지 보상, 항법 5단계의 잃어버린 행성, 연구 5단계의 토큰 뒤집기, 테란 의회의 가이아 자원 전환, 다른 인원수의 확장 고급 기술 25점 조건.</p>
          <a href="?tutorial=1">행동 설명 보기</a>
          {' · '}
          <button type="button" onClick={quit}>로비로</button>
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
