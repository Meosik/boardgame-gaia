import { scoringBoardImageSrc } from '../../assets/scoringBoardImage';
import { roundScoringTileImageSrc } from '../../assets/roundScoringTileImages';
import { finalScoringTileImageSrc } from '../../assets/finalScoringTileImages';
import type { FinalScoringTile, RoundTile } from '../../types/game';

interface Props {
  roundTiles: RoundTile[];
  finalScoringTiles: FinalScoringTile[];
  /** 0 = nothing has been played yet (pre-game preview); otherwise the round currently in
   * progress (1-6) — every tile for a round below this has already been played and flips. */
  currentRound: number;
}

/**
 * Positions measured directly off the complete `boards/scoring_board.jpg` (2104x2130):
 * the 6 round-tile
 * "wedge" slots fan out around the round-tracker dial (each wedge sits directly above its
 * matching dial number 1-6), and the 2 Final Scoring tile slots sit in the gray panels below.
 */
const ROUND_SLOTS_PCT = [
  { x: 38.6, y: 45.81, rotation: -68 },
  { x: 42.2, y: 36.1, rotation: -50 },
  { x: 48.16, y: 34.87, rotation: -16 },
  { x: 54.95, y: 35.02, rotation: 9 },
  { x: 60.7, y: 37.1, rotation: 40 },
  { x: 66.5, y: 46.45, rotation: 61 },
];
const FINAL_SLOTS_PCT = [
  { x: 69.39, y: 56.35 },
  { x: 69.39, y: 75.6 },
];
const ROTATED_FINAL_TILE_IDS = new Set([2, 6, 9]);

export function ScoringBoard({ roundTiles, finalScoringTiles, currentRound }: Props) {
  return (
    <section className="scoring-board" aria-label="점수 보드">
      <div className="scoring-board-image-wrap">
        <img className="scoring-board-image" src={scoringBoardImageSrc()} alt="점수 보드" />
        {roundTiles.map((tile, index) => {
          const round = index + 1;
          const passed = currentRound > 0 && round < currentRound;
          const slot = ROUND_SLOTS_PCT[index];
          if (!slot) return null;
          const { x, y, rotation } = slot;
          const src = roundScoringTileImageSrc(tile.id);
          if (!src) return null;
          return (
            <div
              key={`round-${round}`}
              className="scoring-board-round-anchor"
              style={{
                transformOrigin: `${x}% ${y}%`,
                transform: `rotate(${rotation}deg)`,
              }}
            >
              <div
                className={`scoring-board-tile scoring-board-tile--round ${passed ? 'scoring-board-tile--flipped' : ''}`}
                style={{ left: `${x}%`, top: `${y}%` }}
                aria-label={`라운드 ${round} 점수 타일${passed ? ' (완료됨)' : ''}`}
              >
                <div className="scoring-board-tile-inner">
                  <img className="scoring-board-tile-face scoring-board-tile-front" src={src} alt={`라운드 ${round}`} />
                  <div className="scoring-board-tile-face scoring-board-tile-back" />
                </div>
              </div>
            </div>
          );
        })}
        {finalScoringTiles.map((tile, index) => {
          const slot = FINAL_SLOTS_PCT[index];
          if (!slot) return null;
          const src = finalScoringTileImageSrc(tile.id);
          if (!src) return null;
          const usesRotatedRawScan = ROTATED_FINAL_TILE_IDS.has(tile.id);
          return (
            <div
              key={`final-${tile.id}`}
              className="scoring-board-tile scoring-board-tile--final"
              style={{ left: `${slot.x}%`, top: `${slot.y}%` }}
            >
              <img
                className={`scoring-board-final-image ${usesRotatedRawScan ? 'scoring-board-final-image--rotated-source' : ''}`}
                src={src}
                alt={`게임 종료 점수 타일 ${index + 1}`}
              />
            </div>
          );
        })}
      </div>
    </section>
  );
}
