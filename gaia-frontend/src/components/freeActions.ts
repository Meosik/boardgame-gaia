import type { FreeActionKind, GameState, PlayerState } from '../types/game';

// Rulebook p.15 free-action conversions — unlike every other action, these don't consume the
// turn, so both ActionPanel and SidebarTurnControls render them as a persistent list (always
// visible on the player's turn) rather than a selectable action that needs a confirm step.
// Shared here so the two panels can't drift apart on cost/faction/count logic.
export type FreeActionResource =
  | 'ore'
  | 'credits'
  | 'knowledge'
  | 'qic'
  | 'bowl2'
  | 'bowl3'
  | 'gaiaformer';

export interface FreeActionOption {
  label: string;
  kind: FreeActionKind;
  cost: { resource: FreeActionResource; amount: number };
  faction?: GameState['players'][number]['faction'];
  requiresPlanetaryInstitute?: boolean;
}

export const MAX_FREE_ACTION_COUNT = 30;

export const FREE_ACTIONS: FreeActionOption[] = [
  {
    label: '파워 희생: 2단계 2개 → 3단계 1개',
    kind: 'BurnPower',
    cost: { resource: 'bowl2', amount: 2 },
  },
  {
    label: '크레딧 4 → 정보 큐브 1 (Hadsch Hallas)',
    kind: 'CreditsToQic',
    cost: { resource: 'credits', amount: 4 },
    faction: 'HadschHallas',
    requiresPlanetaryInstitute: true,
  },
  {
    label: '크레딧 3 → 광석 1 (Hadsch Hallas)',
    kind: 'CreditsToOre',
    cost: { resource: 'credits', amount: 3 },
    faction: 'HadschHallas',
    requiresPlanetaryInstitute: true,
  },
  {
    label: '크레딧 4 → 지식 1 (Hadsch Hallas)',
    kind: 'CreditsToKnowledge',
    cost: { resource: 'credits', amount: 4 },
    faction: 'HadschHallas',
    requiresPlanetaryInstitute: true,
  },
  {
    label: '가이아포머 1 → 정보 큐브 1 (Bal T’aks)',
    kind: 'GaiaformerToQic',
    cost: { resource: 'gaiaformer', amount: 1 },
    faction: 'BalTaks',
  },
  {
    label: '파워 1(3단계) → 가이아 영역 + 지식 1 (Nevlas)',
    kind: 'PowerToGaiaKnowledge',
    cost: { resource: 'bowl3', amount: 1 },
    faction: 'Nevlas',
  },
  {
    label: '광석 1 → 파워 1(3단계) (Xenos)',
    kind: 'OreToPowerBowl3',
    cost: { resource: 'ore', amount: 1 },
    faction: 'Xenos',
  },
  { label: '파워 4 → 정보 큐브 1', kind: 'PowerToQic', cost: { resource: 'bowl3', amount: 4 } },
  { label: '파워 3 → 광석 1', kind: 'PowerToOre', cost: { resource: 'bowl3', amount: 3 } },
  { label: '정보 큐브 1 → 광석 1', kind: 'QicToOre', cost: { resource: 'qic', amount: 1 } },
  {
    label: '파워 4 → 지식 1',
    kind: 'PowerToKnowledge',
    cost: { resource: 'bowl3', amount: 4 },
  },
  {
    label: '파워 1 → 크레딧 1',
    kind: 'PowerToCredit',
    cost: { resource: 'bowl3', amount: 1 },
  },
  {
    label: '지식 1 → 크레딧 1',
    kind: 'KnowledgeToCredit',
    cost: { resource: 'knowledge', amount: 1 },
  },
  { label: '광석 1 → 크레딧 1', kind: 'OreToCredit', cost: { resource: 'ore', amount: 1 } },
  {
    label: '광석 1 → 파워 토큰 1 (1단계)',
    kind: 'OreToPower',
    cost: { resource: 'ore', amount: 1 },
  },
];

export function availableFreeActionResource(
  player: PlayerState | undefined,
  resource: FreeActionResource,
): number {
  if (!player) return 0;
  if (resource === 'gaiaformer') {
    return Math.max(
      0,
      player.gaiaformers_total
        - player.gaiaformers_deployed
        - player.resources.spent_gaia_formers
        - (player.gaiaformers_in_gaia_area ?? 0),
    );
  }
  if (resource === 'bowl2' || resource === 'bowl3') return player.resources.power[resource];
  return player.resources[resource];
}

export function maxFreeActionCount(
  player: PlayerState | undefined,
  option: FreeActionOption,
): number {
  return Math.min(
    MAX_FREE_ACTION_COUNT,
    Math.floor(availableFreeActionResource(player, option.cost.resource) / option.cost.amount),
  );
}

export function isFreeActionAvailableToPlayer(
  player: PlayerState | undefined,
  option: FreeActionOption,
): boolean {
  if (!player || (option.faction && player.faction !== option.faction)) return false;
  if (!option.requiresPlanetaryInstitute) return true;
  return player.structures.some(
    (structure) => structure.kind === 'PlanetaryInstitute',
  );
}
