import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { App } from '../../App';
import { factionDisplayName } from '../../displayNames';
import { ReplayHighlightContext, replayHighlight } from '../../replay/highlight';
import { useGameStore } from '../../store/gameStore';
import { candidateLabel, parseCoach, type CoachState } from './protocol';
import { TechnologyPicker } from './TechnologyPicker';
import { BoardChoices } from './BoardChoices';
import { FeedbackDialog } from './FeedbackDialog';
import { SidebarTurnControls } from '../SidebarTurnControls';
import { candidateCoordinates, matchesAction, type CoachBoardControls } from './boardSelection';
import type { HexCoord, ResearchTrack } from '../../types/game';
import { EMPTY_TECHNOLOGY, baseCandidate, groupedChoices, resolveTechnology, technologySummary,
  technologyVariants, type TechnologySelection } from './technology';
import './coach.css';

/** Approval-only local game. The embedded board cannot send game-server commands. */
export function AiCoach() {
  const [data, setData] = useState<CoachState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [technology, setTechnology] = useState<TechnologySelection>(EMPTY_TECHNOLOGY);
  const [boardChoices, setBoardChoices] = useState<number[] | null>(null);
  const [boardMessage, setBoardMessage] = useState('');
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const feedbackChoice = useRef('');
  const [filter, setFilter] = useState('');
  const [reason, setReason] = useState('');
  const [plan, setPlan] = useState('');
  const [busy, setBusy] = useState(false);
  const commandPending = useRef(false);
  const generation = useRef(0);
  const latest = useRef<CoachState | null>(null);
  const actions = useGameStore(s => s.actions);
  const alive = useRef(true);

  function accept(next: CoachState) {
    const old = latest.current;
    if (old?.session_id === next.session_id && old.snapshot.decision_id > next.snapshot.decision_id) return;
    const changed = old?.session_id !== next.session_id || old?.snapshot.decision_id !== next.snapshot.decision_id;
    latest.current = next;
    setData(next);
    if (changed) { setSelected(null); setTechnology(EMPTY_TECHNOLOGY); setBoardChoices(null); setBoardMessage(''); setReason(''); setPlan(''); setFilter(''); setFeedbackOpen(false); feedbackChoice.current = ''; }
  }

  useLayoutEffect(() => {
    alive.current = true;
    actions.setReadOnly(true);
    return () => { alive.current = false; actions.reset(); };
  }, [actions]);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      const requestGeneration = generation.current;
      try {
        if (!commandPending.current) {
          const response = await fetch('/coach-api/state', { signal: controller.signal, cache: 'no-store' });
          if (!response.ok) throw new Error('교정 서버에 연결하지 못했습니다. 게임은 자동 진행하지 않습니다.');
          const next = parseCoach(await response.json());
          if (!controller.signal.aborted && generation.current === requestGeneration && !commandPending.current) {
            accept(next); setError(null);
          }
        }
      } catch (e) {
        if (!controller.signal.aborted) setError(e instanceof Error ? e.message : '연결 실패');
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(poll, 1000);
      }
    }
    void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, []);

  const snapshot = data?.snapshot;
  useLayoutEffect(() => {
    if (!snapshot) return;
    actions.setReadOnly(true);
    actions.setMyPlayerId(snapshot.player ?? 0);
    actions.setGameState(snapshot.state);
  }, [snapshot, actions]);

  async function command(path: 'approve' | 'retry', body: Record<string, unknown>) {
    if (!data || commandPending.current) return;
    commandPending.current = true;
    generation.current++;
    setBusy(true); setError(null);
    try {
      const response = await fetch(`/coach-api/${path}`, { method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Coach-Token': data.token }, body: JSON.stringify(body) });
      const next = await response.json();
      if (!response.ok) throw new Error(next.error ?? '승인 처리 실패');
      if (alive.current) accept(parseCoach(next));
    } catch (e) {
      if (alive.current) setError(e instanceof Error ? e.message : '승인 처리 실패');
    } finally {
      commandPending.current = false;
      if (alive.current) setBusy(false);
    }
  }

  const rec = data?.recommendation;
  const baseIndex = selected ?? rec?.index ?? null;
  const variants = useMemo(() => snapshot && baseIndex !== null
    ? technologyVariants(snapshot.candidates, baseIndex, snapshot.state) : [], [snapshot, baseIndex]);
  const index = variants.length ? resolveTechnology(variants, technology) : baseIndex;
  const override = !!rec && index !== null && index !== rec.index;
  const labels = useMemo(() => snapshot?.candidates.map(c => candidateLabel(c, snapshot.state)) ?? [], [snapshot]);
  const groups = useMemo(() => snapshot && rec ? groupedChoices(snapshot.candidates, snapshot.state,
    rec.scores.map(s => s.value), rec.index) : [], [snapshot, rec]);
  const candidates = useMemo(() => groups
    .filter(({ label }) => label.toLocaleLowerCase().includes(filter.toLocaleLowerCase()))
    .sort((a, b) => Math.max(...b.indices.map(i => rec?.scores[i]?.value ?? 0))
      - Math.max(...a.indices.map(i => rec?.scores[i]?.value ?? 0))), [groups, filter, rec]);
  const ready = data?.status === 'ready' && !!rec && !busy && !error;
  const canSubmit = ready && !feedbackOpen && boardChoices === null && index !== null && (!override || (!!reason.trim() && !!plan.trim()));
  useEffect(() => {
    if (!ready || !override || boardChoices !== null) return;
    const key = `${data?.session_id}:${snapshot?.decision_id}:${index}`;
    if (feedbackChoice.current === key) return;
    feedbackChoice.current = key;
    setReason(''); setPlan(''); setFeedbackOpen(true);
  }, [ready, override, boardChoices, data?.session_id, snapshot?.decision_id, index]);
  const actor = snapshot?.state.players.find(p => p.player_id === snapshot.player);
  const chosen = index === null ? null : snapshot?.candidates[index];
  const selectedScore = index === null ? null : rec?.scores[index];
  function scrollBoard(id: string) {
    requestAnimationFrame(() => document.getElementById(id)?.scrollIntoView?.({ block: 'start', behavior: 'smooth' }));
  }
  function chooseBase(i: number) {
    if (!ready || !snapshot) return;
    setSelected(i); setTechnology(EMPTY_TECHNOLOGY); setBoardChoices(null); setFilter('');
    const tech = technologyVariants(snapshot.candidates, i, snapshot.state);
    setBoardMessage(tech.length ? '연구 보드에서 받을 기술 타일을 누르세요.' : '보드에서 선택했습니다. 오른쪽에서 확인 후 승인하세요.');
    if (tech.length) scrollBoard('game-research');
  }
  function offer(indices: number[]) {
    if (!ready) return;
    const matching = groups.flatMap(g => {
      const found = g.indices.filter(i => indices.includes(i));
      return found.length ? [found.includes(g.index) ? g.index : found[0]] : [];
    });
    if (matching.length === 1) { chooseBase(matching[0]); return; }
    setBoardChoices(indices);
    setBoardMessage(matching.length ? '이 대상에서 할 행동을 고르거나, 보드에서 후속 대상을 누르세요.'
      : '현재 합법 후보에 없는 선택입니다. 다른 대상을 골라 주세요.');
  }
  function pickAction(partial: Record<string, unknown>) {
    if (snapshot) offer(snapshot.candidates.flatMap((c, i) => matchesAction(c.action, partial) ? [i] : []));
  }
  function pickTypes(types: string[]) {
    if (snapshot) offer(snapshot.candidates.flatMap((c, i) => types.includes(c.action.type) ? [i] : []));
  }
  function coordinates(i: number): HexCoord[] {
    if (!snapshot) return [];
    const c = snapshot.candidates[i];
    const ship = typeof c.action.ship === 'string' ? snapshot.state.board.spaceship_tiles?.[c.action.ship as keyof typeof snapshot.state.board.spaceship_tiles] : null;
    return [...candidateCoordinates(c), ...(ship ? [ship] : [])];
  }
  function pickHex(coord: HexCoord) {
    if (!ready || !snapshot) return;
    if (technology.tileKey) {
      const matching = variants.filter(v => v.tileKey === technology.tileKey
        && (v.fixedTrack || v.track === technology.track)
        && candidateCoordinates(v.candidate).some(c => matchesAction(c, coord)));
      if (matching.length === 1) { setTechnology({ ...technology, detail: matching[0].index }); setBoardChoices(null); return; }
    }
    const scope = boardChoices?.length ? boardChoices : snapshot.candidates.map((_, i) => i);
    offer(scope.filter(i => coordinates(i).some(c => matchesAction(c, coord))));
  }
  function pickTech(tile: number, advanced = false) {
    if (!ready) return;
    const choices = variants.filter(v => v.tileId === tile && v.advanced === advanced);
    const keys = [...new Set(choices.map(v => v.tileKey))];
    if (keys.length !== 1) {
      setBoardChoices([]);
      setBoardMessage(keys.length ? '덮을 기존 기술을 오른쪽 기술 선택에서 골라 주세요.' : '먼저 기술을 받는 건물·행동을 선택하세요.');
      return;
    }
    setTechnology({ tileKey: keys[0], track: '', detail: null }); setBoardChoices(null);
    setBoardMessage(choices[0].fixedTrack ? '연결 트랙은 고정입니다. 표시된 결과를 확인하고 승인하세요.'
      : '연구 보드에서 올릴 트랙을 직접 누르세요.');
  }
  function pickTrack(track: ResearchTrack) {
    if (!ready || !snapshot) return;
    if (technology.tileKey) {
      if (variants.some(v => v.tileKey === technology.tileKey && !v.fixedTrack && v.track === track)) {
        setTechnology({ ...technology, track, detail: null }); setBoardChoices(null);
        setBoardMessage('기술과 연구 트랙을 선택했습니다. 승인 전까지 실행되지 않습니다.');
      }
      return;
    }
    const scope = boardChoices?.length ? boardChoices : snapshot.candidates.map((_, i) => i);
    offer(scope.filter(i => /ResearchAdvance|ResearchBoost/.test(snapshot.candidates[i].action.type)
      && snapshot.candidates[i].action.track === track));
  }
  const selectedTile = variants.find(v => v.tileKey === technology.tileKey);
  const board: CoachBoardControls = {
    enabled: !!ready,
    targets: ready && snapshot ? snapshot.candidates.flatMap((_, i) => coordinates(i)) : [],
    onHex: pickHex, onAction: pickAction, onTypes: pickTypes, onTech: pickTech, onTrack: pickTrack,
    techMode: !ready ? null : selectedTile && !selectedTile.fixedTrack ? 'track'
      : selected !== null && variants.length ? 'tile' : null,
    standardTiles: ready ? variants.filter(v => !v.advanced && v.tileId !== null).map(v => v.tileId!) : [],
    advancedTracks: ready ? variants.filter(v => v.advanced).flatMap(v => {
      const c = v.candidate.action.tech_tile_choice ?? v.candidate.action.choice;
      return c && typeof c === 'object' && 'track' in c ? [c.track as ResearchTrack] : [];
    }) : [],
    advancedTiles: ready ? variants.filter(v => v.advanced && v.tileId !== null).map(v => v.tileId!) : [],
    researchTracks: variants.filter(v => v.tileKey === technology.tileKey && !v.fixedTrack && v.track !== 'none').map(v => v.track as ResearchTrack),
    boosterSelection: !!snapshot?.candidates.some(c => typeof c.action.booster_id === 'number'),
    federationSelection: !!snapshot?.candidates.some(c => c.action.type === 'FormFederation'),
  };
  const focusedGroups = boardChoices === null ? [] : groups.filter(g => g.indices.some(i => boardChoices.includes(i)));
  function score(i: number) {
    const value = rec?.scores[i];
    return !value ? '미평가' : value.excluded ? '교사 제외' : value.value.toFixed(2);
  }
  const highlight = snapshot ? replayHighlight({ decision_id: snapshot.decision_id, player: snapshot.player,
    action: rec ? snapshot.candidates[rec.index].action : null,
    legal_action_count: snapshot.candidates.length, legal_federation_count: 0,
    event_end: 0, state: snapshot.state }, { decision_id: snapshot.decision_id, player: snapshot.player,
    action: null, legal_action_count: 0, legal_federation_count: 0, event_end: 0, state: snapshot.state }) : null;
  if (highlight && snapshot && rec) {
    const ai = snapshot.candidates[rec.index];
    const tech = technologyVariants([ai], 0, snapshot.state)[0];
    if (tech?.tileId != null) (tech.advanced ? highlight.advancedTech : highlight.standardTech).add(tech.tileId);
    const trackKeys: Record<string, string> = { Terraforming: 'terraforming', Navigation: 'navigation',
      ArtificialIntelligence: 'ai', GaiaProject: 'gaia', Economy: 'economy', Science: 'science' };
    const track = tech?.track ?? ai.action.track;
    if (typeof track === 'string' && trackKeys[track]) highlight.research.add(trackKeys[track]);
    coordinates(rec.index).forEach(c => highlight.hexes.add(`${c.q},${c.r}`));
    highlight.label = `AI 추천: ${highlight.label}`;
  }

  const panel = <section className="coach-panel" aria-label="AI 교정 패널">
    <header><span className="coach-eyebrow">네 좌석 · 매 수 확인</span><h1>AI 교정 대국</h1>
      <p>승인하기 전에는 어떤 좌석도 행동하지 않습니다.</p></header>
    {data && <>
      <div className="coach-position"><strong>{factionDisplayName(actor?.faction)}</strong>
        <span>{snapshot?.state.round === 0 ? '초기 배치' : `${snapshot?.state.round}라운드`} · {data.recorded}수</span></div>
      {actor && <p className="coach-resources">광석 {actor.resources.ore} · 돈 {actor.resources.credits}
        {' · '}지식 {actor.resources.knowledge} · QIC {actor.resources.qic}</p>}
      <p role="status">{data.status === 'ready' ? '추천 완료 · 사용자 확인 대기'
        : data.status === 'complete' ? '대국 종료 · 기록 보존'
          : data.status === 'error' ? '추천 오류 · 현재 수 보존' : 'AI가 추천을 계산 중입니다. 보드는 그대로입니다.'}</p>
    </>}
    {(error || data?.error) && <p className="coach-error" role="alert">{error ?? data?.error}</p>}
    {data?.status === 'error' && <button disabled={busy} onClick={() => void command('retry', {})}>추천 다시 계산</button>}
    {rec && <>
      <section className="coach-board-instructions" aria-label="보드 직접 선택">
        <strong>보드에서 직접 선택</strong>
        <p className="coach-ai-legend">★ 노란색 = AI 추천 · 하늘색 행성 테두리 = 선택 가능</p>
        <p>건물·행성, 개인 행동 타일, 연구 트랙·파워 액션을 누르세요. 클릭은 선택만 합니다.</p>
        <div className="coach-board-shortcuts">
          <button onClick={() => scrollBoard('game-map')}>건물·행성</button>
          <button onClick={() => scrollBoard('game-player-actions')}>내 행동 타일</button>
          <button onClick={() => scrollBoard('game-research')}>기술·연구·파워</button>
        </div>
        {boardMessage && <p role="status">{boardMessage}</p>}
        {(selected !== null || boardChoices !== null || technology.tileKey) && <button onClick={() => {
          setSelected(null); setTechnology(EMPTY_TECHNOLOGY); setBoardChoices(null); setBoardMessage('다른 건물·행동·연구 트랙을 고르세요.');
        }}>보드 선택 취소</button>}
        {snapshot && boardChoices !== null && <BoardChoices state={snapshot.state} faction={actor?.faction ?? null}
          choices={focusedGroups.map(g => ({ index: g.index, candidate: baseCandidate(snapshot.candidates[g.index]) }))}
          recommended={groups.find(g => g.indices.includes(rec.index))?.index}
          onChoose={chooseBase} />}
      </section>
      {snapshot && <details><summary>모든 합법 행동 · 클릭해서 선택 ({groups.length}개)</summary>
        <BoardChoices state={snapshot.state} faction={actor?.faction ?? null}
          choices={groups.map(g => ({ index: g.index, candidate: baseCandidate(snapshot.candidates[g.index]) }))}
          recommended={groups.find(g => g.indices.includes(rec.index))?.index} onChoose={chooseBase} />
      </details>}
      {actor && <details><summary>자원 변환 · 아이콘으로 선택</summary>
        <SidebarTurnControls player={actor} isMyTurn={!!ready}
          onFreeAction={kind => pickAction({ type: 'FreeAction', kind, count: 1 })} />
      </details>}
      <section className="coach-suggestion" aria-label="AI 최종 추천">
        <h2>AI 최종 추천</h2><p>{labels[rec.index]}</p>
        <p className="coach-track-result">{snapshot && technologySummary(snapshot.candidates[rec.index], snapshot.state)}</p>
        <strong>1차 평가 {score(rec.index)}</strong>
        <p className="coach-muted">{rec.audit.ranking_mode} · {rec.audit.value_model}
          {typeof rec.audit.timing?.seconds === 'number' && ` · ${rec.audit.timing.seconds.toFixed(1)}초`}</p>
        <p className="coach-muted">평가값은 실제 승점이 아닙니다. 탐색 후 추천은 1차 점수 순위와 다를 수 있습니다.</p>
        <button disabled={!ready} onClick={() => chooseBase(rec.index)}>AI 추천 수 선택</button>
      </section>
      <details className="coach-text-fallback"><summary>전체 합법 행동 · 텍스트 목록 (보조)</summary>
      <label>다른 합법 행동 찾기<input value={filter} onChange={e => setFilter(e.target.value)}
        placeholder="예: 연구소, 항해, 7번 섹터" /></label>
      <label>1. 행동 선택 · {candidates.length}/{groups.length}개 행동 · {labels.length}개 합법 조합
        <select aria-label="합법 행동 선택" size={7} value={groups.find(g => baseIndex !== null && g.indices.includes(baseIndex))?.index ?? ''} disabled={!ready}
          onChange={e => chooseBase(Number(e.target.value))}>
          {candidates.map(c => <option key={c.index} value={c.index}>
            {c.indices.includes(rec.index) ? '★ ' : ''}[{c.technology ? '기술별 평가' : score(c.index)}] {c.label}
          </option>)}
        </select>
      </label>
      </details>
      {variants.length > 0 && snapshot && <TechnologyPicker variants={variants} selection={technology}
        onChange={setTechnology} state={snapshot.state} disabled={!ready} />}
      {variants.length > 0 && index === null && <p role="status">기술과 필요한 트랙·대상을 직접 선택해야 실행할 수 있습니다.</p>}
      {chosen && <div className="coach-chosen"><h2>{override ? '사용자 선택' : '선택된 추천 수'}</h2>
        <p>{index !== null && labels[index]}</p><strong>1차 평가 {index !== null && score(index)}</strong>
        <p className="coach-track-result">{snapshot && technologySummary(chosen, snapshot.state)}</p>
        {selectedScore?.excluded && <p>교사 제한 대상이지만 엔진상 합법입니다. 이유를 기록하고 선택할 수 있습니다.</p>}
        <details><summary>평가 근거 · 정확한 행동 매개변수</summary>
          <p>{selectedScore?.reason}</p><pre>{JSON.stringify(chosen.action, null, 2)}</pre>
          <p>최종 추천 경로: {rec.audit.selected ?? '기록 없음'}</p>
        </details>
      </div>}
      {override && <button onClick={() => setFeedbackOpen(true)}>{reason.trim() && plan.trim() ? '선택 이유·계획 확인' : '선택 이유·계획 입력'}</button>}
      {feedbackOpen && override && <FeedbackDialog reason={reason} plan={plan} setReason={setReason} setPlan={setPlan}
        onClose={() => setFeedbackOpen(false)} />}
      <button className="coach-confirm" disabled={!canSubmit} onClick={() => {
        if (canSubmit && snapshot && index !== null) void command('approve', {
          decision_id: snapshot.decision_id, index, reason: override ? reason : '', plan: override ? plan : '',
          ...(variants.length ? { technology_confirmed: true } : {}),
        });
      }}>{busy ? '기록·실행 중…' : override ? '이유 저장 후 이 수 실행' : 'AI 추천 승인 · 한 수 실행'}</button>
    </>}
    {data && <footer><p>승인 {data.recorded}수 · 다른 선택 {data.corrections}건</p>
      {data.last_feedback?.controller === 'human_override' && <details><summary>최근 교정 기록</summary>
        <p>{data.last_feedback.reason}</p><p>다음 계획: {data.last_feedback.plan}</p></details>}
      <a href="/coach-api/record" download="coaching-record.json">대국·교정 기록 다운로드</a>
      <p className="coach-muted">자동 학습·가중치 변경 없음. AI 추천 승인과 사용자 교정을 구분해 저장합니다.</p>
      <details><summary>테스트 설정</summary><p>{data.config.seed}</p>
        <p>B 평가: {data.config.delta_factions.join(', ')} · 나머지는 기존 A</p>
        <p>{data.config.clock?.uses_per_seat === 0
          ? `추천 최대 ${data.config.clock.long_seconds}초 · 자동 연장 없음`
          : `기본 ${data.config.clock?.target_seconds ?? 10}초 · 긴 고민 최대 ${data.config.clock?.long_seconds ?? 120}초, 좌석별 ${data.config.clock?.uses_per_seat ?? 6}회`}</p></details>
    </footer>}
  </section>;

  return <div className="ai-coach">
    {snapshot ? <ReplayHighlightContext.Provider value={highlight}>
      <App replay={{ events: snapshot.state.event_log ?? [], eventStart: 0,
        eventEnd: snapshot.state.event_log?.length ?? 0, onEventSelect: () => {} }} sidePanel={panel} coach={board} />
    </ReplayHighlightContext.Provider> : <div className="coach-loading">{panel}<p>로컬 교정 대국을 불러오는 중…</p></div>}
  </div>;
}
