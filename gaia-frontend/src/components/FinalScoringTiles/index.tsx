import { finalScoringTileImageSrc } from '../../assets/finalScoringTileImages';
import type { FinalScoringTile } from '../../types/game';
import { FINAL_SCORING_LABELS as conditionLabels } from '../../finalScoring';

interface Props {
  tiles: FinalScoringTile[];
}

export function FinalScoringTiles({ tiles }: Props) {
  return (
    <section className="final-scoring-tiles" aria-label="게임 종료 점수 타일">
      <div className="final-scoring-header">
        <span>최종 점수</span>
        <h3>게임 종료 점수</h3>
      </div>
      <div className="final-scoring-list">
        {tiles.map((tile) => {
          const imageSrc = finalScoringTileImageSrc(tile.id);
          return (
            <article className="final-scoring-card" key={tile.id}>
              {imageSrc && <img src={imageSrc} alt={conditionLabels[tile.condition]} />}
              <div>
                <strong>{conditionLabels[tile.condition]}</strong>
                <span>
                  승점: 1위 {tile.vp_1st}점 · 2위 {tile.vp_2nd}점 · 3위 {tile.vp_3rd}점
                </span>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
