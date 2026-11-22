import { useEffect, useRef, useState } from 'react';
import { api } from '../api/rest';
import { useRoomStore } from '../store/roomStore';
import { candidateLabel, type Candidate } from './AiCoach/protocol';
import type { GameState, HexCoord } from '../types/game';

interface Props {
  roomCode: string;
  sessionToken: string;
  state: GameState;
  /** Told the board hexes of the move on screen, and no hexes when no move is shown, so the
   * map can mark them. */
  onHexes?: (hexes: HexCoord[]) => void;
}

interface Shown {
  revision: number;
  text: string;
  failed: boolean;
  hexes: HexCoord[];
}

const NO_HEXES: HexCoord[] = [];

function hintLabel(decision: unknown, state: GameState): string {
  const candidate = decision as Candidate | null;
  if (!candidate || typeof candidate !== 'object' || !candidate.action
    || typeof candidate.action.type !== 'string') {
    return JSON.stringify(decision);
  }
  return candidateLabel(candidate, state);
}

/** Every board hex a decision names (its target, a bonus mine, federation buildings and
 * satellites), each once. REST replies arrive with coordinates already decoded to { q, r }. */
export function hintHexes(decision: unknown): HexCoord[] {
  const found: HexCoord[] = [];
  function walk(value: unknown) {
    if (Array.isArray(value)) {
      value.forEach(walk);
      return;
    }
    if (value === null || typeof value !== 'object') return;
    const object = value as Record<string, unknown>;
    const { q, r } = object;
    if (typeof q === 'number' && typeof r === 'number') {
      if (!found.some((hex) => hex.q === q && hex.r === r)) found.push({ q, r });
      return;
    }
    Object.values(object).forEach(walk);
  }
  walk(decision);
  return found;
}

/** "What would the teacher play here?" for the human seat of an AI game. On request only, one
 * step at a time (the teacher picks a free action and the main action separately). Every request
 * carries the room revision the player is looking at: an answer that arrives after the position
 * changed is dropped, and what is shown disappears with the position it was for. */
export function TeacherHint({ roomCode, sessionToken, state, onHexes }: Props) {
  const revision = useRoomStore((s) => s.revision);
  const [available, setAvailable] = useState(false);
  const [asking, setAsking] = useState<number | null>(null);
  const [shown, setShown] = useState<Shown | null>(null);
  const current = useRef(revision);
  current.current = revision;

  useEffect(() => {
    let cancelled = false;
    setAvailable(false);
    api.aiGame(roomCode)
      .then((aiGame) => { if (!cancelled) setAvailable(aiGame); })
      .catch(() => undefined);
    return () => { cancelled = true; };
  }, [roomCode]);

  const waiting = asking === revision;
  const result = shown && shown.revision === revision ? shown : null;
  // The map marks exactly the move that is on screen: nothing while waiting, after a failure,
  // or once the position changed.
  const hexes = result && !result.failed ? result.hexes : NO_HEXES;
  useEffect(() => {
    onHexes?.(hexes);
  }, [hexes, onHexes]);
  useEffect(() => () => onHexes?.(NO_HEXES), [onHexes]);

  if (!available) return null;

  async function ask() {
    const asked = revision;
    const position = state;
    setAsking(asked);
    setShown(null);
    try {
      const reply = await api.aiHint(roomCode, sessionToken, asked);
      if (reply.revision === asked && current.current === asked) {
        setShown({
          revision: asked,
          text: hintLabel(reply.decision, position),
          failed: false,
          hexes: hintHexes(reply.decision),
        });
      }
    } catch (e) {
      if (current.current === asked) {
        const text = e instanceof Error ? e.message : '교사의 수를 받지 못했습니다.';
        setShown({ revision: asked, text, failed: true, hexes: NO_HEXES });
      }
    } finally {
      setAsking((value) => (value === asked ? null : value));
    }
  }

  return (
    <section className="teacher-hint" aria-label="교사 수 보기">
      <button
        type="button"
        className="btn btn-small btn-secondary"
        onClick={() => void ask()}
        disabled={waiting}
      >
        {waiting ? '교사가 생각 중…' : '교사 수 보기'}
      </button>
      {waiting && (
        <span className="teacher-hint-note">
          보통 20초 안팎, 다른 대국과 겹치면 더 걸립니다. 그사이 수를 두면 이 답은 버려집니다.
        </span>
      )}
      {result && !result.failed && (
        <p className="teacher-hint-move" role="status">
          교사라면: <strong>{result.text}</strong>
          {result.hexes.length > 0 && (
            <span className="teacher-hint-note"> · 지도에 초록 점선으로 표시</span>
          )}
        </p>
      )}
      {result && result.failed && (
        <p className="error-msg" role="alert">{result.text}</p>
      )}
    </section>
  );
}
