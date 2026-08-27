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

/** Positions measured from the user-marked corners on the complete 2104x2130 board image. */
const ROUND_SLOTS_PCT = [
  { x: 28.232, y: 38.398, rotation: -74.86 },
  { x: 34.666, y: 27.537, rotation: -45.01 },
  { x: 45.643, y: 21.193, rotation: -15.22 },
  { x: 58.563, y: 21.195, rotation: 15.58 },
  { x: 69.765, y: 27.613, rotation: 45.87 },
  { x: 76.194, y: 38.458, rotation: 75.4 },
];
const FINAL_SLOTS_PCT = [
  { x: 70.825, y: 52.656, width: 19.897, height: 12.68 },
  { x: 70.83, y: 71.734, width: 19.907, height: 12.531 },
];

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
              className={`scoring-board-tile scoring-board-tile--round ${passed ? 'scoring-board-tile--flipped' : ''}`}
              style={{
                left: `${x}%`,
                top: `${y}%`,
                transform: `translate(-50%, -50%) rotate(${rotation}deg)`,
              }}
              aria-label={`라운드 ${round} 점수 타일${passed ? ' (완료됨)' : ''}`}
            >
              <div className="scoring-board-tile-inner">
                <img className="scoring-board-tile-face scoring-board-tile-front" src={src} alt={`라운드 ${round}`} />
                <div className="scoring-board-tile-face scoring-board-tile-back" />
              </div>
            </div>
          );
        })}
        {finalScoringTiles.map((tile, index) => {
          const slot = FINAL_SLOTS_PCT[index];
          if (!slot) return null;
          const src = finalScoringTileImageSrc(tile.id);
          if (!src) return null;
          return (
            <div
              key={`final-${tile.id}`}
              className="scoring-board-tile scoring-board-tile--final"
              style={{
                left: `${slot.x}%`,
                top: `${slot.y}%`,
                width: `${slot.width}%`,
                height: `${slot.height}%`,
              }}
            >
              <img
                className="scoring-board-final-image"
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
