import type { PlayerId } from '../types/game';
import type { ReplayFrame } from './records';

/** Round transitions already include the recorded income/phase state; never synthesize a frame. */
export function replayRoundStarts(frames: readonly ReplayFrame[]): { round: number; cursor: number }[] {
  const starts = new Map<number, number>();
  frames.forEach((frame, cursor) => {
    const round = frame.state.round;
    if (round >= 1 && round <= 6 && !starts.has(round)) starts.set(round, cursor);
  });
  return [...starts].map(([round, cursor]) => ({ round, cursor }));
}

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
