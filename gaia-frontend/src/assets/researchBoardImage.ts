import researchBoard from './boards/normalized/research_board.webp';

/** The single shared Research Board (rulebook p.8) — one physical board, not per-faction. */
export function researchBoardImageSrc(): string {
  return researchBoard;
}
