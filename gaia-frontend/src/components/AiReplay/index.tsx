import { Component, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { App } from '../../App';
import { useGameStore } from '../../store/gameStore';
import { FACTION_DISPLAY_NAMES } from '../../displayNames';
import type { FactionId, PlayerId } from '../../types/game';
import { POLICY_NAMES, frameForEvent, loadReplay, parseCatalog, type ReplayGame, type ReplayRecord } from '../../replay/records';
import './replay.css';
import { replayScrollTarget } from '../../replay/navigation';
import { adjacentReplayFrame } from '../../replay/stepping';
import { replayRewardBatches } from '../../replay/rewards';
import { RewardMotion } from '../RewardMotion';

import { ReplayHighlightContext, replayHighlight } from '../../replay/highlight';

const SPEEDS = [0.5, 1, 2, 4];

class ReplayBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed ? <p role="alert">리플레이 화면을 표시할 수 없습니다. 다른 기록을 선택해 주세요.</p> : this.props.children;
  }
}

function gameLabel(game: ReplayGame): string {
  return `${POLICY_NAMES[game.policy] ?? game.policy} · ${FACTION_DISPLAY_NAMES[game.faction as FactionId] ?? game.faction} · ${game.seed.split('-').slice(-1)[0]} · ${game.vp}점`;
}

export function AiReplay() {
  const [games, setGames] = useState<ReplayGame[]>([]);
  const [factionFilter, setFactionFilter] = useState('all');
  const [selected, setSelected] = useState('');
  const [actionPlayer, setActionPlayer] = useState<PlayerId | null>(null);
  const [record, setRecord] = useState<ReplayRecord | null>(null);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [motion, setMotion] = useState<{ cursor: number; id: number } | null>(null);
  const [motionReady, setMotionReady] = useState<ReplayRecord['frames'][number] | null>(null);
  const motionSequence = useRef(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const actions = useGameStore(s => s.actions);
  const root = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    actions.setReadOnly(true);
    return () => actions.reset();
  }, [actions]);

  useEffect(() => {
    const controller = new AbortController();
    fetch('/ai-replays/index.json', { signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error('AI 리플레이 목록을 불러오지 못했습니다.'); return response.json() as Promise<unknown>; })
      .then(value => {
        const catalog = parseCatalog(value);
        setGames(catalog);
        if (catalog.length) setSelected(catalog[0].id);
        else { setLoading(false); setError('저장된 AI 리플레이가 없습니다.'); }
      })
      .catch((e: unknown) => { if (!controller.signal.aborted) { setLoading(false); setError(e instanceof Error ? e.message : '목록 읽기 실패'); } });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const game = games.find(g => g.id === selected);
    if (!game) return;
    const controller = new AbortController();
    setRecord(null); setLoading(true); setError(null); setPlaying(false); setCursor(0); setActionPlayer(null); setMotion(null);
    loadReplay(game.file, controller.signal)
      .then(replay => {
        if (controller.signal.aborted) return;
        if (replay.metadata.seed !== game.seed || replay.metadata.policy !== game.policy || replay.metadata.steps !== game.steps) {
          throw new Error('리플레이와 목록 정보가 다릅니다.');
        }
        setRecord(replay); setLoading(false);
      })
      .catch((e: unknown) => { if (!controller.signal.aborted) { setLoading(false); setError(e instanceof Error ? e.message : '기록 읽기 실패'); } });
    return () => controller.abort();
  }, [games, selected]);

  const frame = record?.frames[cursor];
  const previousAction = record ? adjacentReplayFrame(record.frames, cursor, -1, actionPlayer) : null;
  const nextAction = record ? adjacentReplayFrame(record.frames, cursor, 1, actionPlayer) : null;
  useLayoutEffect(() => {
    if (!record || !frame) return;
    actions.setReadOnly(true);
    actions.setMyPlayerId(record.metadata.focus_player);
    actions.setGameState({ ...frame.state, event_log: record.events.slice(0, frame.event_end) });
  }, [record, frame, actions]);

  useEffect(() => {
    if (!playing || !record) return;
    if (nextAction === null) { setPlaying(false); return; }
    const timer = window.setTimeout(() => advance(nextAction), 1000 / speed);
    return () => window.clearTimeout(timer);
  }, [playing, cursor, speed, record, nextAction, actionPlayer]);

  function seek(value: number) {
    if (!record) return;
    setPlaying(false);
    setMotion(null);
    setCursor(Math.max(0, Math.min(value, record.frames.length - 1)));
  }

  function advance(value: number) {
    setMotion({ cursor: value, id: ++motionSequence.current });
    setCursor(value);
  }

  function changeSpeed(value: number) {
    setMotion(null);
    setSpeed(value);
  }

  const previous = record?.frames[Math.max(0, cursor - 1)];
  useEffect(() => {
    if (!frame) return;
    // The store update above commits the board before resolving its move highlights.
    const request = requestAnimationFrame(() => {
      if (!root.current) return;
      replayScrollTarget(root.current, frame, previous)?.scrollIntoView?.({ behavior: 'instant', block: 'nearest', inline: 'nearest' });
      setMotionReady(frame);
    });
    return () => cancelAnimationFrame(request);
  }, [frame, previous]);

  const motionBatches = useMemo(() => record && motion?.cursor === cursor && motionReady === frame && speed < 2
    ? replayRewardBatches(record, cursor, motion.id) : [], [record, cursor, frame, motion, motionReady, speed]);

  useEffect(() => {
    function keydown(event: KeyboardEvent) {
      if (!record || event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || event.isComposing) return;
      const target = event.target;
      if (target instanceof Element && target.closest('input, select, textarea, button, a, [contenteditable]:not([contenteditable="false"]), [role="textbox"], [role="dialog"]')) return;
      if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', ' '].includes(event.key)) return;
      event.preventDefault();
      if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
        setPlaying(false);
        const targetFrame = event.key === 'ArrowRight' ? nextAction : previousAction;
        if (targetFrame !== null) {
          if (event.key === 'ArrowRight') advance(targetFrame);
          else seek(targetFrame);
        }
      } else if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
        setMotion(null);
        setSpeed(value => SPEEDS[Math.max(0, Math.min(SPEEDS.indexOf(value) + (event.key === 'ArrowUp' ? 1 : -1), SPEEDS.length - 1))]);
      } else if (!event.repeat && nextAction !== null) {
        setPlaying(value => !value);
      }
    }
    window.addEventListener('keydown', keydown);
    return () => window.removeEventListener('keydown', keydown);
  }, [record, cursor, previousAction, nextAction]);

  const actor = frame?.state.players.find(p => p.player_id === frame.player);
  const action = frame?.action;
  const ended = !!record && cursor === record.frames.length - 1;
  const replayPlayers = record?.frames[record.frames.length - 1].state.players ?? [];
  const factions = [...new Set(games.map(g => g.faction))].sort(
    (a, b) => (FACTION_DISPLAY_NAMES[a as FactionId] ?? a).localeCompare(FACTION_DISPLAY_NAMES[b as FactionId] ?? b),
  );
  const filteredGames = factionFilter === 'all' ? games : games.filter(g => g.faction === factionFilter);

  function selectFaction(faction: string) {
    setFactionFilter(faction);
    const nextGames = faction === 'all' ? games : games.filter(g => g.faction === faction);
    if (nextGames.length && !nextGames.some(g => g.id === selected)) {
      setPlaying(false); setRecord(null); setSelected(nextGames[0].id);
    }
  }

  return (
    <div className="ai-replay" ref={root}>
      <div className="ai-replay-board">
        {error ? <p className="ai-replay-message" role="alert">{error}</p>
          : loading || !record || !frame ? <p className="ai-replay-message" role="status">AI 리플레이를 불러오는 중...</p>
            : <ReplayBoundary key={selected}>
              <ReplayHighlightContext.Provider value={replayHighlight(frame, previous)}>
              <App replay={{ events: record.events, eventStart: previous?.event_end ?? 0, eventEnd: frame.event_end,
                onEventSelect: index => seek(frameForEvent(record.frames, index)) }} />
              {motionBatches.map(batch => <RewardMotion key={`${batch.id}-${batch.player}`} batch={batch} duration={400 / speed} />)}
              </ReplayHighlightContext.Provider>
            </ReplayBoundary>}
      </div>
      <footer className="ai-replay-controls" aria-label="AI 리플레이 재생바" title="←/→ 이전·다음 행동 · ↑/↓ 재생 속도 · Space 재생·정지">
        <div className="ai-replay-buttons">
          <strong>AI 복기 · 읽기 전용</strong>
          <label>종족 <select aria-label="종족 필터" value={factionFilter} disabled={!games.length}
            onChange={event => selectFaction(event.target.value)}>
            <option value="all">전체</option>
            {factions.map(faction => (
              <option key={faction} value={faction}>{FACTION_DISPLAY_NAMES[faction as FactionId] ?? faction}</option>
            ))}
          </select></label>
          <label>게임 <select aria-label="리플레이 게임" value={selected} disabled={!filteredGames.length}
            onChange={event => { setPlaying(false); setRecord(null); setSelected(event.target.value); }}>
            {filteredGames.map(game => <option key={game.id} value={game.id}>{gameLabel(game)}</option>)}
          </select></label>
          <label>행동 보기 <select aria-label="행동 종족" value={actionPlayer ?? 'all'} disabled={!record}
            onChange={event => { setPlaying(false); setMotion(null); setActionPlayer(event.target.value === 'all' ? null : Number(event.target.value)); }}>
            <option value="all">전체 행동</option>
            {replayPlayers.map(player => <option key={player.player_id} value={player.player_id}>
              {FACTION_DISPLAY_NAMES[player.faction as FactionId] ?? player.nickname}
            </option>)}
          </select></label>
          <button type="button" onClick={() => previousAction !== null && seek(previousAction)} disabled={previousAction === null}>이전 행동</button>
          <button type="button" onClick={() => setPlaying(value => !value)} disabled={nextAction === null} aria-pressed={playing}>
            {playing ? '정지' : '재생'}
          </button>
          <button type="button" onClick={() => { setPlaying(false); if (nextAction !== null) advance(nextAction); }} disabled={nextAction === null}>다음 행동</button>
          <label>배속 <select aria-label="재생 배속" value={speed} onChange={event => changeSpeed(Number(event.target.value))}>
            {SPEEDS.map(value => <option key={value} value={value}>{value}×</option>)}
          </select></label>
        </div>
        <div className="ai-replay-position">
          <label htmlFor="ai-replay-position">{cursor} / {record ? record.frames.length - 1 : 0} 행동</label>
          <input id="ai-replay-position" aria-label="행동 시점" type="range" min={0} max={record ? record.frames.length - 1 : 0}
            value={cursor} disabled={!record} onChange={event => seek(Number(event.target.value))} />
          <span>{frame ? frame.state.round === 0 ? '초기 배치' : `${frame.state.round}라운드` : ''}{ended ? ' · 게임 종료' : record && actionPlayer !== null && nextAction === null ? ' · 선택 종족의 남은 행동 없음' : ''}</span>
        </div>
        <div className="ai-replay-status" role="status">
          {action ? <><b>{actor ? `${FACTION_DISPLAY_NAMES[actor.faction as FactionId] ?? actor.nickname}: ` : ''}{replayHighlight(frame!, previous).label}</b>
            <span>행동 후 상태 · 행동 전 연방 후보 <b>{frame?.legal_federation_count ?? 0}개</b>
              {action.type === 'FormFederation' ? ' · 연방 선택' : (frame?.legal_federation_count ?? 0) > 0 ? ' · 다른 행동 선택' : ''}</span></>
            : '초기 상태 · 게임 행동을 실행하지 않는 관찰 화면입니다.'}
        </div>
      </footer>
    </div>
  );
}
