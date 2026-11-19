import { useState } from 'react';
import { shallow } from 'zustand/shallow';
import { useRoomStore } from '../../store/roomStore';
import type { FactionId, GameSetup, SetupMode } from '../../types/game';
import type { AiGameTable, AiLevel } from '../../api/rest';
import { FACTION_DISPLAY_NAMES, factionDisplayName } from '../../displayNames';

/** The two sides of one faction board (engine: `FactionId::other_board_side`); one table
 * cannot seat both. */
const FACTION_BOARDS: FactionId[][] = [
  ['Terrans', 'Lantids'],
  ['Xenos', 'Gleens'],
  ['Taklons', 'Ambas'],
  ['HadschHallas', 'Ivits'],
  ['Geodens', 'BalTaks'],
  ['Firaks', 'Bescods'],
  ['Nevlas', 'Itars'],
  ['Tinkeroids', 'Darkanians'],
  ['Moweyds', 'SpaceGiants'],
];
const FACTION_IDS = FACTION_BOARDS.flat();
const AI_SEATS = [0, 1, 2];

/** The fixed table the AI-game form asks for: `undefined` when nothing is filled in (the
 * usual auction game), a message when the choices cannot sit at one table. */
function aiGameTable(
  seed: string,
  myFaction: FactionId | '',
  aiFactions: (FactionId | '')[],
): AiGameTable | string | undefined {
  const named = aiFactions.filter((faction): faction is FactionId => faction !== '');
  if (named.length !== 0 && named.length !== aiFactions.length) {
    return 'AI 종족은 셋 다 고르거나 셋 다 무작위로 두세요';
  }
  const seats = myFaction ? [myFaction, ...named] : named;
  const boards = seats.map((faction) => FACTION_BOARDS.findIndex((board) => board.includes(faction)));
  if (new Set(boards).size !== boards.length) {
    return '같은 종족이나 같은 종족판의 앞뒷면(모행성이 같은 두 종족)은 함께 고를 수 없습니다';
  }
  if (!seed && !myFaction && named.length === 0) return undefined;
  return {
    seed: seed || undefined,
    faction: myFaction || undefined,
    aiFactions: named.length ? named : undefined,
  };
}

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
  const [aiSeed, setAiSeed] = useState('');
  const [aiMyFaction, setAiMyFaction] = useState<FactionId | ''>('');
  const [aiFactions, setAiFactions] = useState<(FactionId | '')[]>(AI_SEATS.map(() => ''));
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
    const table = aiGameTable(aiSeed.trim(), aiMyFaction, aiFactions);
    if (typeof table === 'string') {
      setError(table);
      return;
    }
    setLoading(true);
    setError('');
    try {
      if (table) await actions.createAiGame(nickname.trim(), level, table);
      else await actions.createAiGame(nickname.trim(), level);
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
        <details className="ai-table-picker">
          <summary>AI 대전 맵·종족 고정 (선택)</summary>
          <p>
            <small>
              하나라도 채우면 비딩 없이 바로 시작합니다. 같은 시드는 같은 맵·타일이고, 비워 둔
              종족은 시드로 정해집니다.
            </small>
          </p>
          <div className="form-group">
            <label htmlFor="ai-seed">맵 시드</label>
            <input
              id="ai-seed"
              type="text"
              value={aiSeed}
              onChange={(e) => setAiSeed(e.target.value)}
              maxLength={64}
              placeholder="비워두면 무작위 맵"
            />
          </div>
          <div className="form-group">
            <label htmlFor="ai-my-faction">내 종족</label>
            <select
              id="ai-my-faction"
              value={aiMyFaction}
              onChange={(e) => setAiMyFaction(e.target.value as FactionId | '')}
            >
              <option value="">무작위</option>
              {FACTION_IDS.map((faction) => (
                <option key={faction} value={faction}>
                  {FACTION_DISPLAY_NAMES[faction]}
                </option>
              ))}
            </select>
          </div>
          {AI_SEATS.map((seat) => (
            <div className="form-group" key={seat}>
              <label htmlFor={`ai-faction-${seat}`}>AI {seat + 1} 종족</label>
              <select
                id={`ai-faction-${seat}`}
                value={aiFactions[seat]}
                onChange={(e) =>
                  setAiFactions((current) =>
                    current.map((faction, index) =>
                      index === seat ? (e.target.value as FactionId | '') : faction,
                    ),
                  )
                }
              >
                <option value="">무작위</option>
                {FACTION_IDS.map((faction) => (
                  <option key={faction} value={faction}>
                    {FACTION_DISPLAY_NAMES[faction]}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </details>
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
              title="무작위 맵으로 AI 3명과 바로 대전합니다. 종족과 차례는 AI와 비딩으로 정합니다. 방 제목·비밀번호는 쓰지 않습니다."
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
