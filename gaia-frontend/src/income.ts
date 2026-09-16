import nativeIncome from './data/income.json';
import type { EconomyResearchTileSide, PlayerState } from './types/game';

export interface RecurringIncome {
  ore: number;
  credits: number;
  knowledge: number;
  qic: number;
  power_charge: number;
  power_tokens: number;
  vp: number;
}

type StructureIncome = 'Mine' | 'TradingStation' | 'ResearchLab' | 'PlanetaryInstitute' | 'Science' | 'Qic';
type Vector = readonly number[];
interface IncomeRules {
  factions: Record<string, { base: Vector; structures: Record<StructureIncome, Vector[]> }>;
  boosters: Record<string, Vector>;
  tech: Record<string, Vector>;
  artifacts: Record<string, Vector>;
  economy: Record<EconomyResearchTileSide, Vector[]>;
  science: Vector[];
}
const rules: IncomeRules = nativeIncome;

/** Current production and held booster, not already received resources or future choices.
 * Gross income: future spending/storage caps and power charging order are not predicted.
 * Generated native tables keep faction overrides out of a second handwritten rulebook.
 */
export function projectedIncome(
  player: PlayerState,
  economySide: EconomyResearchTileSide = 'Power',
): RecurringIncome {
  const total = [0, 0, 0, 0, 0, 0, 0];
  const add = (income: Vector | undefined) => {
    income?.forEach((value, index) => { total[index] += value; });
  };
  const faction = player.faction ? rules.factions[player.faction] : undefined;
  if (faction) {
    add(faction.base);
    const counts: Record<StructureIncome, number> = {
      Mine: 0, TradingStation: 0, ResearchLab: 0, PlanetaryInstitute: 0, Science: 0, Qic: 0,
    };
    for (const { kind } of player.structures) {
      const name = typeof kind === 'object' ? kind.Academy : kind;
      if (name in counts) counts[name as StructureIncome] += 1;
    }
    for (const name of Object.keys(counts) as StructureIncome[]) {
      const curve = faction.structures[name];
      add(curve[Math.min(counts[name], curve.length - 1)]);
    }
    add(rules.economy[economySide][player.research_tracks.economy]);
    add(rules.science[player.research_tracks.science]);
    if (player.booster != null) add(rules.boosters[player.booster]);
    const covered = new Set(player.covered_tech_tiles ?? []);
    for (const tile of new Set(player.tech_tiles ?? [])) {
      if (!covered.has(tile)) add(rules.tech[tile]);
    }
    for (const artifact of new Set(player.artifacts ?? [])) add(rules.artifacts[artifact]);
    if (player.faction === 'Gleens' && counts.Qic === 0) {
      total[0] += total[3];
      total[3] = 0;
    }
  }
  const [ore, credits, knowledge, qic, power_charge, power_tokens, vp] = total;
  return { ore, credits, knowledge, qic, power_charge, power_tokens, vp };
}
