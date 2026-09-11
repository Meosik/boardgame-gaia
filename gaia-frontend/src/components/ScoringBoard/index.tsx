import type { CSSProperties } from 'react';
import { scoringBoardImageSrc } from '../../assets/scoringBoardImage';
import { roundScoringTileImageSrc, roundScoringTileBackImageSrc } from '../../assets/roundScoringTileImages';
import { finalScoringTileImageSrc } from '../../assets/finalScoringTileImages';
import type { FinalScoringTile, RoundTile } from '../../types/game';

interface Props {
  roundTiles: RoundTile[];
  finalScoringTiles: FinalScoringTile[];
  /** 0 = nothing has been played yet (pre-game preview); otherwise the round currently in
   * progress (1-6) — every tile for a round below this has already been played and flips. */
  currentRound: number;
}

interface Point {
  x: number;
  y: number;
}

const BOARD_WIDTH = 1254;
const BOARD_HEIGHT = 1254;
const ROUND_TILE_WIDTH = 1174;
const ROUND_TILE_HEIGHT = 1340;
const FINAL_TILE_WIDTH = 1624;
const FINAL_TILE_HEIGHT = 1072;
const TRIANGLE_OVERLAP_PX = 3;

/** User-calibrated corners on the current 1254x1254 scoring board.
 * Each entry is [outerStart, outerEnd, innerEnd, innerStart]. */
const ROUND_SLOT_CORNERS: Point[][] = [
  [
    { x: 202, y: 593 },
    { x: 260, y: 383 },
    { x: 472, y: 504 },
    { x: 449, y: 596 },
  ],
  [
    { x: 262, y: 375 },
    { x: 414, y: 223 },
    { x: 536, y: 435 },
    { x: 472, y: 498 },
  ],
  [
    { x: 421, y: 220 },
    { x: 627, y: 166 },
    { x: 631, y: 412 },
    { x: 541, y: 434 },
  ],
  [
    { x: 636, y: 166 },
    { x: 846, y: 214 },
    { x: 722, y: 432 },
    { x: 633, y: 410 },
  ],
  [
    { x: 851, y: 222 },
    { x: 998, y: 378 },
    { x: 791, y: 504 },
    { x: 726, y: 435 },
  ],
  [
    { x: 1001, y: 384 },
    { x: 1061, y: 597 },
    { x: 814, y: 594 },
    { x: 795, y: 508 },
  ],
];

const ROUND_TILE_CORNERS: Point[] = [
  { x: 0, y: 66.33 },
  { x: ROUND_TILE_WIDTH - 1, y: 66.33 },
  { x: 842.4, y: 1293.4 },
  { x: 331.65, y: 1293.4 },
];

const FINAL_SLOT_CORNERS: Point[][] = [
  [
    { x: 738.12, y: 613.86 },
    { x: 979.24, y: 613.78 },
    { x: 979.09, y: 766.87 },
    { x: 738.61, y: 766.81 },
  ],
  [
    { x: 738.23, y: 850.35 },
    { x: 979.33, y: 850.36 },
    { x: 979.04, y: 1002.85 },
    { x: 731.23, y: 1003.13 },
  ],
];

const FINAL_TILE_CORNERS: Point[] = [
  { x: 0, y: 0 },
  { x: FINAL_TILE_WIDTH - 1, y: 0 },
  { x: FINAL_TILE_WIDTH - 1, y: FINAL_TILE_HEIGHT - 1 },
  { x: 0, y: FINAL_TILE_HEIGHT - 1 },
];

function solveLinearSystem(rows: number[][]): number[] {
  const size = rows.length;
  for (let column = 0; column < size; column += 1) {
    let pivot = column;
    for (let row = column + 1; row < size; row += 1) {
      if (Math.abs(rows[row][column]) > Math.abs(rows[pivot][column])) pivot = row;
    }
    [rows[column], rows[pivot]] = [rows[pivot], rows[column]];

    const divisor = rows[column][column];
    if (Math.abs(divisor) < 1e-10) return [];
    for (let entry = column; entry <= size; entry += 1) rows[column][entry] /= divisor;

    for (let row = 0; row < size; row += 1) {
      if (row === column) continue;
      const factor = rows[row][column];
      for (let entry = column; entry <= size; entry += 1) {
        rows[row][entry] -= factor * rows[column][entry];
      }
    }
  }
  return rows.map((row) => row[size]);
}

function affinePieceStyle(
  source: Point[],
  target: Point[],
  sourceWidth: number,
  sourceHeight: number,
): CSSProperties {
  const rows: number[][] = [];
  source.forEach(({ x, y }, index) => {
    const { x: targetX, y: targetY } = target[index];
    rows.push([x, y, 1, 0, 0, 0, targetX]);
    rows.push([0, 0, 0, x, y, 1, targetY]);
  });
  const [a, c, left, b, d, top] = solveLinearSystem(rows);
  const center = source.reduce(
    (sum, point) => ({ x: sum.x + point.x / source.length, y: sum.y + point.y / source.length }),
    { x: 0, y: 0 },
  );
  const clipPath = `polygon(${source
    .map((point) => {
      const offsetX = point.x - center.x;
      const offsetY = point.y - center.y;
      const length = Math.hypot(offsetX, offsetY) || 1;
      const x = point.x + (offsetX / length) * TRIANGLE_OVERLAP_PX;
      const y = point.y + (offsetY / length) * TRIANGLE_OVERLAP_PX;
      return `${(x / sourceWidth) * 100}% ${(y / sourceHeight) * 100}%`;
    })
    .join(', ')})`;

  return {
    left: `${(left / BOARD_WIDTH) * 100}%`,
    top: `${(top / BOARD_HEIGHT) * 100}%`,
    width: `${(sourceWidth / BOARD_WIDTH) * 100}%`,
    height: `${(sourceHeight / BOARD_HEIGHT) * 100}%`,
    clipPath,
    transform: `matrix(${a}, ${b}, ${c}, ${d}, 0, 0)`,
  };
}

function finalTilePieces(src: string, targetCorners: Point[], alt: string) {
  const triangles = [
    [0, 1, 2],
    [0, 2, 3],
  ];
  return triangles.map((indices, pieceIndex) => (
    <img
      key={pieceIndex}
      className="scoring-board-warped-piece"
      style={affinePieceStyle(
        indices.map((index) => FINAL_TILE_CORNERS[index]),
        indices.map((index) => targetCorners[index]),
        FINAL_TILE_WIDTH,
        FINAL_TILE_HEIGHT,
      )}
      src={src}
      alt={pieceIndex === 0 ? alt : ''}
    />
  ));
}

/** Best-fit rotation and uniform scale for the calibrated corners. Unlike a projective warp,
 * this preserves the tile artwork's proportions while retaining the mapped slot position. */
function roundTileStyle(targetCorners: Point[]): CSSProperties {
  const sourceCenter = ROUND_TILE_CORNERS.reduce(
    (sum, point) => ({
      x: sum.x + point.x / ROUND_TILE_CORNERS.length,
      y: sum.y + point.y / ROUND_TILE_CORNERS.length,
    }),
    { x: 0, y: 0 },
  );
  const targetCenter = targetCorners.reduce(
    (sum, point) => ({
      x: sum.x + point.x / targetCorners.length,
      y: sum.y + point.y / targetCorners.length,
    }),
    { x: 0, y: 0 },
  );

  let denominator = 0;
  let aNumerator = 0;
  let bNumerator = 0;
  ROUND_TILE_CORNERS.forEach((source, index) => {
    const target = targetCorners[index];
    const sourceX = source.x - sourceCenter.x;
    const sourceY = source.y - sourceCenter.y;
    const targetX = target.x - targetCenter.x;
    const targetY = target.y - targetCenter.y;
    denominator += sourceX * sourceX + sourceY * sourceY;
    aNumerator += sourceX * targetX + sourceY * targetY;
    bNumerator += sourceX * targetY - sourceY * targetX;
  });

  const a = aNumerator / denominator;
  const b = bNumerator / denominator;
  const left = targetCenter.x - a * sourceCenter.x + b * sourceCenter.y;
  const top = targetCenter.y - b * sourceCenter.x - a * sourceCenter.y;

  return {
    left: `${(left / BOARD_WIDTH) * 100}%`,
    top: `${(top / BOARD_HEIGHT) * 100}%`,
    width: `${(ROUND_TILE_WIDTH / BOARD_WIDTH) * 100}%`,
    height: `${(ROUND_TILE_HEIGHT / BOARD_HEIGHT) * 100}%`,
    transform: `matrix(${a}, ${b}, ${-b}, ${a}, 0, 0)`,
    transformOrigin: '0 0',
  };
}

export function ScoringBoard({ roundTiles, finalScoringTiles, currentRound }: Props) {
  return (
    <section className="scoring-board" aria-label="점수 보드">
      <div className="scoring-board-image-wrap">
        <img className="scoring-board-image" src={scoringBoardImageSrc()} alt="점수 보드" />
        {roundTiles.map((tile, index) => {
          const round = index + 1;
          const slot = ROUND_SLOT_CORNERS[index];
          const src = roundScoringTileImageSrc(tile.id);
          if (!slot || !src) return null;
          const passed = currentRound > 0 && round < currentRound;

          return (
            <div
              key={`round-${round}`}
              className={`scoring-board-tile scoring-board-tile--round ${passed ? 'scoring-board-tile--flipped' : ''}`}
              style={roundTileStyle(slot)}
              aria-label={`라운드 ${round} 점수 타일${passed ? ' (완료됨)' : ''}`}
            >
              <div className="scoring-board-tile-inner">
                <img
                  className="scoring-board-tile-face scoring-board-tile-front"
                  src={src}
                  alt={`라운드 ${round}`}
                />
                <img className="scoring-board-tile-face scoring-board-tile-back" src={roundScoringTileBackImageSrc} alt="" />
              </div>
            </div>
          );
        })}
        {finalScoringTiles.map((tile, index) => {
          const slot = FINAL_SLOT_CORNERS[index];
          const src = finalScoringTileImageSrc(tile.id);
          if (!slot || !src) return null;
          return (
            <div key={`final-${tile.id}`} className="scoring-board-tile scoring-board-tile--final">
              {finalTilePieces(src, slot, `게임 종료 점수 타일 ${index + 1}`)}
            </div>
          );
        })}
      </div>
    </section>
  );
}
