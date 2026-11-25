import { useState } from 'react';
import { useRoomStore } from '../../store/roomStore';
import { readRecentRoom } from '../../store/recentRoom';
import { factionDisplayName } from '../../displayNames';
import { factionBoardImageSrc } from '../../assets/factionBoardImages';
import { AI_TEST_MAP_SEED, aiTestTurnOrder, drawAiTestFactions } from '../../aiTestDraw';
import type { FactionId } from '../../types/game';

interface Props {
  onGameCreated: () => void;
  onBack: () => void;
}

/** The AI test: the lab's fixed map, four factions drawn at random (a 다시 뽑기 button draws four new ones), the player picks
 * one of them and three hard AI seats take the rest. The turn order is the lab's strength order
 * for the four factions (the one expected to do worst moves first), shown on each button. No
 * auction, no room title or password. */
export function AiTestView({ onGameCreated, onBack }: Props) {
  const [nickname, setNickname] = useState(() => readRecentRoom()?.nickname ?? '');
  const [factions, setFactions] = useState(() => drawAiTestFactions());
  const order = aiTestTurnOrder(factions);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  /** The AI seats wait after each of their turns for 계속 / 거절 (can be switched in the game too). */
  const [review, setReview] = useState(false);
  const createAiGame = useRoomStore((s) => s.actions.createAiGame);

  /** `allSeats`: the AI plays all four factions and the player has no seat — they look at the AI
   * turns (계속 / 거절 / 대신 두기). `faction` is then only the fourth faction's name for the
   * server, and the wait after every AI turn starts switched on. */
  async function start(faction: FactionId, allSeats = false) {
    if (!nickname.trim()) {
      setError('닉네임을 입력해주세요');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const table = {
        seed: AI_TEST_MAP_SEED,
        faction,
        aiFactions: order.filter((other) => other !== faction),
        seat: order.indexOf(faction) + 1,
      };
      if (allSeats) await createAiGame(nickname.trim(), 'hard', table, true, true);
      else await createAiGame(nickname.trim(), 'hard', table, review);
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
        <legend>이번 판 종족 — 고르면 바로 시작</legend>
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
              <span className="ai-test-turn">{order.indexOf(faction) + 1}번 차례</span>
            </button>
          );
        })}
      </fieldset>
      <div className="form-group">
        <label>
          <input
            type="checkbox"
            checked={review}
            disabled={loading}
            onChange={(e) => setReview(e.target.checked)}
          />
          {' '}AI 차례마다 멈춤
        </label>
      </div>

      <button
        type="button"
        className="btn btn-primary ai-test-all-ai"
        onClick={() => void start(order[0], true)}
        disabled={loading}
      >
        네 종족 모두 AI로 시작
      </button>
      {error && <p className="error-msg">{error}</p>}

      <div className="form-actions">
        <button className="btn btn-ghost" onClick={onBack} disabled={loading}>
          뒤로
        </button>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => setFactions(drawAiTestFactions())}
          disabled={loading}
        >
          다시 뽑기
        </button>
      </div>
    </div>
  );
}
