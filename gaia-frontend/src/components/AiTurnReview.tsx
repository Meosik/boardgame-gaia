import { useEffect, useState } from 'react';
import { api } from '../api/rest';
import { hintLabel } from './TeacherHint';
import type { AiHold, AiPastTurn, GameState, PlayerId } from '../types/game';

interface Props {
  roomCode: string;
  sessionToken: string;
  /** The live position (never a reviewed earlier one): the hold belongs to it. */
  state: GameState;
}

/** Where the turn on screen came from: the teacher's own choice, a new search without the
 * rejected move (first rejection), or a spare kept from that search (later rejections — only the
 * turn's first move is the spare, every move after it is searched again). */
export function aiHoldOrigin(hold: AiHold): string {
  if (hold.rejections === 0) return '교사의 첫 선택';
  if (hold.rejections === 1) return '거절한 수를 빼고 다시 탐색한 수';
  return hold.turn.decisions.length > 1
    ? '보관해 둔 예비 수(새 탐색 없음) — 첫 수만 예비이고 이어진 수는 새로 탐색'
    : '보관해 둔 예비 수(새 탐색 없음)';
}

/** What another rejection would use: a new search, a spare, or — with no spare left — the
 * player, who then plays the turn in the seat's place. */
export function aiHoldSpares(hold: AiHold): string {
  if (hold.spares_left === null || hold.spares_left === undefined) {
    return '거절하면 그 수를 빼고 다시 탐색합니다(예비 수 최대 3개 보관)';
  }
  return hold.spares_left > 0
    ? `남은 예비 수 ${hold.spares_left}개`
    : '남은 예비 수 없음 — 다시 거절하면 이 차례를 직접 둡니다';
}

/** The review of AI turns in an AI game: the switch (the AI seats wait after each of their
 * turns), and while they wait the finished turn's moves with 계속 / 거절. A rejected turn is
 * taken back and played again without the move that ended it; the server records the rejection.
 * Playing one's own move also lets the AI seats go on, so a turn is rejected before that.
 * It is shown in a floating box (`.ai-review-float`) on the setup screens and the game screen
 * and can be folded to one line.
 * An earlier AI turn can be rejected too (「지난 AI 차례」): the room goes back to that turn's
 * first position and everything played since — the player's own moves too — is gone, so it is
 * asked about once more before it is done. */
export function AiTurnReview({ roomCode, sessionToken, state }: Props) {
  const [available, setAvailable] = useState(false);
  const [busy, setBusy] = useState<'switch' | 'continue' | 'reject' | 'past' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [pastOpen, setPastOpen] = useState(false);
  const [past, setPast] = useState<AiPastTurn[] | null>(null);
  /** `turn.start_revision` of the earlier turn the player is asked about. */
  const [pastChosen, setPastChosen] = useState<number | null>(null);
  const pastCount = state.ai_past_turns ?? 0;
  const pastHeldAt = state.ai_hold?.revision ?? null;

  // The list is read when it is opened and again when the game has moved on.
  useEffect(() => {
    if (!pastOpen) return undefined;
    let cancelled = false;
    setPastChosen(null);
    api.aiTurns(roomCode, sessionToken)
      .then((answer) => { if (!cancelled) setPast(answer.turns); })
      .catch(() => { if (!cancelled) setPast([]); });
    return () => { cancelled = true; };
  }, [pastOpen, pastCount, pastHeldAt, roomCode, sessionToken]);

  useEffect(() => {
    let cancelled = false;
    setAvailable(false);
    api.aiGame(roomCode)
      .then((aiGame) => { if (!cancelled) setAvailable(aiGame); })
      .catch(() => undefined);
    return () => { cancelled = true; };
  }, [roomCode]);

  const enabled = state.ai_review === true;
  const hold = state.ai_hold ?? null;
  const replay = state.ai_replay ?? null;
  const takeover = state.ai_takeover ?? null;
  const heldAt = hold?.revision ?? null;
  // A message is about the position it was raised at.
  useEffect(() => {
    setError(null);
  }, [heldAt]);

  if (!available) return null;

  const nameOf = (id: PlayerId) =>
    state.players.find((player) => player.player_id === id)?.nickname ?? `플레이어 ${id}`;

  // Folded, the box is one line that still says what the AI seats are waiting for.
  const status = hold
    ? `⏸ ${nameOf(hold.turn.player)}의 차례가 끝났습니다`
    : takeover
      ? `✋ ${nameOf(takeover.player)}의 차례를 직접 두는 중`
      : replay
        ? `↩ ${nameOf(replay.player)} — 다시 두는 중`
        : 'AI 차례 검토';

  async function run(kind: 'switch' | 'continue' | 'reject' | 'past', call: () => Promise<unknown>, failed: string) {
    if (busy) return;
    setBusy(kind);
    setError(null);
    try {
      await call();
    } catch (e) {
      setError(e instanceof Error ? e.message : failed);
    } finally {
      setBusy(null);
    }
  }

  const foldButton = (
    <button
      type="button"
      className="ai-turn-review-collapse"
      aria-expanded={!collapsed}
      onClick={() => setCollapsed((value) => !value)}
    >
      {collapsed ? '펼치기' : '접기'}
    </button>
  );

  if (collapsed) {
    return (
      <section className="teacher-hint ai-turn-review ai-turn-review--collapsed" aria-label="AI 차례 검토">
        <span className="ai-turn-review-status" role="status">{status}</span>
        {foldButton}
      </section>
    );
  }

  return (
    <section className="teacher-hint ai-turn-review" aria-label="AI 차례 검토">
      <div className="ai-turn-review-head">
        <label className="ai-turn-review-switch">
          <input
            type="checkbox"
            checked={enabled}
            disabled={busy !== null}
            onChange={() => void run(
              'switch',
              () => api.aiReview(roomCode, sessionToken, !enabled),
              'AI 차례 멈춤을 바꾸지 못했습니다.',
            )}
          />
          {' '}AI 차례마다 멈춤
        </label>
        {foldButton}
      </div>
      {takeover && (
        <p className="teacher-hint-move" role="status">
          ✋ <strong>{nameOf(takeover.player)}</strong>의 차례를 직접 두세요 — 교사가 낼 다른 수가 없습니다
          {takeover.rejections ? ` (거절 ${takeover.rejections}회)` : ''}
        </p>
      )}
      {replay && !hold && (
        <p className="teacher-hint-note" role="status">
          ↩ {nameOf(replay.player)} — 거절된 차례를 다시 두는 중 (거절 {replay.rejections}회). 탐색이 끝나면 새 수가 나옵니다.
        </p>
      )}
      {hold && (
        <div className="ai-turn-review-hold" role="status">
          <p className="teacher-hint-move">
            ⏸ <strong>{nameOf(hold.turn.player)}</strong>의 차례가 끝났습니다
            {hold.by_player ? ' — 내가 대신 둔 차례' : hold.rejections > 0 && ` (거절 ${hold.rejections}회)`}
          </p>
          <ol className="ai-turn-review-moves">
            {hold.turn.decisions.map((decision, index) => (
              <li key={index}>{hintLabel(decision, state)}</li>
            ))}
          </ol>
          {!hold.by_player && typeof hold.spares_left === 'number' && (
            <p className="teacher-hint-note">{aiHoldSpares(hold)}</p>
          )}
          <div className="ai-turn-review-buttons">
          <button
            type="button"
            className="btn btn-primary"
            disabled={busy !== null}
            onClick={() => void run(
              'continue',
              () => api.aiContinue(roomCode, sessionToken),
              'AI를 이어 가게 하지 못했습니다.',
            )}
          >
            {busy === 'continue' ? '이어 가는 중…' : '계속'}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={busy !== null || !hold.can_reject}
            onClick={() => void run(
              'reject',
              () => api.aiReject(roomCode, sessionToken, hold.revision),
              'AI 차례를 거절하지 못했습니다.',
            )}
          >
            {busy === 'reject' ? '되돌리는 중…' : hold.by_player ? '다시 두기' : hold.spares_left === 0 ? '거절하고 직접 두기' : '거절'}
          </button>
          </div>
        </div>
      )}
      {pastCount > 0 && (
        <div className="ai-turn-review-past">
          <button
            type="button"
            className="ai-turn-review-collapse"
            aria-expanded={pastOpen}
            onClick={() => setPastOpen((value) => !value)}
          >
            지난 AI 차례 {pastCount}개 {pastOpen ? '닫기' : '보기'}
          </button>
          {pastOpen && past === null && <p className="teacher-hint-note">불러오는 중…</p>}
          {pastOpen && past !== null && (
            <ul className="ai-turn-review-past-list">
              {/* Newest first; the turn the AI seats wait at has its own buttons above. */}
              {[...past].reverse().filter((entry) => entry.turn.start_revision !== hold?.turn.start_revision).map((entry) => {
                const start = entry.turn.start_revision;
                return (
                  <li key={start}>
                    <span>
                      {entry.round > 0 ? `${entry.round}R` : '셋업'} · <strong>{nameOf(entry.turn.player)}</strong>
                      {entry.by_player ? ' (내가 둠)' : entry.rejections > 0 ? ` (거절 ${entry.rejections}회 뒤)` : ''}
                      {' — '}{entry.turn.decisions.map((decision) => hintLabel(decision, state)).join(' → ')}
                    </span>
                    {pastChosen === start ? (
                      <span className="ai-turn-review-past-confirm" role="alert">
                        이 차례의 처음으로 되돌립니다. 그 뒤에 둔 수는 내 수까지 모두 사라집니다.
                        <button
                          type="button"
                          className="btn btn-secondary"
                          disabled={busy !== null}
                          onClick={() => void run(
                            'past',
                            // The room's revision is asked for at the click: it may have moved on.
                            async () => {
                              const now = await api.aiTurns(roomCode, sessionToken);
                              await api.aiReject(roomCode, sessionToken, now.revision, start);
                              setPastChosen(null);
                              setPastOpen(false);
                            },
                            '지난 AI 차례로 되돌리지 못했습니다.',
                          )}
                        >
                          {busy === 'past' ? '되돌리는 중…' : entry.by_player ? '되돌려 다시 두기' : '되돌려 거절'}
                        </button>
                        <button type="button" className="ai-turn-review-collapse" disabled={busy !== null} onClick={() => setPastChosen(null)}>
                          취소
                        </button>
                      </span>
                    ) : (
                      <button type="button" className="ai-turn-review-collapse" disabled={busy !== null} onClick={() => setPastChosen(start)}>
                        여기로 되돌리기
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
          {pastOpen && <p className="teacher-hint-note">서버가 다시 시작되기 전의 차례는 목록에 없습니다.</p>}
        </div>
      )}
      {error && <p className="error-msg" role="alert">{error}</p>}
    </section>
  );
}
