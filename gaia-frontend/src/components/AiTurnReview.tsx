import { useEffect, useState } from 'react';
import { api } from '../api/rest';
import { hintLabel } from './TeacherHint';
import type { AiHold, GameState, PlayerId } from '../types/game';

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
 * Playing one's own move also lets the AI seats go on, so a turn is rejected before that. */
export function AiTurnReview({ roomCode, sessionToken, state }: Props) {
  const [available, setAvailable] = useState(false);
  const [busy, setBusy] = useState<'switch' | 'continue' | 'reject' | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  async function run(kind: 'switch' | 'continue' | 'reject', call: () => Promise<unknown>, failed: string) {
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

  return (
    <section className="teacher-hint ai-turn-review" aria-label="AI 차례 검토">
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
      {error && <p className="error-msg" role="alert">{error}</p>}
    </section>
  );
}
