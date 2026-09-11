import type { PlayerId } from '../types/game';
import type { ReplayFrame } from './records';

/** Only navigation is filtered; callers still render the original complete snapshot. */
export function adjacentReplayFrame(
  frames: readonly ReplayFrame[],
  cursor: number,
  direction: -1 | 1,
  player: PlayerId | null,
): number | null {
  for (let index = cursor + direction; index >= 0 && index < frames.length; index += direction) {
    // Keep the initial, pre-action state reachable even when filtering one faction.
    if (index === 0 || player === null || (frames[index].player === player && frames[index].action !== null)) {
      return index;
    }
  }
  return null;
}
