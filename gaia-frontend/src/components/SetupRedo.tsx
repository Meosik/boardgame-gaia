import { useState } from 'react';
import { api } from '../api/rest';
import { useRoomStore } from '../store/roomStore';
import type { GameState } from '../types/game';

interface Props {
  roomCode: string;
  sessionToken: string;
  /** The live position: `setup_redo` says how many of the player's setup choices can be taken back. */
  state: GameState;
}

/** In an AI game the player takes back their own setup choices — starting structures and the
 * starting booster — latest first: the room goes back to the position of that choice, the player
 * chooses again and the AI seats play what came after it again. Offered from the first placement
 * until the player's first action of the game; shown only while the server says a choice can be
 * taken back. */
export function SetupRedo({ roomCode, sessionToken, state }: Props) {
  const revision = useRoomStore((s) => s.revision);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const count = state.setup_redo ?? 0;
  if (count <= 0) return null;

  async function redo() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await api.setupRedo(roomCode, sessionToken, revision);
    } catch (e) {
      setError(e instanceof Error ? e.message : '선택을 되돌리지 못했습니다.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="teacher-hint setup-redo" aria-label="셋업 선택 되돌리기">
      <button
        type="button"
        className="btn btn-small btn-secondary"
        disabled={busy}
        onClick={() => void redo()}
      >
        {busy ? '되돌리는 중…' : `내 직전 셋업 선택 되돌리기 (${count})`}
      </button>
      <span className="teacher-hint-note">
        시작 건물·시작 부스터를 고른 자리로 돌아가 다시 고릅니다. 그 뒤 AI의 선택은 AI가 다시 둡니다. 내 첫 행동 전까지 쓸 수 있습니다.
      </span>
      {error && <p className="error-msg" role="alert">{error}</p>}
    </section>
  );
}
