import { createContext, useContext } from 'react';
import type { ReplayFrame } from './records';
import { ACTION_NAMES } from './records';

export interface ReplayHighlight {
  player: number | null;
  faction: string | null;
  standardTech: Set<number>;
  advancedTech: Set<number>;
  actionType: string;
  label: string;
  hexes: Set<string>;
  research: Set<string>;
  powerAction: number | null;
  ship: string | null;
  booster: number | null;
}
export const ReplayHighlightContext = createContext<ReplayHighlight | null>(null);
export const useReplayHighlight = () => useContext(ReplayHighlightContext);
const BUILDINGS: Record<string, string> = {
  Mine: '광산', TradingStation: '교역소', ResearchLab: '연구소', PlanetaryInstitute: '행성의회', Academy: '아카데미', GaiaFormer: '가이아포머',
};
function building(value: unknown): string {
  const key = typeof value === 'string' ? value : value && typeof value === 'object' ? Object.keys(value)[0] : '';
  return BUILDINGS[key] ?? key;
}
export function replayHighlight(frame: ReplayFrame, previous?: ReplayFrame): ReplayHighlight {
  const action = frame.action;
  const hexes = new Set<string>();
  // Action coordinates identify targets without confusing round-transition changes with this move.
  function collect(value: unknown) {
    if (!value || typeof value !== 'object') return;
    if (Array.isArray(value)) { value.forEach(collect); return; }
    const obj = value as Record<string, unknown>;
    if (Number.isInteger(obj.q) && Number.isInteger(obj.r)) hexes.add(`${obj.q},${obj.r}`);
    else Object.values(obj).forEach(collect);
  }
  collect(action);
  let label = action ? ACTION_NAMES[action.type] ?? action.type : '';
  const before = previous?.state.players.find(p => p.player_id === frame.player);
  const after = frame.state.players.find(p => p.player_id === frame.player);
  const research = new Set<string>();
  const standardTech = new Set(after?.tech_tiles?.filter(id => !before?.tech_tiles?.includes(id)) ?? []);
  const advancedTech = new Set(after?.advanced_tech_tiles?.filter(id => !before?.advanced_tech_tiles?.includes(id)) ?? []);
  if (!action) { standardTech.clear(); advancedTech.clear(); }
  if (action?.type === 'TechTileSpecialAction' && action.tile && typeof action.tile === 'object') {
    const tile = action.tile as { pool?: string; tile?: number };
    if (typeof tile.tile === 'number') {
      if (tile.pool === 'Standard') standardTech.add(tile.tile);
      if (tile.pool === 'Advanced') advancedTech.add(tile.tile);
    }
  }
  if (action && before && after) {
    for (const key of Object.keys(after.research_tracks) as (keyof typeof after.research_tracks)[]) {
      if (before.research_tracks[key] !== after.research_tracks[key]) research.add(key);
    }
    // Includes the origin of PI swaps as well as their explicitly supplied destination.
    for (const structure of [...before.structures, ...after.structures]) {
      const key = `${structure.hex.q},${structure.hex.r}`;
      const old = before.structures.find(s => s.hex.q === structure.hex.q && s.hex.r === structure.hex.r);
      const next = after.structures.find(s => s.hex.q === structure.hex.q && s.hex.r === structure.hex.r);
      if (JSON.stringify(old?.kind) !== JSON.stringify(next?.kind)) hexes.add(key);
    }
    if (action.type === 'Upgrade') {
      const coord = action.coord as { q: number; r: number } | undefined;
      const old = before.structures.find(s => s.hex.q === coord?.q && s.hex.r === coord?.r);
      label = `${building(old?.kind)} → ${building(action.to)}`;
    }
  }
  return { player: frame.player, faction: after?.faction ?? null, standardTech, advancedTech, actionType: action?.type ?? '', label, hexes, research,
    powerAction: action?.type === 'PowerAction' && typeof action.id === 'number' ? action.id : null,
    booster: ['Pass', 'SelectStartingBooster'].includes(action?.type ?? '') && typeof action?.booster_id === 'number' ? action.booster_id : null,
    ship: typeof action?.ship === 'string' ? action.ship : null };
}
