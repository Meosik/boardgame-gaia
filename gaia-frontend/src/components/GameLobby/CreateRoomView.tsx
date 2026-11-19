import { useState } from 'react';
import { shallow } from 'zustand/shallow';
import { useRoomStore } from '../../store/roomStore';
import type { FactionId, GameSetup, SetupMode } from '../../types/game';
import type { AiLevel } from '../../api/rest';
import { FACTION_DISPLAY_NAMES, factionDisplayName } from '../../displayNames';

/** The lab's fixed-map experiment (gaia-rl/lab/fixed-seed-factions-quartet-e-88365.json,
 * HANDOFF E178/E181): one map seed and twelve faction sets, seat order as listed. Keep in
 * step with that file. */
const FIXED_MAP_SEED = 'quartet-e-88365';
const FIXED_MAP_TABLES: FactionId[][] = [
  ['Darkanians', 'BalTaks', 'Itars', 'Ivits'],
  ['Moweyds', 'Nevlas', 'Firaks', 'BalTaks'],
  ['Bescods', 'HadschHallas', 'BalTaks', 'Gleens'],
  ['Lantids', 'Xenos', 'Bescods', 'Itars'],
  ['Darkanians', 'Terrans', 'SpaceGiants', 'Geodens'],
  ['Tinkeroids', 'SpaceGiants', 'Taklons', 'Lantids'],
  ['Firaks', 'Terrans', 'Nevlas', 'Darkanians'],
  ['Ivits', 'Geodens', 'Taklons', 'Tinkeroids'],
  ['Geodens', 'Terrans', 'Firaks', 'Gleens'],
  ['Ambas', 'Xenos', 'Bescods', 'Moweyds'],
  ['Xenos', 'Lantids', 'Taklons', 'Tinkeroids'],
  ['SpaceGiants', 'HadschHallas', 'Nevlas', 'Ambas'],
];
/** `aiTable` value for the earlier AI game: random map, factions by the setup auction. */
const RANDOM_AUCTION = -1;

interface Props {
  onRoomCreated: () => void;
  manualControl?: boolean;
  onBack: () => void;
}

export function CreateRoomView({ onRoomCreated, onBack, manualControl = false }: Props) {
  const [nickname, setNickname] = useState(manualControl ? 'DEV' : '');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [setupMode, setSetupMode] = useState<SetupMode>('bidding');
  const [aiTable, setAiTable] = useState(0);
  const [aiFaction, setAiFaction] = useState<FactionId>(FIXED_MAP_TABLES[0][0]);
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
      if (manualControl) {
        await actions.createRoom(nickname.trim(), undefined, setupMode, true);
      } else {
        await actions.createRoom(nickname.trim(), undefined, setupMode, false, {
          name: name.trim() || undefined,
          password: password.trim() || undefined,
        });
      }
      onRoomCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : '방 생성에 실패했습니다');
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateAiGame(level: AiLevel) {
    if (!nickname.trim()) {
      setError('닉네임을 입력해주세요');
      return;
    }
    setLoading(true);
    setError('');
    try {
      if (aiTable === RANDOM_AUCTION) {
        await actions.createAiGame(nickname.trim(), level);
      } else {
        await actions.createAiGame(nickname.trim(), level, {
          seed: FIXED_MAP_SEED,
          faction: aiFaction,
          aiFactions: FIXED_MAP_TABLES[aiTable].filter((faction) => faction !== aiFaction),
        });
      }
      onRoomCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'AI 대전을 시작하지 못했습니다');
    } finally {
      setLoading(false);
    }
  }

  async function handleRegenerate() {
    setLoading(true);
    try {
      await actions.regenerateSetup();
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
        <label htmlFor="room-name">방 제목</label>
        <input
          id="room-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={24}
          placeholder="비워두면 '닉네임님의 방'"
        />
      </div>
      <div className="form-group">
        <label htmlFor="room-password">비밀번호 (선택)</label>
        <input
          id="room-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          maxLength={32}
          placeholder="비워두면 누구나 참가"
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
            <strong>승점 비딩</strong>
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
      {!manualControl && (
        <fieldset className="ai-table-picker">
          <legend>AI 대전 (고정 맵 실험)</legend>
          <div className="form-group">
            <label htmlFor="ai-table">종족 묶음</label>
            <select
              id="ai-table"
              value={aiTable}
              onChange={(e) => {
                const index = Number(e.target.value);
                setAiTable(index);
                if (index >= 0) setAiFaction(FIXED_MAP_TABLES[index][0]);
              }}
            >
              {FIXED_MAP_TABLES.map((table, index) => (
                <option key={index} value={index}>
                  {`${index + 1}. ` + table.map((faction) => FACTION_DISPLAY_NAMES[faction]).join(' · ')}
                </option>
              ))}
              <option value={RANDOM_AUCTION}>무작위 맵 · 비딩 (기존 AI 대전)</option>
            </select>
          </div>
          {aiTable !== RANDOM_AUCTION && (
            <div className="form-group">
              <label htmlFor="ai-my-faction">내 종족</label>
              <select
                id="ai-my-faction"
                value={aiFaction}
                onChange={(e) => setAiFaction(e.target.value as FactionId)}
              >
                {FIXED_MAP_TABLES[aiTable].map((faction) => (
                  <option key={faction} value={faction}>
                    {FACTION_DISPLAY_NAMES[faction]}
                  </option>
                ))}
              </select>
            </div>
          )}
          <p>
            <small>
              맵·타일은 실험과 같은 시드(quartet-e-88365)로 고정되고 비딩 없이 바로 시작합니다. 고른
              종족 말고 나머지 셋은 AI가 둡니다.
            </small>
          </p>
        </fieldset>
      )}

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
        {!manualControl && (
          <>
            <button
              className="btn btn-secondary"
              onClick={() => handleCreateAiGame('normal')}
              disabled={loading}
              title="위에서 고른 종족 묶음으로 AI 3명과 대전합니다. 무작위 맵을 고르면 종족과 차례를 AI와 비딩으로 정합니다. 방 제목·비밀번호는 쓰지 않습니다."
            >
              AI 3명과 대전
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => handleCreateAiGame('hard')}
              disabled={loading}
              title="더 강한 AI 3명과 대전합니다. AI가 수마다 더 오래 생각합니다(평균 몇 초, 길면 20초)."
            >
              AI 3명과 대전 (어려움)
            </button>
          </>
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
          {setup.setup_mode === 'bidding' ? '승점 비딩' : '순차 선택'}
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
              {factionDisplayName(faction)}
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
