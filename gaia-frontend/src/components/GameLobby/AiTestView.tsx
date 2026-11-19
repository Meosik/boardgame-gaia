import { useState } from 'react';
import { useRoomStore } from '../../store/roomStore';
import { readRecentRoom } from '../../store/recentRoom';
import { factionDisplayName } from '../../displayNames';
import { factionBoardImageSrc } from '../../assets/factionBoardImages';
import {
  AI_TEST_MAP_SEED,
  drawAiTestFactions,
  readShownCounts,
  recordShown,
} from '../../aiTestDraw';
import type { FactionId } from '../../types/game';

interface Props {
  onGameCreated: () => void;
  onBack: () => void;
}

/** The AI test: the lab's fixed map, four factions dealt evenly over the games, the player picks
 * one of them and three hard AI seats take the rest. No auction, no room title or password. */
export function AiTestView({ onGameCreated, onBack }: Props) {
  const [nickname, setNickname] = useState(() => readRecentRoom()?.nickname ?? '');
  const [factions] = useState(() => drawAiTestFactions(readShownCounts()));
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const createAiGame = useRoomStore((s) => s.actions.createAiGame);

  async function start(faction: FactionId) {
    if (!nickname.trim()) {
      setError('닉네임을 입력해주세요');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await createAiGame(nickname.trim(), 'hard', {
        seed: AI_TEST_MAP_SEED,
        faction,
        aiFactions: factions.filter((other) => other !== faction),
      });
      recordShown(factions);
      onGameCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'AI 테스트를 시작하지 못했습니다');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="create-room-view ai-test-view">
      <h2>AI 테스트</h2>
      <div className="form-group">
        <label htmlFor="ai-test-nickname">닉네임</label>
        <input
          id="ai-test-nickname"
          type="text"
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
          maxLength={16}
          placeholder="닉네임 입력"
        />
      </div>
      <fieldset className="ai-test-factions">
        <legend>이번 판 종족 — 하나를 고르면 바로 시작합니다</legend>
        {factions.map((faction) => {
          const portrait = factionBoardImageSrc(faction);
          return (
            <button
              key={faction}
              type="button"
              className="ai-test-faction"
              data-faction={faction}
              disabled={loading}
              onClick={() => void start(faction)}
            >
              {portrait && (
                <span
                  className="faction-pool-portrait"
                  aria-hidden="true"
                  style={{ backgroundImage: `url(${portrait})` }}
                />
              )}
              <span>{factionDisplayName(faction)}</span>
            </button>
          );
        })}
      </fieldset>
      <p>
        <small>
          나머지 세 종족은 AI(어려움)가 둡니다. 맵·타일은 실험과 같은 시드({AI_TEST_MAP_SEED})로
          고정되고 비딩 없이 바로 시작합니다. AI는 수마다 길면 20초쯤 생각합니다.
        </small>
      </p>

      {error && <p className="error-msg">{error}</p>}

      <div className="form-actions">
        <button className="btn btn-ghost" onClick={onBack} disabled={loading}>
          뒤로
        </button>
      </div>
    </div>
  );
}
