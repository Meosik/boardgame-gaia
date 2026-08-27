import { factionBoardImageSrc } from '../../assets/factionBoardImages';
import { FACTION_STRUCTURE_COLOR, structureImageSrc } from '../../assets/structureImages';
import type { FactionId, Structure } from '../../types/game';

interface Props {
  faction: FactionId;
  structures: Structure[];
}

/**
 * Positions measured directly off `faction_board_01a.jpg` (2323x1489) — every
 * faction board shares this same template (confirmed by comparing 01a/02a/08a
 * side by side; only the artwork and the faction-special-track box differ).
 *
 * Slot counts/values cross-checked against `gaia-engine`'s actual income
 * tables (`rules/engine.rs`) rather than guessed from the art alone:
 * `UNIVERSAL_TRADING_STATION_TABLE = [3, 4, 4, 5]` and
 * `UNIVERSAL_RESEARCH_LAB_TABLE = [1, 1, 1]` match the two printed tracks
 * exactly. The Mine income row (`UNIVERSAL_MINE_TABLE`, 8 entries) and the
 * Academy upgrade-cost box couldn't be pinned down to an unambiguous slot
 * count/position from the scan alone (the printed row has 9 boxes, one
 * blank, for an 8-entry table — position of the blank doesn't resolve
 * cleanly) — left as static art for now rather than risk a wrong marker.
 */
const TRADING_STATION_SLOTS_PCT = [13.99, 19.16, 24.32, 29.49];
const RESEARCH_LAB_SLOTS_PCT = [44.77, 50.15, 55.53];
const STRUCTURE_ROW_Y_PCT = 72.91;
const PLANETARY_INSTITUTE_PCT = { x: 4.31, y: 53.43 };

function countByKind(structures: Structure[], kind: 'TradingStation' | 'ResearchLab' | 'PlanetaryInstitute'): number {
  return structures.filter((s) => s.kind === kind).length;
}

export function FactionBoard({ faction, structures }: Props) {
  const imageSrc = factionBoardImageSrc(faction);
  const tradingStations = countByKind(structures, 'TradingStation');
  const researchLabs = countByKind(structures, 'ResearchLab');
  const hasPlanetaryInstitute = countByKind(structures, 'PlanetaryInstitute') > 0;
  const color = FACTION_STRUCTURE_COLOR[faction];

  if (!imageSrc) return null;

  return (
    <figure className="faction-board" aria-label={`${faction} 종족 보드`}>
      <div className="faction-board-image-wrap">
        <img className="faction-board-image" src={imageSrc} alt={`${faction} 종족 보드`} />
        {TRADING_STATION_SLOTS_PCT.map((xPct, i) =>
          i < tradingStations ? (
            <img
              key={`ts-${i}`}
              className="faction-board-slot"
              src={structureImageSrc(color, 'structure6')}
              alt=""
              style={{ left: `${xPct}%`, top: `${STRUCTURE_ROW_Y_PCT}%` }}
              aria-label={`교역소 수입 ${i + 1} 확보됨`}
            />
          ) : null,
        )}
        {RESEARCH_LAB_SLOTS_PCT.map((xPct, i) =>
          i < researchLabs ? (
            <img
              key={`rl-${i}`}
              className="faction-board-slot"
              src={structureImageSrc(color, 'researchlab')}
              alt=""
              style={{ left: `${xPct}%`, top: `${STRUCTURE_ROW_Y_PCT}%` }}
              aria-label={`연구소 수입 ${i + 1} 확보됨`}
            />
          ) : null,
        )}
        {hasPlanetaryInstitute && (
          <img
            className="faction-board-slot faction-board-slot--large"
            src={structureImageSrc(color, 'planetary_institute')}
            alt=""
            style={{ left: `${PLANETARY_INSTITUTE_PCT.x}%`, top: `${PLANETARY_INSTITUTE_PCT.y}%` }}
            aria-label="행성 의회 건설됨"
          />
        )}
      </div>
    </figure>
  );
}
