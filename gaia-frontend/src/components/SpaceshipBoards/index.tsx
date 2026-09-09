import { spaceshipBoardImageSrc } from '../../assets/spaceshipBoardImages';
import { explorationShuttleImageSrc } from '../../assets/explorationShuttleImages';
import { artifactImageSrc } from '../../assets/artifactImages';
import { federationTokenImageSrc } from '../../assets/federationTokenImages';
import { standardTechTileImageSrc } from '../../assets/techTileImages';
import { SPACESHIP_ACTION_SPACES } from '../boardActionSpaces';
import { GamePieceIcon } from '../GamePieceIcon';
import type { GameAction, PlayerId, PlayerState, SpaceshipBoard, SpaceshipId } from '../../types/game';

interface Props {
  spaceshipBoards: SpaceshipBoard[];
  players: Pick<PlayerState, 'player_id' | 'faction'>[];
  myPlayerId?: PlayerId;
  isMyTurn?: boolean;
  usedActionIds?: number[];
  selectedAction?: GameAction['type'] | null;
  onActionSelect?: (actionType: GameAction['type']) => void;
}

const SHIPS: { id: SpaceshipId; label: string }[] = [
  { id: 'Twilight', label: 'Twilight' },
  { id: 'Rebellion', label: 'Rebellion' },
  { id: 'TFMars', label: 'T F Mars' },
  { id: 'Eclipse', label: 'Eclipse' },
];

// Twilight keeps its fourth shuttle fixed and adds about 5 source pixels to
// every adjacent gap upward from that anchor.
const TWILIGHT_EXPLORER_SLOTS_PCT = [
  { x: 22.75, y: 25.35 },
  { x: 22.75, y: 42.13 },
  { x: 22.75, y: 59.11 },
  { x: 22.75, y: 76.49 },
];

// Rebellion uses the slightly wider 2135x736 scan. Move its shuttle column
// 75 source pixels left and add roughly 14 source pixels between each socket.
// The full group is then shifted 10 source pixels upward.
const REBELLION_EXPLORER_SLOTS_PCT = [
  { x: 22.75 - 75 * 100 / 2135, y: 25.95 - 15 * 100 / 736 },
  { x: 22.75 - 75 * 100 / 2135, y: 43.25 - 10 * 100 / 736 },
  { x: 22.75 - 75 * 100 / 2135, y: 60.75 - 10 * 100 / 736 },
  { x: 22.75 - 75 * 100 / 2135, y: 78.65 - 10 * 100 / 736 },
];

// T F Mars spreads adjacent sockets by roughly 14 source pixels and shifts
// the column 25 source pixels left. Blue moves 10px down, red/yellow move
// 5px down, and the white shuttle moves 5px up from the prior placement.
const TF_MARS_EXPLORER_SLOTS_PCT = [
  { x: 22.75 - 25 * 100 / 2172, y: 23.14 + 10 * 100 / 724 },
  { x: 22.75 - 25 * 100 / 2172, y: 40.47 + 5 * 100 / 724 },
  { x: 22.75 - 25 * 100 / 2172, y: 58.01 + 5 * 100 / 724 },
  { x: 22.75 - 25 * 100 / 2172, y: 75.94 - 5 * 100 / 724 },
];

// Eclipse shifts the full shuttle column 80 source pixels right. Its second
// shuttle anchors the column after reducing each adjacent gap by 7px from the
// previous 28px expansion; the complete group also remains 10px upward.
const ECLIPSE_EXPLORER_SLOTS_PCT = [
  { x: 22.75 + 83 * 100 / 2172, y: 22.586 - 10 * 100 / 724 },
  { x: 22.75 + 80 * 100 / 2172, y: 40.879 },
  { x: 22.75 + 80 * 100 / 2172, y: 59.392 - 5 * 100 / 724 },
  { x: 22.75 + 80 * 100 / 2172, y: 78.285 - 5 * 100 / 724 },
];

// Re-measured against the current `boards/normalized/spaceship_twilight.webp` scan (2172x724) —
// the previous values were measured off an older 3411x1050 source scan with a
// different crop/aspect ratio, so they no longer lined up with
// this image's actual oval sockets once the art was swapped.
const TWILIGHT_ARTIFACT_SLOTS = [
  { x: 75.3, y: 27.0, yOffsetPx: 1 },
  { x: 92.0, y: 28.0, yOffsetPx: 2 },
  { x: 75.3, y: 67.5, yOffsetPx: 0 },
  { x: 92.0, y: 68.0, yOffsetPx: 0 },
];
const TWILIGHT_BOARD_HEIGHT_PX = 724;

// Artifact 08 was exported with substantially more transparent padding than
// the other redraws. The common 3:2 display box normalizes canvas ratios; this
// scale only compensates for that file's internal padding.
const ARTIFACT_VISUAL_SCALE: Partial<Record<number, number>> = {
  8: 1.45,
};

// Each ship's federation-token badge position AND size, re-measured directly off its own scan via
// the `?calibrate=1` debug tool (badge's hexagon bounding box) — no longer relying on
// `.spaceship-board-federation`'s shared 7.7% width, which assumed every scan was both the same
// 2172x724 size (false for Rebellion's 2135x736 scan) and the same badge size relative to that
// scan (false in general — the earlier eyeballed positions were off by several points in every
// direction once actually checked against the art, not just Rebellion's resolution mismatch).
// `width` stays optional so a ship can still fall back to the shared CSS value if unmeasured.
const FEDERATION_SLOTS: Record<SpaceshipId, { left: string; top: string; width?: string }> = {
  Twilight: { left: '61.53%', top: '77.07%', width: '8.15%' },
  Rebellion: { left: '68.15%', top: '63.18%', width: '8.71%' },
  TFMars: { left: '69.34%', top: '71.13%', width: '7.46%' },
  Eclipse: { left: '69.52%', top: '72.44%', width: '7.09%' },
};

/**
 * Each board prints one large cockpit-screen panel with a cut bottom-left corner — the tech tile
 * sits somewhere on that whole screen, not in a tile-shaped cutout — so `width`/`aspectRatio`
 * describe that screen panel's own bounding box (measured directly off each scan via the
 * `?calibrate=1` debug tool: click the panel's two true right-angle corners — top-right and
 * bottom-right — plus a point on its uncut left edge), not the printed tile card's generic
 * 178x134 physical ratio. `left`/`top` are the panel's center — `.spaceship-board-tech-tile`
 * applies `translate(-50%, -50%)` — expressed relative to that scan's own pixel size.
 */
const TECH_TILE_SLOT: Partial<
  Record<SpaceshipId, { left: string; top: string; width: string; aspectRatio: string }>
> = {
  Eclipse: { left: '79.67%', top: '37.29%', width: '16.53%', aspectRatio: '359 / 300' },
  TFMars: { left: '81.86%', top: '46.62%', width: '16.55%', aspectRatio: '359.5 / 285' },
  Rebellion: { left: '82.29%', top: '48.51%', width: '17.03%', aspectRatio: '363.5 / 316' },
};

export function SpaceshipBoards({
  spaceshipBoards,
  players,
  myPlayerId,
  isMyTurn = false,
  usedActionIds = [],
  selectedAction = null,
  onActionSelect,
}: Props) {
  const factionByPlayer = new Map(players.map((p) => [p.player_id, p.faction]));

  return (
    <section className="spaceship-boards" aria-label="Lost Fleet 함선">
      {SHIPS.map(({ id, label }) => {
        const board = spaceshipBoards.find((b) => b.id === id);
        const imageSrc = spaceshipBoardImageSrc(id);
        if (!board || !imageSrc) return null;

        return (
          <figure key={id} className="spaceship-board" aria-label={`${label} 함선 보드`}>
            <div className="spaceship-board-image-wrap">
              <img className="spaceship-board-image" src={imageSrc} alt={`${label} 함선 보드`} />
              {board.tech_tiles?.[0] !== undefined && (() => {
                const tileId = board.tech_tiles[0];
                const renderedSrc = standardTechTileImageSrc(tileId);
                const slot = TECH_TILE_SLOT[id];
                if (!renderedSrc || !slot) return null;
                return (
                  <span
                    className="spaceship-board-tech-tile"
                    style={slot}
                  >
                    <img
                      className="spaceship-board-tech-source"
                      src={renderedSrc}
                      alt={`${label} 표준 기술 타일 ${tileId}`}
                    />
                  </span>
                );
              })()}
              {id === 'Twilight' && board.artifact_pool.map((artifactId, index) => {
                const slot = TWILIGHT_ARTIFACT_SLOTS[index];
                const src = artifactImageSrc(artifactId);
                if (!slot || !src) return null;
                return (
                  <img
                    key={`artifact-${artifactId}`}
                    className="spaceship-board-artifact spaceship-board-artifact--transparent-redraw"
                    style={{
                      left: `${slot.x}%`,
                      top: `${slot.y + slot.yOffsetPx * 100 / TWILIGHT_BOARD_HEIGHT_PX}%`,
                      transform: `translate(-50%, -50%) scale(${ARTIFACT_VISUAL_SCALE[artifactId] ?? 1})`,
                    }}
                    src={src}
                    alt={`아티팩트 ${artifactId}`}
                  />
                );
              })}
              {board.federation_token !== null && (() => {
                const renderedSrc = federationTokenImageSrc(board.federation_token);
                if (!renderedSrc) return null;
                return (
                  <span
                    className="spaceship-board-federation"
                    style={{
                      left: FEDERATION_SLOTS[id].left,
                      top: FEDERATION_SLOTS[id].top,
                      ...(FEDERATION_SLOTS[id].width ? { width: FEDERATION_SLOTS[id].width } : null),
                    }}
                  >
                    <img
                      className="spaceship-board-federation-source"
                      src={renderedSrc}
                      alt={`${label} 연방 토큰 ${board.federation_token}`}
                    />
                  </span>
                );
              })()}
              {board.explorers.map((playerId, i) => {
                if (playerId === null) return null;
                const faction = factionByPlayer.get(playerId) ?? null;
                const explorerSlots = id === 'Twilight'
                  ? TWILIGHT_EXPLORER_SLOTS_PCT
                  : id === 'Rebellion'
                    ? REBELLION_EXPLORER_SLOTS_PCT
                    : id === 'TFMars'
                      ? TF_MARS_EXPLORER_SLOTS_PCT
                      : ECLIPSE_EXPLORER_SLOTS_PCT;
                const { x, y } = explorerSlots[i];
                return (
                  <span
                    key={i}
                    className="spaceship-board-explorer"
                    style={{ left: `${x}%`, top: `${y}%` }}
                    aria-label={`탐사 셔틀 ${i + 1} 슬롯 탐사 완료`}
                  >
                    <img
                      className="spaceship-board-explorer-image"
                      src={explorationShuttleImageSrc(faction)}
                      alt=""
                      aria-hidden
                    />
                  </span>
                );
              })}
              {onActionSelect && myPlayerId !== undefined && SPACESHIP_ACTION_SPACES[id].map((space) => {
                const entered = board.explorers.includes(myPlayerId);
                const used = usedActionIds.includes(space.id);
                const available = isMyTurn && entered && !used;
                const selected = selectedAction !== null && space.actionTypes.includes(selectedAction);
                const reason = used
                  ? '이번 라운드에 다른 플레이어가 사용함'
                  : !entered
                    ? '이 함선에 탐사 셔틀을 배치해야 함'
                    : isMyTurn
                      ? '사용 가능'
                      : '내 행동 턴이 아님';
                return (
                  <button
                    key={`${id}-action-space-${space.id}`}
                    type="button"
                    className={`board-action-hotspot spaceship-board-action-space board-action-hotspot--${
                      used ? 'used' : available ? 'available' : 'locked'
                    }${selected ? ' board-action-hotspot--selected' : ''}`}
                    style={{ left: `${space.x}%`, top: `${space.y}%` }}
                    disabled={!available}
                    onClick={() => onActionSelect(space.primaryActionType)}
                    aria-label={`${label} — ${space.label}: ${reason}`}
                    title={`${space.label} — ${reason}`}
                  >
                    {used && <GamePieceIcon kind="action-used" />}
                  </button>
                );
              })}
            </div>
            <figcaption>{label}</figcaption>
          </figure>
        );
      })}
    </section>
  );
}
