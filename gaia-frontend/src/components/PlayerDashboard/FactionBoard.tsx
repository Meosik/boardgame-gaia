import { factionBoardImageSrc } from '../../assets/factionBoardImages';
import { tinkeringTileImageSrc } from '../../assets/tinkeringTileImages';
import { TERRAFORMING_SATELLITE_COLOR } from '../../assets/terraformingBoard';
import {
  FACTION_STRUCTURE_COLOR,
  STRUCTURE_COLOR_HEX,
  structureImageSrc,
} from '../../assets/structureImages';
import type { FactionId, PlanetType, PowerCycle, Resources, Structure } from '../../types/game';
import { factionDisplayName, planetTypeDisplayName } from '../../displayNames';
import { GamePieceIcon, type GamePieceIconKind } from '../GamePieceIcon';
import { ResourcePanel } from './ResourcePanel';
import { SatelliteToken } from './SatelliteToken';
import { exposedFactionBoardStructureSlots, remainingFactionBoardStructureSlots } from './factionBoardStructureSlots';
import { FactionBoardSideRack } from './FactionBoardSideRack';

interface Props {
  faction: FactionId;
  structures: Structure[];
  resources?: Resources;
  power?: PowerCycle;
  gaiaformersAvailable?: number;
  techTiles?: number[];
  advancedTechTiles?: number[];
  coveredTechTiles?: number[];
  federationTokens?: number[];
  grayFederationTokens?: number[];
  booster?: number | null;
  artifacts?: number[];
  expensiveTerraformingPlanetTypes?: PlanetType[];
  selectedTinkeringTile?: number | null;
}

const POWER_BOWLS = [
  { key: 'bowl1', label: 'I', centerX: 25.8, centerY: 32.0, columns: 4 },
  { key: 'bowl2', label: 'II', centerX: 25.8, centerY: 18.2, columns: 4 },
  { key: 'bowl3', label: 'III', centerX: 44.0, centerY: 23.3, columns: 4 },
  { key: 'gaia_bowl', label: 'G', centerX: 7.5, centerY: 24.5, columns: 3 },
] as const;

const GAIAFORMER_SLOTS = [
  { x: 1869, y: 519 },
  { x: 2056, y: 519 },
  { x: 2238, y: 519 },
] as const;
const FACTION_BOARD_WIDTH = 2323;
const FACTION_BOARD_HEIGHT = 1489;
const RESOURCE_TRACK_CENTER_Y = 112;
const RESOURCE_TRACK_X = [
  109, 299, 448, 595, 743, 893, 1040, 1186,
  1334, 1482, 1631, 1767, 1885, 2004, 2123, 2244,
] as const;

function resourceTrackPosition(
  value: number,
  stackIndex = 0,
  stackSize = 1,
): { left: string; top: string } {
  const trackValue = Math.max(0, Math.min(15, value));
  const stackOffset = (stackIndex - (stackSize - 1) / 2) * 34;
  return {
    left: `${(RESOURCE_TRACK_X[trackValue] + stackOffset) * 100 / FACTION_BOARD_WIDTH}%`,
    top: `${RESOURCE_TRACK_CENTER_Y * 100 / FACTION_BOARD_HEIGHT}%`,
  };
}

function resourceTrackMarkers(resources: Resources) {
  const markers = [
    { key: 'ore', className: 'ore', icon: 'ore' as const, value: resources.ore, label: `광석 트랙 ${resources.ore}` },
    { key: 'knowledge', className: 'knowledge', icon: 'knowledge' as const, value: resources.knowledge, label: `지식 트랙 ${resources.knowledge}` },
    {
      key: 'credits-primary',
      className: 'credits',
      icon: 'credits' as const,
      value: Math.min(resources.credits, 15),
      label: `크레딧 첫 번째 마커 ${Math.min(resources.credits, 15)}`,
    },
    {
      key: 'credits-secondary',
      className: 'credits',
      icon: 'credits' as const,
      value: Math.max(resources.credits - 15, 0),
      label: `크레딧 두 번째 마커 ${Math.max(resources.credits - 15, 0)}`,
    },
  ];

  return markers.map((marker) => {
    const stacked = markers.filter((candidate) => candidate.value === marker.value);
    return {
      ...marker,
      position: resourceTrackPosition(marker.value, stacked.indexOf(marker), stacked.length),
    };
  });
}

function powerTokenPosition(
  index: number,
  count: number,
  bowl: (typeof POWER_BOWLS)[number],
): { left: string; top: string } {
  const row = Math.floor(index / bowl.columns);
  const rowStart = row * bowl.columns;
  const rowLength = Math.min(bowl.columns, count - rowStart);
  const column = index % bowl.columns;
  const xStep = 2.45;
  const yStep = 3.1;

  return {
    left: `${bowl.centerX + (column - (rowLength - 1) / 2) * xStep}%`,
    top: `${bowl.centerY + row * yStep}%`,
  };
}

export function FactionBoard({
  faction,
  structures,
  resources,
  power,
  gaiaformersAvailable = 0,
  techTiles = [],
  advancedTechTiles = [],
  coveredTechTiles = [],
  federationTokens = [],
  grayFederationTokens = [],
  booster = null,
  artifacts = [],
  expensiveTerraformingPlanetTypes = [],
  selectedTinkeringTile = null,
}: Props) {
  const imageSrc = factionBoardImageSrc(faction);
  const color = FACTION_STRUCTURE_COLOR[faction];
  const remainingSlots = remainingFactionBoardStructureSlots(structures, faction);
  const brainstoneBowlKey = power?.brainstone === 'Area1'
    ? 'bowl1'
    : power?.brainstone === 'Area2'
      ? 'bowl2'
      : power?.brainstone === 'Area3'
        ? 'bowl3'
        : power?.brainstone === 'Gaia'
          ? 'gaia_bowl'
          : null;
  const powerBowlCount = (key: (typeof POWER_BOWLS)[number]['key']) => {
    if (!power) return 0;
    return key === 'gaia_bowl'
      ? power.gaia_bowl + power.gaia_forming
      : power[key];
  };

  if (!imageSrc) return null;

  return (
    <figure className="faction-board" aria-label={`${factionDisplayName(faction)} 종족 보드`}>
      {resources && (
        <div className="faction-board-resource-header">
          {(expensiveTerraformingPlanetTypes.length > 0 || selectedTinkeringTile !== null) && (
            <div className="faction-board-special-status">
              {expensiveTerraformingPlanetTypes.length > 0 && (
                <span
                  className="faction-board-expensive-colors"
                  aria-label={`테라포밍 3단계 색상: ${expensiveTerraformingPlanetTypes.map(planetTypeDisplayName).join(', ')}`}
                >
                  <strong>3단계</strong>
                  {expensiveTerraformingPlanetTypes.map((planetType) => {
                    const markerColor = TERRAFORMING_SATELLITE_COLOR[planetType];
                    return markerColor ? (
                      <img
                        key={planetType}
                        src={structureImageSrc(markerColor, 'marker')}
                        alt={`${planetTypeDisplayName(planetType)} 색상 위성`}
                      />
                    ) : null;
                  })}
                </span>
              )}
              {selectedTinkeringTile !== null && (
                <img
                  className="faction-board-current-tinkering-tile"
                  src={tinkeringTileImageSrc(selectedTinkeringTile)}
                  alt={`현재 팅커링 타일 ${selectedTinkeringTile}`}
                />
              )}
            </div>
          )}
          <ResourcePanel resources={resources} placement="faction-board" />
        </div>
      )}
      <div className="faction-board-main">
        <div className="faction-board-image-wrap">
        <img className="faction-board-image" src={imageSrc} alt={`${factionDisplayName(faction)} 종족 보드`} />
        {remainingSlots.map((slot) => (
          <img
            key={slot.id}
            className="faction-board-slot"
            src={structureImageSrc(color, slot.asset)}
            alt=""
            style={{
              left: `${slot.xPct}%`,
              top: `${slot.yPct}%`,
              width: `${slot.widthPct}%`,
            }}
            aria-label={slot.label}
          />
        ))}
        {exposedFactionBoardStructureSlots(structures, faction).map(slot => (
          <span
            key={`income-${slot.id}`}
            className="faction-board-exposed-income"
            data-tutorial-target="income:building"
            aria-label={`${slot.label} 자리의 수입 아이콘`}
            style={{ left: `${slot.xPct}%`, top: `${slot.yPct}%`, width: `${slot.widthPct}%` }}
          />
        ))}
        {resources && (
          <>
            {resourceTrackMarkers(resources).map((marker) => (
              <GamePieceIcon
                key={marker.key}
                className={`faction-board-resource-marker faction-board-resource-marker--${marker.className}`}
                kind={marker.icon as GamePieceIconKind}
                style={marker.position}
                decorative={false}
                label={marker.label}
              />
            ))}
          </>
        )}
        {power && POWER_BOWLS.map(bowl => (
          <span
            key={`power-region-${bowl.key}`}
            data-tutorial-target={`power:${bowl.label}`}
            aria-hidden="true"
            style={{
              position: 'absolute',
              left: `${bowl.centerX}%`,
              top: `${bowl.centerY}%`,
              width: '13%',
              height: '13%',
              transform: 'translate(-50%, -35%)',
              borderRadius: '50%',
              pointerEvents: 'none',
            }}
          />
        ))}
        {power && POWER_BOWLS.flatMap((bowl) => {
          const count = powerBowlCount(bowl.key);
          return Array.from({ length: count }, (_, index) => (
            <SatelliteToken
              key={`${bowl.key}-${index}`}
              className="faction-board-power-token"
              color={STRUCTURE_COLOR_HEX[color]}
              faction={faction}
              style={powerTokenPosition(index, count, bowl)}
              label={`파워 영역 ${bowl.label} 토큰 ${index + 1}`}
            />
          ));
        })}
        {power && brainstoneBowlKey && (() => {
          const bowl = POWER_BOWLS.find((candidate) => candidate.key === brainstoneBowlKey)!;
          return (
            <GamePieceIcon
              className="faction-board-power-token faction-board-brainstone"
              kind="brainstone"
              style={powerTokenPosition(
                powerBowlCount(bowl.key),
                powerBowlCount(bowl.key) + 1,
                bowl,
              )}
              decorative={false}
              label={`브레인스톤 ${bowl.label} 영역`}
            />
          );
        })()}
        {GAIAFORMER_SLOTS.slice(0, Math.min(gaiaformersAvailable, GAIAFORMER_SLOTS.length))
          .map((slot, index) => (
            <img
              key={`gaiaformer-${index}`}
              className="faction-board-gaiaformer"
              src={structureImageSrc(color, 'gaiaformer')}
              alt=""
              style={{
                left: `${slot.x * 100 / FACTION_BOARD_WIDTH}%`,
                top: `${slot.y * 100 / FACTION_BOARD_HEIGHT}%`,
              }}
              aria-label={`사용 가능한 가이아포머 ${index + 1}`}
            />
          ))}
        </div>
        {resources && (
          <FactionBoardSideRack
            faction={faction}
            qic={resources.qic}
            techTiles={techTiles}
            advancedTechTiles={advancedTechTiles}
            coveredTechTiles={coveredTechTiles}
            federationTokens={federationTokens}
            grayFederationTokens={grayFederationTokens}
            booster={booster}
            artifacts={artifacts}
          />
        )}
      </div>
    </figure>
  );
}
