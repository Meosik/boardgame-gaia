import type { GameAction, SpaceshipId } from '../types/game';

export interface PowerActionSpace {
  id: number;
  label: string;
  x: number;
  y: number;
}

export interface SpaceshipActionSpace {
  id: number;
  label: string;
  actionTypes: GameAction['type'][];
  primaryActionType: GameAction['type'];
  x: number;
  y: number;
}

/**
 * Physical centers of the seven shared power-action tokens on the research board image
 * (`researchBoardImageSrc()`, normalized to 1209x1300px). Re-measured via the `?calibrate=1`
 * debug tool — each token's 8 octagon-corner points were clicked and averaged to its centroid.
 */
export const POWER_ACTION_SPACES: PowerActionSpace[] = [
  { id: 1, label: '파워 7 → 지식 3', x: 5.97, y: 97.24 },
  { id: 2, label: '파워 5 → 광산 건설', x: 15.18, y: 97.19 },
  { id: 3, label: '파워 4 → 광석 2', x: 24.10, y: 97.18 },
  { id: 4, label: '파워 4 → 크레딧 7', x: 32.90, y: 97.13 },
  { id: 5, label: '파워 4 → 지식 2', x: 41.99, y: 97.30 },
  { id: 6, label: '파워 3 → 광산 건설', x: 50.74, y: 97.22 },
  { id: 7, label: '파워 3 → 파워 토큰 2', x: 59.69, y: 97.36 },
];

/**
 * Appendix II action-token centers, re-measured via the `?calibrate=1` debug tool against the
 * current normalized ship scans (`spaceshipBoardImageSrc`: 2172x724 for Eclipse/T F Mars/Twilight,
 * 2135x736 for Rebellion) — each token's 8 octagon-corner points were clicked and averaged to its
 * centroid, same methodology as `POWER_ACTION_SPACES` above. Shared ids match
 * GameState.used_spaceship_actions and the engine constants.
 */
export const SPACESHIP_ACTION_SPACES: Record<SpaceshipId, SpaceshipActionSpace[]> = {
  Twilight: [
    {
      id: 10,
      label: '연방 토큰 효과 재사용',
      actionTypes: ['TwilightReplayFederationToken'],
      primaryActionType: 'TwilightReplayFederationToken',
      x: 33.15,
      y: 51.00,
    },
    {
      id: 2,
      label: '교역소를 연구소로 무료 업그레이드',
      actionTypes: ['TwilightFreeResearchLab'],
      primaryActionType: 'TwilightFreeResearchLab',
      x: 44.49,
      y: 50.17,
    },
    {
      id: 11,
      label: '+3 사거리 행동',
      actionTypes: [
        'TwilightRangeBuild',
        'TwilightRangeGaiaFormation',
        'TwilightRangeExploreSpaceship',
      ],
      primaryActionType: 'TwilightRangeBuild',
      x: 55.19,
      y: 50.97,
    },
  ],
  Rebellion: [
    {
      id: 12,
      label: '표준 기술 타일 획득',
      actionTypes: ['RebellionGainTechTile'],
      primaryActionType: 'RebellionGainTechTile',
      x: 34.40,
      y: 58.54,
    },
    {
      id: 3,
      label: '광산을 교역소로 무료 업그레이드',
      actionTypes: ['RebellionFreeTradingStation'],
      primaryActionType: 'RebellionFreeTradingStation',
      x: 46.37,
      y: 57.52,
    },
    {
      id: 4,
      label: '크레딧 2 + 정보 큐브 1 획득',
      actionTypes: ['RebellionCreditsAndQic'],
      primaryActionType: 'RebellionCreditsAndQic',
      x: 57.69,
      y: 58.02,
    },
  ],
  TFMars: [
    {
      id: 1,
      label: '크레딧 행동: 테라포밍 1단계 무료 광산',
      actionTypes: ['SpaceshipCreditTerraform'],
      primaryActionType: 'SpaceshipCreditTerraform',
      x: 36.88,
      y: 39.33,
    },
    {
      id: 5,
      label: '기술 타일 수만큼 점수 획득',
      actionTypes: ['TFMarsTechBonus'],
      primaryActionType: 'TFMarsTechBonus',
      x: 48.82,
      y: 39.11,
    },
    {
      id: 6,
      label: '즉시 가이아포밍',
      actionTypes: ['TFMarsGaiaFormation'],
      primaryActionType: 'TFMarsGaiaFormation',
      x: 60.19,
      y: 38.86,
    },
  ],
  Eclipse: [
    {
      id: 7,
      label: '행성 종류 수만큼 점수 획득',
      actionTypes: ['EclipsePlanetTypeBonus'],
      primaryActionType: 'EclipsePlanetTypeBonus',
      x: 38.62,
      y: 42.90,
    },
    {
      id: 8,
      label: '연구 부스트',
      actionTypes: ['EclipseResearchBoost'],
      primaryActionType: 'EclipseResearchBoost',
      x: 51.35,
      y: 43.06,
    },
    {
      id: 9,
      label: '소행성 광산 건설',
      actionTypes: ['EclipseAsteroidMine'],
      primaryActionType: 'EclipseAsteroidMine',
      x: 63.05,
      y: 44.04,
    },
  ],
};

export const SPACESHIP_ACTION_SLOT_BY_TYPE: Partial<Record<GameAction['type'], number>> =
  Object.values(SPACESHIP_ACTION_SPACES)
    .flat()
    .reduce<Partial<Record<GameAction['type'], number>>>((result, space) => {
      for (const actionType of space.actionTypes) result[actionType] = space.id;
      return result;
    }, {});

export const REQUIRED_SPACESHIP_BY_ACTION: Partial<Record<GameAction['type'], SpaceshipId>> =
  Object.entries(SPACESHIP_ACTION_SPACES).reduce<
    Partial<Record<GameAction['type'], SpaceshipId>>
  >((result, [ship, spaces]) => {
    for (const space of spaces) {
      for (const actionType of space.actionTypes) result[actionType] = ship as SpaceshipId;
    }
    return result;
  }, {});

export function isSpaceshipBoardAction(actionType: GameAction['type'] | null): boolean {
  return actionType !== null && REQUIRED_SPACESHIP_BY_ACTION[actionType] !== undefined;
}
