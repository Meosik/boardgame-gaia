import { FACTION_STRUCTURE_COLOR, STRUCTURE_COLOR_HEX, structureImageSrc } from '../../assets/structureImages';
import {
  TERRAFORMING_SATELLITE_COLOR,
  terraformingSelectionBoardImageSrc,
} from '../../assets/terraformingBoard';
import { factionDisplayName, planetTypeDisplayName } from '../../displayNames';
import type { FactionId, PlanetType } from '../../types/game';

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
  allocations?: { faction: FactionId; colors: PlanetType[] }[];
}

export function TerraformingSelectionBoard({ colorOrder, allocations = [] }: Props) {
  if (colorOrder.length !== SLOT_POSITIONS.length) return null;

  return (
    <figure className="terraforming-selection-board" aria-label="테라포밍 색상 선택 보드">
      {allocations.length > 0 && <figcaption className="terraforming-allocation-caption">표시된 색은 해당 종족의 테라포밍 3단계</figcaption>}
      <div className="terraforming-selection-board-surface">
      <img
        className="terraforming-selection-board-image"
        src={terraformingSelectionBoardImageSrc}
        alt="모웨이드와 팅커로이드 테라포밍 색상 순서 보드"
      />
      {colorOrder.map((planetType, index) => {
        const color = TERRAFORMING_SATELLITE_COLOR[planetType];
        if (!color) return null;
        const owners = allocations.filter((allocation) => allocation.colors.includes(planetType));
        const ownerColors = owners.map(({ faction }) => STRUCTURE_COLOR_HEX[FACTION_STRUCTURE_COLOR[faction]]);
        const label = owners.map(({ faction }) => factionDisplayName(faction)).join(' · ');
        return (
          <div
            key={`${index}-${planetType}`}
            className="terraforming-selection-board-marker"
            title={label ? `${planetTypeDisplayName(planetType)}: ${label} 테라포밍 3단계` : undefined}
            style={{
              ...SLOT_POSITIONS[index],
              borderColor: ownerColors[0] ?? 'transparent',
              borderRightColor: ownerColors[1] ?? ownerColors[0] ?? 'transparent',
              borderBottomColor: ownerColors[1] ?? ownerColors[0] ?? 'transparent',
            }}
          >
            <img src={structureImageSrc(color, 'marker')} alt={`${index + 1}번 ${planetTypeDisplayName(planetType)} 색상 위성`} />
            {owners.length > 0 && <span className="terraforming-allocation-label">{owners.map(({ faction }) =>
              <span key={faction} style={{ color: STRUCTURE_COLOR_HEX[FACTION_STRUCTURE_COLOR[faction]] }}>{factionDisplayName(faction)}</span>
            )}</span>}
          </div>
        );
      })}
      </div>
    </figure>
  );
}
