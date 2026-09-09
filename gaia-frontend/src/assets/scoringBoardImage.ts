import scoringBoard from './boards/normalized/scoring_board.webp';

/** The shared Round/Final Scoring board — the fan of 6 wedge slots (one per round, arranged
 * around the round-tracker dial) plus the 2 final-scoring-tile slots below it. */
export function scoringBoardImageSrc(): string {
  return scoringBoard;
}
