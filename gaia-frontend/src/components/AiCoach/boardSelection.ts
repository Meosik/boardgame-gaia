import type { HexCoord, ResearchTrack } from '../../types/game';
import type { Candidate } from './protocol';

/** Selection-only adapter. It has no command transport or approval capability. */
export interface CoachBoardControls {
  enabled: boolean;
  targets: HexCoord[];
  onHex: (coord: HexCoord) => void;
  onAction: (action: Record<string, unknown>) => void;
  onTypes: (types: string[]) => void;
  onTech: (tile: number, advanced?: boolean) => void;
  onTrack: (track: ResearchTrack) => void;
  techMode: 'tile' | 'track' | null;
  standardTiles: number[];
  advancedTracks: ResearchTrack[];
  advancedTiles: number[];
  researchTracks: ResearchTrack[];
  boosterSelection: boolean;
  federationSelection: boolean;
}

export function matchesAction(actual: unknown, partial: unknown): boolean {
  if (partial === null || typeof partial !== 'object') return actual === partial;
  if (actual === null || typeof actual !== 'object') return false;
  if (Array.isArray(partial)) return Array.isArray(actual) && partial.length === actual.length
    && partial.every((v, i) => matchesAction(actual[i], v));
  return Object.entries(partial).every(([key, value]) =>
    matchesAction((actual as Record<string, unknown>)[key], value));
}

export function candidateCoordinates(candidate: Candidate): HexCoord[] {
  const result: HexCoord[] = [];
  function visit(value: unknown) {
    if (!value || typeof value !== 'object') return;
    if ('q' in value && 'r' in value && typeof value.q === 'number' && typeof value.r === 'number') {
      result.push({ q: value.q, r: value.r }); return;
    }
    Object.values(value).forEach(visit);
  }
  visit(candidate.action);
  return result;
}
