import type { AcademyType, Structure } from '../../types/game';

export type FactionBoardSupplyAsset =
  | 'mine'
  | 'trading_station'
  | 'research_lab'
  | 'planetary_institute'
  | 'academy';

export interface FactionBoardStructureSlot {
  id: string;
  asset: FactionBoardSupplyAsset;
  label: string;
  xPct: number;
  yPct: number;
  widthPct: number;
  academyType?: AcademyType;
}

const BOARD_WIDTH = 2323;
const BOARD_HEIGHT = 1489;

function xPct(sourceX: number): number {
  return (sourceX / BOARD_WIDTH) * 100;
}

function yPct(sourceY: number): number {
  return (sourceY / BOARD_HEIGHT) * 100;
}

function widthPct(sourceWidth: number): number {
  return (sourceWidth / BOARD_WIDTH) * 100;
}

function rowSlots(
  prefix: string,
  asset: FactionBoardSupplyAsset,
  label: string,
  centers: readonly number[],
  sourceY: number,
  sourceWidth: number,
): FactionBoardStructureSlot[] {
  return centers.map((sourceX, index) => ({
    id: `${prefix}-${index + 1}`,
    asset,
    label: `${label} 보유 ${index + 1}`,
    xPct: xPct(sourceX),
    yPct: yPct(sourceY),
    widthPct: widthPct(sourceWidth),
  }));
}

const MINE_SLOTS = rowSlots(
  'mine',
  'mine',
  '광산',
  [328.8, 447.7, 562.5, 686.1, 803.2, 923, 1038.9, 1155.7],
  1347.7,
  100,
);

const TRADING_STATION_SLOTS = rowSlots(
  'trading-station',
  'trading_station',
  '교역소',
  [326.4, 444.4, 562.7, 679.6],
  1080.8,
  125,
);

const RESEARCH_LAB_SLOTS = rowSlots(
  'research-lab',
  'research_lab',
  '연구소',
  [1162.3, 1337.6, 1511.9],
  1089.9,
  120,
);

const PLANETARY_INSTITUTE_SLOT: FactionBoardStructureSlot = {
  id: 'planetary-institute',
  asset: 'planetary_institute',
  label: '행성 의회 보유',
  xPct: xPct(430),
  yPct: yPct(770),
  widthPct: widthPct(270),
};

const ACADEMY_SLOTS: FactionBoardStructureSlot[] = [
  {
    id: 'academy-science',
    asset: 'academy',
    academyType: 'Science',
    label: '과학 아카데미 보유',
    xPct: xPct(1195.1),
    yPct: yPct(778.4),
    widthPct: widthPct(225),
  },
  {
    id: 'academy-qic',
    asset: 'academy',
    academyType: 'Qic',
    label: '정보 큐브 아카데미 보유',
    xPct: xPct(1459.4),
    yPct: yPct(778.4),
    widthPct: widthPct(225),
  },
];

function countBuilt(structures: Structure[], kind: string): number {
  return structures.filter((structure) => structure.kind === kind).length;
}

function hasAcademy(structures: Structure[], academyType: AcademyType): boolean {
  return structures.some(
    (structure) =>
      typeof structure.kind === 'object' && structure.kind.Academy === academyType,
  );
}

export function remainingFactionBoardStructureSlots(
  structures: Structure[],
): FactionBoardStructureSlot[] {
  const remainingMines = MINE_SLOTS.slice(Math.min(countBuilt(structures, 'Mine'), MINE_SLOTS.length));
  const remainingTradingStations = TRADING_STATION_SLOTS.slice(
    Math.min(countBuilt(structures, 'TradingStation'), TRADING_STATION_SLOTS.length),
  );
  const remainingResearchLabs = RESEARCH_LAB_SLOTS.slice(
    Math.min(countBuilt(structures, 'ResearchLab'), RESEARCH_LAB_SLOTS.length),
  );
  const remainingPlanetaryInstitute = countBuilt(structures, 'PlanetaryInstitute') === 0
    ? [PLANETARY_INSTITUTE_SLOT]
    : [];
  const remainingAcademies = ACADEMY_SLOTS.filter(
    (slot) => slot.academyType && !hasAcademy(structures, slot.academyType),
  );

  return [
    ...remainingMines,
    ...remainingTradingStations,
    ...remainingResearchLabs,
    ...remainingPlanetaryInstitute,
    ...remainingAcademies,
  ];
}
