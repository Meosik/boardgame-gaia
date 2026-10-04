import { Component, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { App } from '../../App';
import { useGameStore } from '../../store/gameStore';
import { FACTION_DISPLAY_NAMES } from '../../displayNames';
import type { FactionId, PlayerId } from '../../types/game';
import { POLICY_NAMES, frameForEvent, loadReplay, parseCatalog, type ReplayGame, type ReplayRecord } from '../../replay/records';
import './replay.css';
import { replayScrollTarget, scrollReplayTargetIntoView } from '../../replay/navigation';
import { replayRoundStarts } from '../../replay/stepping';
import { adjacentReplayPosition, buildReplaySettlement, settlementRewards, settlementState } from '../../replay/settlement';
import { replayRewardBatches } from '../../replay/rewards';
import { RewardMotion } from '../RewardMotion';
import { useLiveReplays } from '../../replay/useLiveReplays';

import { ReplayHighlightContext, replayHighlight } from '../../replay/highlight';

const SPEEDS = [0.5, 1, 2, 4];
const SHORT_POLICY_NAMES: Record<string, string> = {
  CurrentActionTeacher: 'AT', ResearchPlanTeacher: 'RP', ResourcePlanTeacher: 'XP', teacher: 'T',
};

class ReplayBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed ? <p role="alert">리플레이 화면을 표시할 수 없습니다. 다른 기록을 선택해 주세요.</p> : this.props.children;
  }
}

function publicationLabels(value: unknown): Map<string, string> {
  const labels = new Map<string, string>();
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return labels;
  const format = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Seoul', month: 'numeric', day: 'numeric',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  });
  for (const [id, seconds] of Object.entries(value)) {
    // Automatic eval IDs have recorded publication dates; legacy entries may
    // only have a later retention-clock start, not their original publication.
    if (!id.startsWith('eval-')) continue;
    if (typeof seconds !== 'number' || seconds < 0) continue;
    const date = new Date(seconds * 1000);
    if (!Number.isFinite(date.getTime())) continue;
    const parts = Object.fromEntries(format.formatToParts(date).map(part => [part.type, part.value]));
    labels.set(id, `${parts.month}/${parts.day} ${parts.hour}:${parts.minute}`);
  }
  return labels;
}

function gameLabel(game: ReplayGame, registeredAt?: string): string {
  const policy = SHORT_POLICY_NAMES[game.policy] ?? POLICY_NAMES[game.policy] ?? game.policy;
  const faction = FACTION_DISPLAY_NAMES[game.faction as FactionId] ?? game.faction;
  const name = `${policy} · ${faction} ${game.vp}점`;
  return registeredAt ? `${name} · ${registeredAt}` : name;
}

export function AiReplay() {
  const [savedGames, setGames] = useState<ReplayGame[]>([]);
  const [registeredAt, setRegisteredAt] = useState<ReadonlyMap<string, string>>(() => new Map());
  const [factionFilter, setFactionFilter] = useState('all');
  const [selected, setSelected] = useState('');
  const [followLive, setFollowLive] = useState(true);
  const live = useLiveReplays(selected);
  const latestLiveGame = live.games.find(game => game.status === 'running') ?? live.games[0];
  const games = useMemo(() => [...live.games, ...savedGames], [live.games, savedGames]);
  const liveGame = live.games.find(game => game.id === selected);
  const liveStatus = live.record?.metadata.live_status ?? liveGame?.status;
  const selectedSaved = savedGames.find(game => game.id === selected);
  const liveSelection = useRef('');
  const [actionPlayer, setActionPlayer] = useState<PlayerId | null>(null);
  const [record, setRecord] = useState<ReplayRecord | null>(null);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [motion, setMotion] = useState<{ cursor: number; id: number } | null>(null);
  const [motionReady, setMotionReady] = useState<{ frame: ReplayRecord['frames'][number]; cursor: number } | null>(null);
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
    // Optional historical registration dates must never delay or block playback.
    fetch('/ai-replays/publication-times.json', { signal: controller.signal, cache: 'no-cache' })
      .then(response => response.ok ? response.json() as Promise<unknown> : null)
      .then(value => { if (!controller.signal.aborted) setRegisteredAt(publicationLabels(value)); })
      .catch(() => {});
    fetch('/ai-replays/index.json', { signal: controller.signal, cache: 'no-cache' })
      .then(response => { if (!response.ok) throw new Error('AI 리플레이 목록을 불러오지 못했습니다.'); return response.json() as Promise<unknown>; })
      .then(value => {
        const catalog = parseCatalog(value);
        setGames(catalog);
        if (catalog.length) setSelected(value => value || catalog[0].id);
        else { setLoading(false); setError('저장된 AI 리플레이가 없습니다.'); }
      })
      .catch((e: unknown) => { if (!controller.signal.aborted) { setLoading(false); setError(e instanceof Error ? e.message : '목록 읽기 실패'); } });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (followLive && latestLiveGame && selected !== latestLiveGame.id) {
      setFactionFilter('all');
      setSelected(latestLiveGame.id);
    }
  }, [selected, latestLiveGame, followLive]);

  useEffect(() => {
    liveSelection.current = '';
    setRecord(null); setLoading(true); setError(null); setPlaying(false); setCursor(0);
    setActionPlayer(null); setMotion(null);
  }, [selected]);

  useEffect(() => {
    if (!live.record || live.record.gameId !== selected) return;
    setRecord(live.record); setLoading(false); setError(null);
    if (liveSelection.current !== selected) {
      liveSelection.current = selected;
      setCursor(live.record.frames.length - 1);
      setPlaying(live.record.metadata.live_status === 'running');
    } else if (live.record.metadata.live_status === 'failed') {
      setPlaying(false);
    }
  }, [live.record, selected]);

  useEffect(() => {
    const game = selectedSaved;
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
  }, [selectedSaved, selected]);

  const settlement = useMemo(() => record ? buildReplaySettlement(record) : { steps: [], events: [] }, [record]);
  const lastAction = record ? record.frames.length - 1 : 0;
  const maxCursor = lastAction + settlement.steps.length;
  const sourceCursor = Math.min(cursor, lastAction);
  const frame = record?.frames[sourceCursor];
  const step = settlement.steps[cursor - lastAction - 1];
  const roundStarts = useMemo(() => replayRoundStarts(record?.frames ?? []), [record]);
  const previousAction = record ? adjacentReplayPosition(record.frames, cursor, -1, actionPlayer, settlement.steps.length) : null;
  const nextAction = record ? adjacentReplayPosition(record.frames, cursor, 1, actionPlayer, settlement.steps.length) : null;
  const waitingForLive = !!liveGame && liveStatus === 'running';
  const canPlay = !!record && (nextAction !== null || waitingForLive);
  useLayoutEffect(() => {
    if (!record || !frame) return;
    actions.setReadOnly(true);
    actions.setMyPlayerId(record.metadata.focus_player);
    const state = step ? settlementState(frame.state, step) : frame.state;
    actions.setGameState({ ...state, event_log: settlement.events.slice(0, step?.eventEnd ?? frame.event_end) });
  }, [record, frame, step, settlement, actions]);

  useEffect(() => {
    if (!playing || !record) return;
    if (nextAction === null) { if (!waitingForLive) setPlaying(false); return; }
    const timer = window.setTimeout(() => advance(nextAction), 1000 / speed);
    return () => window.clearTimeout(timer);
  }, [playing, cursor, speed, record, nextAction, actionPlayer, waitingForLive]);

  function goLive() {
    if (!latestLiveGame) return;
    setFollowLive(true);
    setFactionFilter('all');
    setActionPlayer(null);
    setMotion(null);
    if (selected !== latestLiveGame.id) {
      setSelected(latestLiveGame.id);
      return;
    }
    if (!record) return;
    setCursor(lastAction);
    setPlaying(liveStatus === 'running');
  }

  function togglePlaying() {
    setFollowLive(!playing && !!liveGame && liveStatus === 'running' && actionPlayer === null);
    setPlaying(value => !value);
  }

  function seek(value: number) {
    if (!record) return;
    setFollowLive(false);
    setPlaying(false);
    setMotion(null);
    setCursor(Math.max(0, Math.min(value, maxCursor)));
  }

  function advance(value: number) {
    setMotion({ cursor: value, id: ++motionSequence.current });
    setCursor(value);
  }

  function changeSpeed(value: number) {
    setMotion(null);
    setSpeed(value);
  }

  const previous = record?.frames[Math.max(0, sourceCursor - 1)];
  useEffect(() => {
    if (!frame) return;
    // The store update above commits the board before resolving its move highlights.
    const request = requestAnimationFrame(() => {
      if (!root.current) return;
      const target = !step ? replayScrollTarget(root.current, frame, previous)
        : step.kind === 'goal' ? root.current.querySelector('#game-round-boosters')
          : step.kind === 'research' ? root.current.querySelector('#game-research') : null;
      if (target) scrollReplayTargetIntoView(target, root.current);
      setMotionReady({ frame, cursor });
    });
    return () => cancelAnimationFrame(request);
  }, [frame, previous, cursor, step]);

  const motionBatches = useMemo(() => record && motion?.cursor === cursor && motionReady?.frame === frame
    && motionReady?.cursor === cursor && speed < 2
    ? step ? settlementRewards(step, motion.id) : replayRewardBatches(record, cursor, motion.id) : [],
  [record, cursor, frame, step, motion, motionReady, speed]);

  useEffect(() => {
    function keydown(event: KeyboardEvent) {
      if (!record || event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || event.isComposing) return;
      const target = event.target;
      if (target instanceof Element && target.closest('input, select, textarea, button, a, [contenteditable]:not([contenteditable="false"]), [role="textbox"], [role="dialog"]')) return;
      if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', ' '].includes(event.key)) return;
      event.preventDefault();
      if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
        setFollowLive(false);
        setPlaying(false);
        const targetFrame = event.key === 'ArrowRight' ? nextAction : previousAction;
        if (targetFrame !== null) {
          if (event.key === 'ArrowRight') advance(targetFrame);
          else seek(targetFrame);
        }
      } else if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
        setMotion(null);
        setSpeed(value => SPEEDS[Math.max(0, Math.min(SPEEDS.indexOf(value) + (event.key === 'ArrowUp' ? 1 : -1), SPEEDS.length - 1))]);
      } else if (!event.repeat && canPlay) {
        togglePlaying();
      }
    }
    window.addEventListener('keydown', keydown);
    return () => window.removeEventListener('keydown', keydown);
  }, [record, cursor, previousAction, nextAction, canPlay, playing, liveGame, liveStatus, actionPlayer]);

  const actor = frame?.state.players.find(p => p.player_id === frame.player);
  const action = frame?.action;
  const ended = cursor === maxCursor && !!frame && typeof frame.state.phase === 'object' && 'Ended' in frame.state.phase;
  const replayPlayers = record?.frames[record.frames.length - 1].state.players ?? [];
  const factions = [...new Set(games.map(g => g.faction))].sort(
    (a, b) => (FACTION_DISPLAY_NAMES[a as FactionId] ?? a).localeCompare(FACTION_DISPLAY_NAMES[b as FactionId] ?? b),
  );
  const filteredGames = factionFilter === 'all' ? games : games.filter(g => g.faction === factionFilter);
  function optionLabel(game: ReplayGame) {
    const status = live.games.find(item => item.id === game.id)?.status;
    const prefix = status === 'running' ? 'LIVE · ' : status === 'complete' ? '완료 · ' : status === 'failed' ? '중단 · ' : '';
    return prefix + gameLabel(game, registeredAt.get(game.id));
  }

  function selectFaction(faction: string) {
    setFollowLive(false);
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
              <ReplayHighlightContext.Provider value={replayHighlight(step ? { ...frame, action: null, player: null } : frame, step ? undefined : previous)}>
              <App replay={{ events: settlement.events, eventStart: step?.eventStart ?? previous?.event_end ?? 0,
                eventEnd: step?.eventEnd ?? frame.event_end,
                onEventSelect: index => {
                  const target = settlement.steps.findIndex(s => index >= s.eventStart && index < s.eventEnd);
                  seek(target >= 0 ? lastAction + 1 + target : frameForEvent(record.frames, index));
                } }} />
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
            onChange={event => { setFollowLive(false); setPlaying(false); setRecord(null); setSelected(event.target.value); }}>
            {filteredGames.map(game => <option key={game.id} value={game.id}>
              {optionLabel(game)}
            </option>)}
          </select></label>
          <label>행동 보기 <select aria-label="행동 종족" value={actionPlayer ?? 'all'} disabled={!record}
            onChange={event => { setFollowLive(false); setPlaying(false); setMotion(null); setActionPlayer(event.target.value === 'all' ? null : Number(event.target.value)); }}>
            <option value="all">전체 행동</option>
            {replayPlayers.map(player => <option key={player.player_id} value={player.player_id}>
              {FACTION_DISPLAY_NAMES[player.faction as FactionId] ?? player.nickname}
            </option>)}
          </select></label>
          <label>라운드 <select aria-label="라운드 선택" value={frame?.state.round || ''} disabled={!record || !roundStarts.length}
            onChange={event => {
              const start = roundStarts.find(item => item.round === Number(event.target.value));
              if (start) seek(start.cursor);
            }}>
            <option value="" disabled>{record ? '초기 배치' : '라운드'}</option>
            {roundStarts.map(item => <option key={item.round} value={item.round}>{item.round}라운드</option>)}
          </select></label>
          <button type="button" onClick={() => previousAction !== null && seek(previousAction)} disabled={previousAction === null}>이전 행동</button>
          <button type="button" onClick={togglePlaying} disabled={!canPlay} aria-pressed={playing}>
            {playing ? '정지' : '재생'}
          </button>
          <button type="button" onClick={() => { setFollowLive(false); setPlaying(false); if (nextAction !== null) advance(nextAction); }} disabled={nextAction === null}>다음 행동</button>
          {liveGame && <>
            <button type="button" onClick={goLive} disabled={!record}
              aria-pressed={playing && cursor === lastAction && actionPlayer === null}>
              LIVE · 최신 수
            </button>
            <span role="status" aria-label="실시간 연결 상태">{live.error ?? (liveStatus === 'complete' ? '대전 종료'
              : liveStatus === 'failed' ? '기록 중단 · 마지막 수 보존'
                : cursor === lastAction ? playing ? '최신 수 · 새 행동 대기' : '최신 수 · 정지'
                  : `${lastAction - Math.min(cursor, lastAction)}수 뒤`)}</span>
          </>}
          <label>배속 <select aria-label="재생 배속" value={speed} onChange={event => changeSpeed(Number(event.target.value))}>
            {SPEEDS.map(value => <option key={value} value={value}>{value}×</option>)}
          </select></label>
        </div>
        <div className="ai-replay-position">
          <label htmlFor="ai-replay-position">{sourceCursor} / {lastAction} 행동{step ? ` · 정산 ${cursor - lastAction}/${settlement.steps.length}` : ''}</label>
          <input id="ai-replay-position" aria-label="행동 시점" type="range" min={0} max={maxCursor}
            value={cursor} disabled={!record} onChange={event => seek(Number(event.target.value))} />
          <span>{step ? '종료 정산' : frame ? frame.state.round === 0 ? '초기 배치' : `${frame.state.round}라운드` : ''}{ended ? ' · 게임 종료' : record && actionPlayer !== null && nextAction === null ? ' · 선택 종족의 남은 행동 없음' : ''}</span>
        </div>
        <div className="ai-replay-status" role="status" data-settlement-kind={step?.kind}>
          {step ? <><b>{step.title}</b>{step.awards.map(award => {
            const player = frame?.state.players.find(p => p.player_id === award.player);
            return <span key={award.player}>{FACTION_DISPLAY_NAMES[player?.faction as FactionId] ?? player?.nickname}: {award.detail}
              {' · '}{award.amount > 0 ? '+' : ''}{award.amount}점 · 누적 <b>{award.total}점</b></span>;
          })}</> : action ? <><b>{actor ? `${FACTION_DISPLAY_NAMES[actor.faction as FactionId] ?? actor.nickname}: ` : ''}{replayHighlight(frame!, previous).label}</b>
            <span>행동 후 상태 · 행동 전 연방 후보 <b>{frame?.legal_federation_count ?? 0}개</b>
              {action.type === 'FormFederation' ? ' · 연방 선택' : (frame?.legal_federation_count ?? 0) > 0 ? ' · 다른 행동 선택' : ''}</span></>
            : '초기 상태 · 게임 행동을 실행하지 않는 관찰 화면입니다.'}
          {settlement.warning && <span role="alert">{settlement.warning}</span>}
        </div>
      </footer>
    </div>
  );
}
