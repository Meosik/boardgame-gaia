import { useState } from 'react';
import { api } from '../../api/rest';
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
  /** The map of the game: the lab's fixed one, or that of the earlier room taken over (`like`). */
  const [mapSeed, setMapSeed] = useState(AI_TEST_MAP_SEED);
  /** An earlier AI game whose table is taken over: its code (the last room by default) and,
   * once read, what kind of game it was. */
  const [likeCode, setLikeCode] = useState(() => readRecentRoom()?.roomCode ?? '');
  const [like, setLike] = useState<{ code: string; allSeats: boolean } | null>(null);

  /** Takes over the factions, map and review switch of an earlier AI game; the game itself is
   * started with the buttons below, as after a draw. */
  async function takeOver() {
    const code = likeCode.trim().toUpperCase();
    if (!code) return;
    setLoading(true);
    setError('');
    try {
      const table = await api.aiTable(code);
      if (!table || table.factions.length !== 4) {
        setError(`방 ${code}의 세팅을 읽지 못했습니다 (AI 대전이 아니거나 종족이 정해지지 않은 방)`);
        return;
      }
      setFactions(table.factions);
      setMapSeed(table.seed);
      setReview(table.review);
      setLike({ code, allSeats: table.all_seats });
    } catch (e) {
      setError(e instanceof Error ? e.message : `방 ${code}의 세팅을 읽지 못했습니다`);
    } finally {
      setLoading(false);
    }
  }

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
        seed: mapSeed,
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
      <div className="form-group ai-test-like">
        <label htmlFor="ai-test-like">이전 방 세팅 그대로</label>
        <input
          id="ai-test-like"
          type="text"
          value={likeCode}
          onChange={(e) => setLikeCode(e.target.value)}
          maxLength={8}
          placeholder="방 코드"
        />
        <button type="button" className="btn btn-ghost" onClick={() => void takeOver()} disabled={loading || !likeCode.trim()}>
          불러오기
        </button>
        {like && (
          <p className="teacher-hint-note" role="status">
            방 {like.code}의 종족 · 지도를 불러왔습니다
            {like.allSeats ? ' — 그 방은 네 종족 모두 AI였습니다(아래 「네 종족 모두 AI로 시작」)' : ''}
          </p>
        )}
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
          onClick={() => {
            // A new draw is on the lab's map again, whatever room was taken over before.
            setFactions(drawAiTestFactions());
            setMapSeed(AI_TEST_MAP_SEED);
            setLike(null);
          }}
          disabled={loading}
        >
          다시 뽑기
        </button>
      </div>
    </div>
  );
}
