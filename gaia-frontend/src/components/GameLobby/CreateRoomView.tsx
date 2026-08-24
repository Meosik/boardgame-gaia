import { useState } from 'react';
import { useRoomStore } from '../../store/roomStore';
import type { GameSetup } from '../../types/game';

interface Props {
  onRoomCreated: () => void;
  onBack: () => void;
}

export function CreateRoomView({ onRoomCreated, onBack }: Props) {
  const [nickname, setNickname] = useState('');
  const [seed, setSeed] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { gameSetup, actions } = useRoomStore((s) => ({
    gameSetup: s.gameSetup,
    actions: s.actions,
  }));

  async function handleCreate() {
    if (!nickname.trim()) {
      setError('닉네임을 입력해주세요');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await actions.createRoom(nickname.trim(), seed.trim() || undefined);
      onRoomCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : '방 생성에 실패했습니다');
    } finally {
      setLoading(false);
    }
  }

  async function handleRegenerate() {
    setLoading(true);
    try {
      await actions.regenerateSetup(seed.trim() || undefined);
    } catch (e) {
      setError(e instanceof Error ? e.message : '재생성에 실패했습니다');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="create-room-view">
      <h2>방 만들기</h2>
      <div className="form-group">
        <label htmlFor="nickname">닉네임</label>
        <input
          id="nickname"
          type="text"
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
          maxLength={16}
          placeholder="닉네임 입력"
        />
      </div>
      <div className="form-group">
        <label htmlFor="seed">시드 (선택)</label>
        <input
          id="seed"
          type="text"
          value={seed}
          onChange={(e) => setSeed(e.target.value)}
          placeholder="랜덤 시드 (비워두면 자동)"
        />
      </div>

      {error && <p className="error-msg">{error}</p>}

      {gameSetup && <SetupPreview setup={gameSetup} />}

      <div className="form-actions">
        <button className="btn btn-ghost" onClick={onBack} disabled={loading}>
          뒤로
        </button>
        {gameSetup && (
          <button className="btn btn-secondary" onClick={handleRegenerate} disabled={loading}>
            재생성
          </button>
        )}
        <button className="btn btn-primary" onClick={handleCreate} disabled={loading}>
          {loading ? '생성 중...' : '방 만들기'}
        </button>
      </div>
    </div>
  );
}

function SetupPreview({ setup }: { setup: GameSetup }) {
  return (
    <div className="setup-preview">
      <h3>셋업 미리보기</h3>
      <div className="preview-row">
        <span className="preview-label">시드:</span>
        <span className="preview-value mono">{setup.seed}</span>
      </div>
      <div className="preview-row">
        <span className="preview-label">섹터 수:</span>
        <span className="preview-value">{setup.sector_layout.length}</span>
      </div>
      <div className="preview-row">
        <span className="preview-label">팩션:</span>
        <span className="preview-value">
          {setup.factions.map((faction, i) => (
            <span key={i} className="faction-pair">
              {faction}
            </span>
          ))}
        </span>
      </div>
      <div className="preview-row">
        <span className="preview-label">라운드 타일:</span>
        <span className="preview-value">{setup.round_tile_ids.join(', ')}</span>
      </div>
    </div>
  );
}
