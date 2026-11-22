import { useEffect, useMemo, useState } from 'react';
import { useRoomStore } from '../../store/roomStore';
import { readRecentRoom } from '../../store/recentRoom';
import { factionDisplayName } from '../../displayNames';
import { factionBoardImageSrc } from '../../assets/factionBoardImages';
import { api } from '../../api/rest';
import {
  AI_TEST_MAP_SEED,
  aiTestTurnOrder,
  drawAiTestFactions,
  readShownCounts,
  recordShown,
} from '../../aiTestDraw';
import { GameBoard } from '../GameBoard';
import { RoundBoosters } from '../RoundBoosters';
import { ScoringBoard } from '../ScoringBoard';
import { HOME_PLANET_BY_FACTION } from './FactionSelectView';
import type { FactionId, HexCoord, ResearchTracks, SeedPreview } from '../../types/game';

interface Props {
  onGameCreated: () => void;
  onBack: () => void;
}

const TRACK_NAMES: Record<keyof ResearchTracks, string> = {
  terraforming: '테라포밍',
  navigation: '항해',
  ai: '인공지능',
  gaia: '가이아',
  economy: '경제',
  science: '과학',
};

/** One line of what a faction starts the game with, from the engine's own seeded position. */
export function startLine(start: SeedPreview['starts'][number]): string {
  const { ore, credits, knowledge, qic, power } = start.resources;
  const tracks = (Object.keys(TRACK_NAMES) as (keyof ResearchTracks)[])
    .filter((track) => start.research_tracks[track] > 0)
    .map((track) => `${TRACK_NAMES[track]} ${start.research_tracks[track]}`);
  return [
    `광석 ${ore}`,
    `크레딧 ${credits}`,
    `지식 ${knowledge}`,
    `QIC ${qic}`,
    `파워 ${power.bowl1}/${power.bowl2}/${power.bowl3}${power.brainstone ? ' + 브레인스톤' : ''}`,
    ...(tracks.length > 0 ? [`시작 연구 ${tracks.join(', ')}`] : []),
  ].join(' · ');
}

/** The AI test: the lab's fixed map, four factions dealt evenly over the games, the player picks
 * one of them and three hard AI seats take the rest. The turn order is the lab's strength order
 * for the four factions (the one expected to do worst moves first), shown on each button. No
 * auction, no room title or password. The fixed map, its boosters and goals, and each dealt
 * faction's starting resources are shown, since the pick is made against them. */
export function AiTestView({ onGameCreated, onBack }: Props) {
  const [nickname, setNickname] = useState(() => readRecentRoom()?.nickname ?? '');
  const [factions] = useState(() => drawAiTestFactions(readShownCounts()));
  const order = aiTestTurnOrder(factions);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<SeedPreview | null>(null);
  const [pointed, setPointed] = useState<FactionId | null>(null);
  const createAiGame = useRoomStore((s) => s.actions.createAiGame);

  useEffect(() => {
    let cancelled = false;
    api.getSeedPreview(AI_TEST_MAP_SEED, factions)
      .then((value) => {
        if (!cancelled) setPreview(value);
      })
      .catch(() => {
        // The pick works without the preview; the page just stays as it was before it existed.
      });
    return () => {
      cancelled = true;
    };
  }, [factions]);

  // The planets the pointed-at faction may start on, outlined on the map.
  const homeHexes = useMemo<HexCoord[]>(() => {
    if (!preview || !pointed) return [];
    const home = HOME_PLANET_BY_FACTION[pointed];
    return Object.values(preview.board.hexes)
      .filter((hex) => hex.planet?.planet_type === home)
      .map((hex) => hex.coord);
  }, [preview, pointed]);

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
        aiFactions: order.filter((other) => other !== faction),
        seat: order.indexOf(faction) + 1,
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
        <legend>이번 판 종족 — 하나를 고르면 바로 시작합니다 (차례는 이 맵에서 잘 풀릴 것 같은 종족일수록 뒤)</legend>
        {factions.map((faction) => {
          const portrait = factionBoardImageSrc(faction);
          const begin = preview?.starts.find((candidate) => candidate.faction === faction);
          return (
            <button
              key={faction}
              type="button"
              className="ai-test-faction"
              data-faction={faction}
              disabled={loading}
              onClick={() => void start(faction)}
              onMouseEnter={() => setPointed(faction)}
              onMouseLeave={() => setPointed((current) => (current === faction ? null : current))}
              onFocus={() => setPointed(faction)}
              onBlur={() => setPointed((current) => (current === faction ? null : current))}
            >
              {portrait && (
                <span
                  className="faction-pool-portrait"
                  aria-hidden="true"
                  style={{ backgroundImage: `url(${portrait})` }}
                />
              )}
              <span className="ai-test-faction-text">
                <span>{factionDisplayName(faction)}</span>
                <span className="ai-test-turn">{order.indexOf(faction) + 1}번 차례</span>
                {begin && <small className="ai-test-start">{startLine(begin)}</small>}
              </span>
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

      {preview && (
        <section className="ai-test-preview" aria-label="이번 판 미리보기">
          <h3>이번 판 지도</h3>
          <p className="ai-test-preview-note">
            <small>종족 위에 마우스를 올리면 그 종족이 시작할 수 있는 행성이 노란 테두리로 표시됩니다.</small>
          </p>
          <div className="ai-test-map">
            <GameBoard board={preview.board} validTargets={homeHexes} highlightDeepSpace highlightInterspace />
          </div>
          <h3>라운드 부스터</h3>
          <RoundBoosters availableBoosters={preview.boosters} players={[]} />
          <h3>라운드·게임 종료 목표</h3>
          <ScoringBoard
            roundTiles={preview.round_tiles}
            finalScoringTiles={preview.final_scoring_tiles}
            currentRound={0}
          />
        </section>
      )}

      {error && <p className="error-msg">{error}</p>}

      <div className="form-actions">
        <button className="btn btn-ghost" onClick={onBack} disabled={loading}>
          뒤로
        </button>
      </div>
    </div>
  );
}
