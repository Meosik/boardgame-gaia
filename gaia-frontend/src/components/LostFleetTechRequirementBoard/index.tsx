import { ADVANCED_TECH_TILE_LABELS } from '../advancedTechDescriptions';
import {
  lostFleetTechRequirementBoardImageSrc,
  type LostFleetTechRequirementSide,
} from '../../assets/lostFleetTechRequirementBoardImages';
import { advancedTechTileImageSrc } from '../../assets/techTileImages';
import { LOST_FLEET_DISPLAY_NAME } from '../../displayNames';

interface Props {
  side?: LostFleetTechRequirementSide;
  tileId?: number | null;
  onSelect?: () => void;
}

export function LostFleetTechRequirementBoard({
  side = 'exploration-shuttles',
  tileId = null,
  onSelect,
}: Props) {
  const requirementLabel = side === 'exploration-shuttles'
    ? '함선 3곳 탐사 고급 기술 조건 보드'
    : '승점 25점 이상 고급 기술 조건 보드';
  const tileSrc = tileId === null ? undefined : advancedTechTileImageSrc(tileId);

  return (
    <figure className="lost-fleet-tech-requirement" aria-label={`${LOST_FLEET_DISPLAY_NAME} 고급 기술 조건 보드`}>
      <img
        className="lost-fleet-tech-requirement-board"
        src={lostFleetTechRequirementBoardImageSrc(side)}
        alt={requirementLabel}
      />
      {tileSrc && onSelect ? <button type="button" data-tutorial-target="advanced:LostFleet" className="lost-fleet-tech-requirement-tile"
        style={{ background: 'transparent', border: 0, padding: 0 }} onClick={onSelect}
        aria-label={`함대 고급 기술 타일 ${tileId} 선택`}>
        <img src={tileSrc} alt="" style={{ width: '100%', display: 'block' }} />
      </button> : tileSrc && (
        <img
          className="lost-fleet-tech-requirement-tile"
          src={tileSrc}
          alt={`${LOST_FLEET_DISPLAY_NAME} 조건 고급 기술 타일 ${tileId}`}
          title={tileId === null ? undefined : ADVANCED_TECH_TILE_LABELS[tileId]}
        />
      )}
    </figure>
  );
}
