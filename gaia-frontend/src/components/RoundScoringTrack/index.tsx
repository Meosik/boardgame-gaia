import { roundScoringTileImageSrc } from '../../assets/roundScoringTileImages';
import type { RoundCondition, RoundTile } from '../../types/game';

interface Props {
  tiles: RoundTile[];
  currentRound: number;
}

const conditionLabels: Record<RoundCondition, string> = {
  BuildMine: '광산 건설',
  TerraformingStep: '테라포밍 단계 사용',
  BuildMineOnGaia: '가이아 행성에 광산 건설',
  UpgradeTradingStation: '교역소로 업그레이드',
  UpgradeLargeBuilding: '행성 의회·아카데미로 업그레이드',
  ResearchAdvance: '연구 분야 전진',
  FormFederation: '연방 토큰 획득',
  BuildMineOnNewPlanetType: '새로운 행성 유형에 광산 건설',
  BuildMineInNewSector: '이전에 개척하지 않은 우주·심우주 섹터에 광산 건설',
  UpgradeResearchLab: '연구소로 업그레이드',
};

export function RoundScoringTrack({ tiles, currentRound }: Props) {
  return (
    <section className="round-scoring-track" aria-label="라운드별 점수 타일">
      <div className="round-scoring-header">
        <div>
          <span>ROUND SCORING</span>
          <h3>라운드 점수 타일</h3>
        </div>
        <strong>{currentRound > 0 && currentRound <= 6 ? `${currentRound} / 6` : '게임 종료'}</strong>
      </div>
      <div className="round-scoring-list">
        {tiles.map((tile, index) => {
          const round = index + 1;
          const isActive = round === currentRound;
          const isComplete = round < currentRound || currentRound > tiles.length;
          const imageSrc = roundScoringTileImageSrc(tile.id);
          return (
            <article
              key={`${round}-${tile.id}`}
              className={`round-scoring-card ${isActive ? 'active' : ''} ${isComplete ? 'complete' : ''}`}
              aria-current={isActive ? 'step' : undefined}
            >
              <div className="round-scoring-round">R{round}</div>
              {imageSrc && <img src={imageSrc} alt={`라운드 ${round}: ${conditionLabels[tile.condition]}`} />}
              <div className="round-scoring-copy">
                <strong>{conditionLabels[tile.condition]}</strong>
                <span>단위당 +{tile.vp_per_unit} VP</span>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
