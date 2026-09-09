import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { scoringBoardImageSrc } from '../../assets/scoringBoardImage';
import { roundScoringTileImageSrc } from '../../assets/roundScoringTileImages';
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

// The board scan was re-exported square (1254x1254) — the previous 2104x2130 canvas this whole
// file's geometry was measured against no longer matches, so every constant below was re-derived
// against the current scan rather than reused. `ROUND_TILE_WIDTH/HEIGHT` and
// `FINAL_TILE_WIDTH/HEIGHT` still track their own source tile images 1:1 (both were re-exported
// at a uniformly larger, same-aspect-ratio size — 1174x1340 and 1624x1072 respectively — so only
// the raw dimensions needed updating, not the shape math built on them).
const BOARD_WIDTH = 1254;
const BOARD_HEIGHT = 1254;
const ROUND_TILE_WIDTH = 1174;
const ROUND_TILE_HEIGHT = 1340;
const FINAL_TILE_WIDTH = 1624;
const FINAL_TILE_HEIGHT = 1072;
const QUAD_TRIANGLES = [
  [0, 1, 2],
  [0, 2, 3],
] as const;
const ROUND_TILE_TRIANGLES = [
  [0, 1, 4],
  [1, 3, 4],
  [1, 2, 3],
] as const;
// The 6 round-tile wedges fan out symmetrically around this center — re-measured by fitting a
// circle through the 6 printed slot-number badges' centers (the inner radius) via the
// `?calibrate=1` debug tool, then reading the fan's own outer rim along its vertical symmetry
// axis for the outer radius. `BOARD_RING_RADIUS` is that outer radius, used both to place each
// wedge's outer corners and to bow its outer edge outward via `outerArcMidpoint`.
const BOARD_RING_CENTER = { x: 715.7, y: 756.9 };
const BOARD_RING_RADIUS = 575.0;
const TRIANGLE_OVERLAP_PX = 3;

/** The 6 wedges' corners — computed from `BOARD_RING_CENTER`, an inner radius of 231.4 (the
 * slot-number badge ring), `BOARD_RING_RADIUS` as the outer radius, and 6 equal 24.858°-wide
 * wedges centered on the fan's vertical symmetry axis (measured the same way as the ring
 * center/radii above). Each entry is [outerStart, outerEnd, innerEnd, innerStart]. */
const ROUND_SLOT_CORNERS: Point[][] = [
  [
    { x: 161.41, y: 603.95 },
    { x: 277.06, y: 385.12 },
    { x: 539.18, y: 607.28 },
    { x: 492.64, y: 695.35 },
  ],
  [
    { x: 277.06, y: 385.12 },
    { x: 473.99, y: 235.17 },
    { x: 618.43, y: 546.94 },
    { x: 539.18, y: 607.28 },
  ],
  [
    { x: 473.99, y: 235.17 },
    { x: 715.7, y: 181.9 },
    { x: 715.7, y: 525.5 },
    { x: 618.43, y: 546.94 },
  ],
  [
    { x: 715.7, y: 181.9 },
    { x: 957.41, y: 235.17 },
    { x: 812.97, y: 546.94 },
    { x: 715.7, y: 525.5 },
  ],
  [
    { x: 957.41, y: 235.17 },
    { x: 1154.34, y: 385.12 },
    { x: 892.22, y: 607.28 },
    { x: 812.97, y: 546.94 },
  ],
  [
    { x: 1154.34, y: 385.12 },
    { x: 1269.99, y: 603.95 },
    { x: 938.76, y: 695.35 },
    { x: 892.22, y: 607.28 },
  ],
];

// Scaled from the previous 177x202-canvas outline by the same ~6.633x factor the tile image
// itself was re-exported at (1174/177 = 1340/202, confirming a uniform upscale — see the comment
// on `ROUND_TILE_WIDTH` above).
const ROUND_TILE_OUTLINE = [
  { x: 0, y: 66.33 },
  { x: ROUND_TILE_WIDTH / 2, y: 0 },
  { x: ROUND_TILE_WIDTH - 1, y: 66.33 },
  { x: 842.4, y: 1293.4 },
  { x: 331.65, y: 1293.4 },
];

function outerArcMidpoint(start: Point, end: Point): Point {
  const chordMidpoint = {
    x: (start.x + end.x) / 2,
    y: (start.y + end.y) / 2,
  };
  const offset = {
    x: chordMidpoint.x - BOARD_RING_CENTER.x,
    y: chordMidpoint.y - BOARD_RING_CENTER.y,
  };
  const scale = BOARD_RING_RADIUS / Math.hypot(offset.x, offset.y);
  return {
    x: BOARD_RING_CENTER.x + offset.x * scale,
    y: BOARD_RING_CENTER.y + offset.y * scale,
  };
}

const ROUND_SLOT_OUTLINES = ROUND_SLOT_CORNERS.map(
  ([outerStart, outerEnd, innerEnd, innerStart]) => [
    outerStart,
    outerArcMidpoint(outerStart, outerEnd),
    outerEnd,
    innerEnd,
    innerStart,
  ],
);

// TODO: rough-scaled from the old 2104x2130-canvas corners by independent x/y axis factors
// (0.596, 0.5887) rather than re-measured directly off the current 1254x1254 scan like
// `ROUND_SLOT_CORNERS` above — those two axis factors are close but not identical, so this is an
// approximation good enough to stop the final-scoring tiles rendering off-board, not a precise
// calibration. Re-measure via `?calibrate=1` if these look off in practice.
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

const FINAL_TILE_CANVAS = [
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

function projectiveTransform(from: Point[], to: Point[]): Float32Array {
  const rows: number[][] = [];
  from.forEach(({ x, y }, index) => {
    const { x: targetX, y: targetY } = to[index];
    rows.push([x, y, 1, 0, 0, 0, -targetX * x, -targetX * y, targetX]);
    rows.push([0, 0, 0, x, y, 1, -targetY * x, -targetY * y, targetY]);
  });
  const [h0, h1, h2, h3, h4, h5, h6, h7] = solveLinearSystem(rows);
  return new Float32Array([
    h0, h3, h6,
    h1, h4, h7,
    h2, h5, 1,
  ]);
}

function warpedPieceStyle(
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
  const overlappingClip = source.map((point) => {
    const offsetX = point.x - center.x;
    const offsetY = point.y - center.y;
    const length = Math.hypot(offsetX, offsetY) || 1;
    return {
      x: point.x + (offsetX / length) * TRIANGLE_OVERLAP_PX,
      y: point.y + (offsetY / length) * TRIANGLE_OVERLAP_PX,
    };
  });
  const clipPath = `polygon(${overlappingClip
    .map(({ x, y }) => `${(x / sourceWidth) * 100}% ${(y / sourceHeight) * 100}%`)
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

interface WarpedTileProps {
  sourceCorners: Point[];
  targetCorners: Point[];
  sourceWidth: number;
  sourceHeight: number;
  src?: string;
  alt?: string;
}

function WarpedTile({
  sourceCorners,
  targetCorners,
  sourceWidth,
  sourceHeight,
  src,
  alt = '',
}: WarpedTileProps) {
  const triangles = sourceCorners.length === 5 ? ROUND_TILE_TRIANGLES : QUAD_TRIANGLES;
  return triangles.map((indices, pieceIndex) => {
    const source = indices.map((index) => sourceCorners[index]);
    const target = indices.map((index) => targetCorners[index]);
    const style = warpedPieceStyle(source, target, sourceWidth, sourceHeight);
    return (
      <img
        key={pieceIndex}
        className="scoring-board-warped-piece"
        style={style}
        src={src}
        alt={pieceIndex === 0 ? alt : ''}
      />
    );
  });
}

interface RoundCanvasTile {
  src: string;
  targetCorners: Point[];
}

function compileShader(
  gl: WebGLRenderingContext,
  type: number,
  source: string,
): WebGLShader | null {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    gl.deleteShader(shader);
    return null;
  }
  return shader;
}

function createRoundTileProgram(gl: WebGLRenderingContext): WebGLProgram | null {
  const vertexShader = compileShader(
    gl,
    gl.VERTEX_SHADER,
    `
      attribute vec2 a_position;
      varying vec2 v_position;

      void main() {
        vec2 clip = vec2(
          (a_position.x / ${BOARD_WIDTH.toFixed(1)}) * 2.0 - 1.0,
          1.0 - (a_position.y / ${BOARD_HEIGHT.toFixed(1)}) * 2.0
        );
        gl_Position = vec4(clip, 0.0, 1.0);
        v_position = a_position;
      }
    `,
  );
  const fragmentShader = compileShader(
    gl,
    gl.FRAGMENT_SHADER,
    `
      precision mediump float;
      varying vec2 v_position;
      uniform sampler2D u_texture;
      uniform mat3 u_targetToSource;

      void main() {
        vec3 source = u_targetToSource * vec3(v_position, 1.0);
        vec2 texCoord = (source.xy / source.z) / vec2(
          ${ROUND_TILE_WIDTH.toFixed(1)},
          ${ROUND_TILE_HEIGHT.toFixed(1)}
        );
        gl_FragColor = texture2D(u_texture, texCoord);
      }
    `,
  );
  if (!vertexShader || !fragmentShader) return null;

  const program = gl.createProgram();
  if (!program) return null;
  gl.attachShader(program, vertexShader);
  gl.attachShader(program, fragmentShader);
  gl.linkProgram(program);
  gl.deleteShader(vertexShader);
  gl.deleteShader(fragmentShader);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    gl.deleteProgram(program);
    return null;
  }
  return program;
}

function loadTileImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error(`Failed to load scoring tile: ${src}`));
    image.src = src;
  });
}

function RoundTilesCanvas({ tiles }: { tiles: RoundCanvasTile[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    setIsReady(false);
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    if (typeof WebGLRenderingContext === 'undefined') return undefined;
    const gl = canvas.getContext('webgl', { alpha: true, antialias: true });
    if (!gl) return undefined;

    let cancelled = false;
    const program = createRoundTileProgram(gl);
    if (!program) return undefined;

    const positionLocation = gl.getAttribLocation(program, 'a_position');
    const transformLocation = gl.getUniformLocation(program, 'u_targetToSource');
    const positionBuffer = gl.createBuffer();
    const indexBuffer = gl.createBuffer();
    if (!transformLocation || !positionBuffer || !indexBuffer) {
      gl.deleteProgram(program);
      return undefined;
    }

    const indices = new Uint16Array(ROUND_TILE_TRIANGLES.flatMap((triangle) => [...triangle]));

    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, indices, gl.STATIC_DRAW);
    gl.viewport(0, 0, BOARD_WIDTH, BOARD_HEIGHT);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.useProgram(program);

    void Promise.all(tiles.map(async (tile) => ({ ...tile, image: await loadTileImage(tile.src) })))
      .then((loadedTiles) => {
        if (cancelled) return;
        loadedTiles.forEach(({ image, targetCorners }) => {
          const texture = gl.createTexture();
          if (!texture) return;
          gl.bindTexture(gl.TEXTURE_2D, texture);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
          gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);

          gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
          gl.bufferData(
            gl.ARRAY_BUFFER,
            new Float32Array(targetCorners.flatMap(({ x, y }) => [x, y])),
            gl.STREAM_DRAW,
          );
          gl.enableVertexAttribArray(positionLocation);
          gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);

          const quadIndices = [0, 2, 3, 4];
          const targetQuad = quadIndices.map((index) => targetCorners[index]);
          const sourceQuad = quadIndices.map((index) => ROUND_TILE_OUTLINE[index]);
          gl.uniformMatrix3fv(
            transformLocation,
            false,
            projectiveTransform(targetQuad, sourceQuad),
          );
          gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
          gl.drawElements(gl.TRIANGLES, indices.length, gl.UNSIGNED_SHORT, 0);
          gl.deleteTexture(texture);
        });
        setIsReady(true);
      })
      .catch(() => {
        if (!cancelled) setIsReady(false);
      });

    return () => {
      cancelled = true;
      gl.deleteBuffer(positionBuffer);
      gl.deleteBuffer(indexBuffer);
      gl.deleteProgram(program);
    };
  }, [tiles]);

  return (
    <>
      <div
        className={`scoring-board-round-fallback ${isReady ? 'scoring-board-round-fallback--hidden' : ''}`}
        aria-hidden="true"
      >
        {tiles.map(({ src, targetCorners }, tileIndex) => (
          <WarpedTile
            key={`${src}-${tileIndex}`}
            sourceCorners={ROUND_TILE_OUTLINE}
            targetCorners={targetCorners}
            sourceWidth={ROUND_TILE_WIDTH}
            sourceHeight={ROUND_TILE_HEIGHT}
            src={src}
          />
        ))}
      </div>
      <canvas
        ref={canvasRef}
        className="scoring-board-round-canvas"
        width={BOARD_WIDTH}
        height={BOARD_HEIGHT}
        aria-hidden="true"
      />
    </>
  );
}

function roundTileBackStyle(targetCorners: Point[]): CSSProperties {
  return {
    clipPath: `polygon(${targetCorners
      .map(({ x, y }) => `${(x / BOARD_WIDTH) * 100}% ${(y / BOARD_HEIGHT) * 100}%`)
      .join(', ')})`,
  };
}

export function ScoringBoard({ roundTiles, finalScoringTiles, currentRound }: Props) {
  const visibleRoundTiles = roundTiles.flatMap((tile, index): RoundCanvasTile[] => {
    const round = index + 1;
    const slot = ROUND_SLOT_OUTLINES[index];
    const src = roundScoringTileImageSrc(tile.id);
    const passed = currentRound > 0 && round < currentRound;
    return slot && src && !passed ? [{ src, targetCorners: slot }] : [];
  });

  return (
    <section className="scoring-board" aria-label="점수 보드">
      <div className="scoring-board-image-wrap">
        <img className="scoring-board-image" src={scoringBoardImageSrc()} alt="점수 보드" />
        {roundTiles.map((tile, index) => {
          const round = index + 1;
          const passed = currentRound > 0 && round < currentRound;
          const slot = ROUND_SLOT_OUTLINES[index];
          const src = roundScoringTileImageSrc(tile.id);
          if (!slot || !src) return null;
          return (
            <div
              key={`round-${round}`}
              className={`scoring-board-tile scoring-board-tile--round ${passed ? 'scoring-board-tile--flipped' : ''}`}
              aria-label={`라운드 ${round} 점수 타일${passed ? ' (완료됨)' : ''}`}
            >
              {passed ? (
                <div className="scoring-board-round-back" style={roundTileBackStyle(slot)} />
              ) : null}
            </div>
          );
        })}
        <RoundTilesCanvas tiles={visibleRoundTiles} />
        {finalScoringTiles.map((tile, index) => {
          const slot = FINAL_SLOT_CORNERS[index];
          if (!slot) return null;
          const src = finalScoringTileImageSrc(tile.id);
          if (!src) return null;
          return (
            <div key={`final-${tile.id}`} className="scoring-board-tile scoring-board-tile--final">
              <WarpedTile
                sourceCorners={FINAL_TILE_CANVAS}
                targetCorners={slot}
                sourceWidth={FINAL_TILE_WIDTH}
                sourceHeight={FINAL_TILE_HEIGHT}
                src={src}
                alt={`게임 종료 점수 타일 ${index + 1}`}
              />
            </div>
          );
        })}
      </div>
    </section>
  );
}
