import { createContext, useContext } from 'react';
import type { HexCoord } from '../types/game';

/** Replay hex-marking mode: while provided, board clicks mark hexes instead of acting. */
export interface ReplayMarks {
  /** Map hex `q,r` -> short label drawn on that hex. */
  marks: Record<string, string>;
  onHexMark(coord: HexCoord): void;
}
export const ReplayMarksContext = createContext<ReplayMarks | null>(null);
export const useReplayMarks = () => useContext(ReplayMarksContext);
