import { useState } from 'react';
import { shallow } from 'zustand/shallow';
import { useRoomStore } from '../../store/roomStore';
import type { GameSetup, SetupMode } from '../../types/game';

interface Props {
  onRoomCreated: () => void;
  onBack: () => void;
}

export function CreateRoomView({ onRoomCreated, onBack }: Props) {
  const [nickname, setNickname] = useState('');
  const [seed, setSeed] = useState('');
  const [setupMode, setSetupMode] = useState<SetupMode>('bidding');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { gameSetup, actions } = useRoomStore(
    (s) => ({
      gameSetup: s.gameSetup,
      actions: s.actions,
    }),
    shallow,
  );

  async function handleCreate() {
    if (!nickname.trim()) {
      setError('닉네임을 입력해주세요');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await actions.createRoom(nickname.trim(), seed.trim() || undefined, setupMode);
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
      <fieldset className="setup-mode-picker">
        <legend>종족 결정 방식</legend>
        <label className={setupMode === 'bidding' ? 'selected' : ''}>
          <input
            type="radio"
            name="setup-mode"
            value="bidding"
            checked={setupMode === 'bidding'}
            onChange={() => setSetupMode('bidding')}
          />
          <span>
            <strong>VP 비딩</strong>
            <small>방장부터 입찰하고 종족과 최종 순서를 선택합니다.</small>
          </span>
        </label>
        <label className={setupMode === 'sequential' ? 'selected' : ''}>
          <input
            type="radio"
            name="setup-mode"
            value="sequential"
            checked={setupMode === 'sequential'}
            onChange={() => setSetupMode('sequential')}
          />
          <span>
            <strong>순차 선택</strong>
            <small>기존 방식대로 시계방향으로 종족만 선택합니다.</small>
          </span>
        </label>
      </fieldset>

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
        <span className="preview-label">선택 방식:</span>
        <span className="preview-value">
          {setup.setup_mode === 'bidding' ? 'VP 비딩' : '순차 선택'}
        </span>
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
