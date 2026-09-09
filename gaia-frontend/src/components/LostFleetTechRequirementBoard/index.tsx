import {
  lostFleetTechRequirementBoardImageSrc,
  type LostFleetTechRequirementSide,
} from '../../assets/lostFleetTechRequirementBoardImages';
import { advancedTechTileImageSrc } from '../../assets/techTileImages';

interface Props {
  side?: LostFleetTechRequirementSide;
  tileId?: number | null;
}

export function LostFleetTechRequirementBoard({
  side = 'exploration-shuttles',
  tileId = null,
}: Props) {
  const requirementLabel = side === 'exploration-shuttles'
    ? '함선 3곳 탐사 고급 기술 조건 보드'
    : '승점 25점 이상 고급 기술 조건 보드';
  const tileSrc = tileId === null ? undefined : advancedTechTileImageSrc(tileId);

  return (
    <figure className="lost-fleet-tech-requirement" aria-label="Lost Fleet 고급 기술 조건 보드">
      <img
        className="lost-fleet-tech-requirement-board"
        src={lostFleetTechRequirementBoardImageSrc(side)}
        alt={requirementLabel}
      />
      {tileSrc && (
        <img
          className="lost-fleet-tech-requirement-tile"
          src={tileSrc}
          alt={`Lost Fleet 조건 고급 기술 타일 ${tileId}`}
        />
      )}
    </figure>
  );
}
