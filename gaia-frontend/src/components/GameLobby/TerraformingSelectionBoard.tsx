import { structureImageSrc } from '../../assets/structureImages';
import {
  TERRAFORMING_SATELLITE_COLOR,
  terraformingSelectionBoardImageSrc,
} from '../../assets/terraformingBoard';
import type { PlanetType } from '../../types/game';

const SLOT_POSITIONS = [
  { left: '11.7%', top: '65.1%' },
  { left: '37.0%', top: '65.1%' },
  { left: '62.2%', top: '65.1%' },
  { left: '87.4%', top: '65.1%' },
  { left: '24.5%', top: '87.3%' },
  { left: '49.9%', top: '87.3%' },
  { left: '75.2%', top: '87.3%' },
] as const;

interface Props {
  colorOrder: PlanetType[];
}

export function TerraformingSelectionBoard({ colorOrder }: Props) {
  if (colorOrder.length !== SLOT_POSITIONS.length) return null;

  return (
    <figure className="terraforming-selection-board" aria-label="테라포밍 색상 선택 보드">
      <img
        className="terraforming-selection-board-image"
        src={terraformingSelectionBoardImageSrc}
        alt="모웨이드와 팅커로이드 테라포밍 색상 순서 보드"
      />
      {colorOrder.map((planetType, index) => {
        const color = TERRAFORMING_SATELLITE_COLOR[planetType];
        if (!color) return null;
        return (
          <img
            key={`${index}-${planetType}`}
            className="terraforming-selection-board-marker"
            src={structureImageSrc(color, 'marker')}
            alt={`${index + 1}번 ${planetType} 색상 위성`}
            style={SLOT_POSITIONS[index]}
          />
        );
      })}
    </figure>
  );
}
