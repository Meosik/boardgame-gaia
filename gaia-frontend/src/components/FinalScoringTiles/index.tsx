import { finalScoringTileImageSrc } from '../../assets/finalScoringTileImages';
import type { FinalScoringCondition, FinalScoringTile } from '../../types/game';

interface Props {
  tiles: FinalScoringTile[];
}

const conditionLabels: Record<FinalScoringCondition, string> = {
  MostGaiaPlanets: '가장 많은 가이아 행성',
  MostDeepSpaceSectors: '가장 많은 심우주 섹터',
  MostStructuresInFederation: '연방에 포함된 건물 수',
  MostPlanetTypes: '개척한 행성 유형 수',
  MostBuildings: '전체 건물 수',
  MostAsteroids: '개척한 소행성 수',
  MostSectors: '개척한 일반 우주 섹터 수',
  GreatestDistancePiAcademy: '행성 의회와 아카데미 사이 최장 거리',
  MostSatellites: '배치한 위성 수',
};

export function FinalScoringTiles({ tiles }: Props) {
  return (
    <section className="final-scoring-tiles" aria-label="게임 종료 점수 타일">
      <div className="final-scoring-header">
        <span>FINAL SCORING</span>
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
                  1위 {tile.vp_1st} · 2위 {tile.vp_2nd} · 3위 {tile.vp_3rd} VP
                </span>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
