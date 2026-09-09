import { researchBoardImageSrc } from '../../assets/researchBoardImage';
import { FACTION_VISUAL } from '../GameLobby/FactionBadge';
import { SatelliteToken } from './SatelliteToken';
import { advancedTechTileImageSrc, standardTechTileImageSrc } from '../../assets/techTileImages';
import { economyResearchTileImageSrc } from '../../assets/economyResearchTileImages';
import { federationTokenImageSrc } from '../../assets/federationTokenImages';
import lostPlanetImageSrc from '../../assets/boards/normalized/lost_planet.webp';
import qicOverlayImageSrc from '../../assets/boards/normalized/lost_fleet_qic_board_overlay.webp';
import { POWER_ACTION_SPACES } from '../boardActionSpaces';
import { GamePieceIcon } from '../GamePieceIcon';
import type {
  PlayerState,
  ResearchBoard as ResearchBoardState,
  ResearchTrack,
  ResearchTracks,
} from '../../types/game';

interface Props {
  players: PlayerState[];
  board?: ResearchBoardState;
  usedPowerActions?: number[];
  isMyTurn?: boolean;
  selectedPowerActionId?: number | null;
  onPowerAction?: (id: number) => void;
  techSelectionMode?: 'tile' | 'track' | null;
  selectableStandardTiles?: number[];
  selectableAdvancedTracks?: ResearchTrack[];
  selectableResearchTracks?: ResearchTrack[];
  onStandardTechTile?: (tileId: number, slotIndex: number) => void;
  onAdvancedTechTile?: (tileId: number, track: ResearchTrack) => void;
  onResearchTrack?: (track: ResearchTrack) => void;
  /** Normal action-phase research: clicking a track pays four knowledge and advances it. */
  onPaidResearchTrack?: (track: ResearchTrack) => void;
}

/**
 * Column order left-to-right on the physical `research_board.jpg` scan,
 * confirmed against `ActionPanel`'s `TRACK_ORDER` (same rulebook sequence).
 * `xPct` is each column's chevron-track x-position (measured directly off
 * the 2441x2624 scan: chevron center ~x=97 within a ~406.8px-wide column,
 * i.e. `(colIndex * 406.8 + 97) / 2441`); `levelYPct` are the 6 level rows'
 * y-positions (measured the same way: level 5 chevron ~y=100 down to the
 * level-0 "start" icon ~y=1410, all six levels shared identically across
 * every column), as fractions of the scan's 2624px height.
 */
export const RESEARCH_TRACK_ORDER: ResearchTrack[] = [
  'Terraforming',
  'Navigation',
  'ArtificialIntelligence',
  'GaiaProject',
  'Economy',
  'Science',
];

const TRACKS: { key: keyof ResearchTracks; track: ResearchTrack; xPct: number }[] = [
  { key: 'terraforming', track: 'Terraforming', xPct: 3.97 },
  { key: 'navigation', track: 'Navigation', xPct: 20.64 },
  { key: 'ai', track: 'ArtificialIntelligence', xPct: 37.31 },
  { key: 'gaia', track: 'GaiaProject', xPct: 53.97 },
  { key: 'economy', track: 'Economy', xPct: 70.64 },
  { key: 'science', track: 'Science', xPct: 87.31 },
];

const TRACK_LABELS: Record<ResearchTrack, string> = {
  Terraforming: '테라포밍',
  Navigation: '항법',
  ArtificialIntelligence: '인공지능',
  GaiaProject: '가이아 프로젝트',
  Economy: '경제',
  Science: '과학',
};

const LEVEL_Y_PCT: Record<number, number> = {
  5: 3.81,
  4: 20.96,
  3: 28.20,
  2: 39.25,
  1: 46.11,
  0: 53.74,
};

/** Each of the 9 standard-tech sockets re-measured directly off the scan via the `?calibrate=1`
 * debug tool (socket's cut-corner pentagon: two true right-angle corners plus a point on its
 * uncut edge, same method as `ADVANCED_TECH_SLOTS`) — replaces the old shared-width six-then-three
 * row layout, which didn't account for each socket's own size varying slightly column to column.
 * `left`/`top` are the socket's center (the CSS class applies `translate(-50%, -50%)`). */
const STANDARD_TECH_SLOTS: { left: number; top: number; width: number; aspectRatio: string }[] = [
  { left: 9.29, top: 69.0, width: 15.84, aspectRatio: '191.5 / 142' },
  { left: 26.16, top: 69.08, width: 15.92, aspectRatio: '192.5 / 144' },
  { left: 42.74, top: 69.08, width: 15.43, aspectRatio: '186.5 / 142' },
  { left: 59.02, top: 69.0, width: 15.80, aspectRatio: '191 / 140' },
  { left: 75.17, top: 69.04, width: 15.51, aspectRatio: '187.5 / 145' },
  { left: 91.15, top: 69.12, width: 14.39, aspectRatio: '174 / 143' },
  { left: 15.72, top: 82.23, width: 15.88, aspectRatio: '192 / 132' },
  { left: 48.72, top: 82.33, width: 15.55, aspectRatio: '188 / 137.5' },
  { left: 79.92, top: 82.15, width: 14.35, aspectRatio: '173.5 / 138' },
];

/** Each of the 6 advanced-tech sockets re-measured directly off the scan via the `?calibrate=1`
 * debug tool (socket's cut-corner pentagon: two true right-angle corners plus a point on its
 * uncut edge, same method as the spaceship tech-tile sockets) — replaces the old shared-width/
 * per-column-offset approximation, which didn't account for each socket's own size varying
 * slightly column to column. `left`/`top` are the socket's center (the CSS class applies
 * `translate(-50%, -50%)`). */
const ADVANCED_TECH_SLOTS: { left: number; top: number; width: number; aspectRatio: string }[] = [
  { left: 10.53, top: 13.92, width: 12.20, aspectRatio: '147.5 / 134' },
  { left: 27.81, top: 13.92, width: 13.19, aspectRatio: '159.5 / 130' },
  { left: 44.50, top: 14.15, width: 11.91, aspectRatio: '144 / 132' },
  { left: 60.48, top: 13.96, width: 11.29, aspectRatio: '136.5 / 123' },
  { left: 76.72, top: 14.04, width: 12.49, aspectRatio: '151 / 127' },
  { left: 92.58, top: 14.0, width: 11.04, aspectRatio: '133.5 / 132' },
];

export function ResearchBoard({
  players,
  board,
  usedPowerActions = [],
  isMyTurn = false,
  selectedPowerActionId = null,
  onPowerAction,
  techSelectionMode = null,
  selectableStandardTiles,
  selectableAdvancedTracks,
  selectableResearchTracks,
  onStandardTechTile,
  onAdvancedTechTile,
  onResearchTrack,
  onPaidResearchTrack,
}: Props) {
  const active = players.filter((p) => p.faction);
  const lostPlanetAvailable = !active.some((player) => player.research_tracks.navigation >= 5);

  return (
    <section className="research-board" aria-label="연구판">
      <div className="research-board-image-wrap">
        <img className="research-board-image" src={researchBoardImageSrc()} alt="연구판" />
        <img
          className="research-board-economy-overlay"
          src={economyResearchTileImageSrc(board?.economy_research_tile_side ?? 'Power')}
          alt={`경제 연구 3·4레벨 대체 타일 — ${
            board?.economy_research_tile_side === 'VictoryPoints' ? '승점 면' : '파워 면'
          }`}
        />
        <img
          className="research-board-qic-overlay"
          src={qicOverlayImageSrc}
          alt="Lost Fleet 식민화 오버레이 — 기존 정보 큐브 액션 3개 폐쇄"
        />
        {board?.terraforming_level_5_token != null && federationTokenImageSrc(board.terraforming_level_5_token) && (
          <img
            className="research-board-terraforming-federation"
            src={federationTokenImageSrc(board.terraforming_level_5_token)}
            alt={`테라포밍 5레벨 연방 토큰 ${board.terraforming_level_5_token}`}
          />
        )}
        {lostPlanetAvailable && (
          <img
            className="research-board-lost-planet"
            src={lostPlanetImageSrc}
            alt="항법 5레벨 검은 행성 토큰"
          />
        )}
        {board?.tech_tile_slots?.map((tileId, index) => {
          const slot = STANDARD_TECH_SLOTS[index];
          if (!slot || tileId === null) return null;
          const src = standardTechTileImageSrc(tileId);
          const style = {
            left: `${slot.left}%`,
            top: `${slot.top}%`,
            width: `${slot.width}%`,
            aspectRatio: slot.aspectRatio,
          };
          const selectable = techSelectionMode === 'tile'
            && onStandardTechTile !== undefined
            && (selectableStandardTiles === undefined || selectableStandardTiles.includes(tileId));
          return (
            <span key={`standard-tech-${index}-${tileId}`}>
              <img
                className="research-board-standard-tech"
                style={style}
                src={src}
                alt={`표준 기술 타일 ${tileId}`}
              />
              {techSelectionMode === 'tile' && (
                <button
                  type="button"
                  className="research-board-tech-hotspot research-board-tech-hotspot--standard"
                  style={style}
                  disabled={!selectable}
                  onClick={() => onStandardTechTile?.(tileId, index)}
                  aria-label={`표준 기술 타일 ${tileId} 선택`}
                  title={selectable ? `표준 기술 타일 ${tileId} 선택` : '선택할 수 없는 기술 타일'}
                />
              )}
            </span>
          );
        })}
        {board?.advanced_tech_tiles.map((tileId, index) => {
          const slot = ADVANCED_TECH_SLOTS[index];
          if (!slot || tileId === null) return null;
          const src = advancedTechTileImageSrc(tileId);
          const track = RESEARCH_TRACK_ORDER[index];
          const style = {
            left: `${slot.left}%`,
            top: `${slot.top}%`,
            width: `${slot.width}%`,
            aspectRatio: slot.aspectRatio,
          };
          const selectable = techSelectionMode === 'tile'
            && onAdvancedTechTile !== undefined
            && selectableAdvancedTracks?.includes(track) === true;
          return (
            <span key={`advanced-tech-${index}-${tileId}`}>
              <img
                className="research-board-advanced-tech"
                style={style}
                src={src}
                alt={`고급 기술 타일 ${tileId}`}
              />
              {techSelectionMode === 'tile' && (
                <button
                  type="button"
                  className="research-board-tech-hotspot research-board-tech-hotspot--advanced"
                  style={style}
                  disabled={!selectable}
                  onClick={() => onAdvancedTechTile?.(tileId, track)}
                  aria-label={`고급 기술 타일 ${tileId} 선택`}
                  title={selectable ? `고급 기술 타일 ${tileId} 선택` : '연구 4레벨과 사용 가능한 연방 토큰이 필요합니다'}
                />
              )}
            </span>
          );
        })}
        {TRACKS.map(({ key, track, xPct }) =>
          active.map((player) => {
            const level = Math.max(0, Math.min(5, player.research_tracks[key]));
            const yPct = LEVEL_Y_PCT[level];
            // Players sharing a level on the same track fan out slightly so
            // their tokens don't fully overlap.
            const sameLevelPlayers = active.filter(
              (p) => Math.max(0, Math.min(5, p.research_tracks[key])) === level,
            );
            const slot = sameLevelPlayers.indexOf(player);
            const fanOffset = (slot - (sameLevelPlayers.length - 1) / 2) * 2.2;
            const tooltip = `${player.nickname} · ${player.faction} · ${TRACK_LABELS[track]} ${level}레벨`;
            const researchTrackSelectable = selectableResearchTracks === undefined
              || selectableResearchTracks.includes(track);
            const chooseTrack = techSelectionMode === 'track'
              ? researchTrackSelectable ? onResearchTrack : undefined
              : techSelectionMode === null
                ? onPaidResearchTrack
                : undefined;
            return (
              <span
                key={`${key}-${player.player_id}`}
                className={`research-board-token${chooseTrack ? ' research-board-token--clickable' : ''}`}
                style={{ top: `${yPct}%`, left: `${xPct + fanOffset}%` }}
                aria-label={tooltip}
                title={tooltip}
                onClick={chooseTrack ? () => chooseTrack(track) : undefined}
              >
                <SatelliteToken color={FACTION_VISUAL[player.faction!].color} faction={player.faction} size={16} />
              </span>
            );
          }),
        )}
        {((techSelectionMode === 'track' && onResearchTrack) ||
          (techSelectionMode === null && onPaidResearchTrack)) && TRACKS.map(({ track }, index) => {
          const selectable = techSelectionMode !== 'track'
            || selectableResearchTracks === undefined
            || selectableResearchTracks.includes(track);
          return (
            <button
              key={`research-track-choice-${track}`}
              type="button"
              className={`research-board-track-hotspot${
                techSelectionMode === null ? ' research-board-track-hotspot--paid' : ''
              }`}
              style={{ left: `${index * (100 / 6)}%`, width: `${100 / 6}%` }}
              disabled={!selectable}
              onClick={() => {
                if (!selectable) return;
                if (techSelectionMode === 'track') onResearchTrack?.(track);
                else onPaidResearchTrack?.(track);
              }}
              aria-label={`${TRACK_LABELS[track]} 트랙 ${
                techSelectionMode === 'track' ? '선택' : '연구 (지식 4)'
              }`}
              title={`${TRACK_LABELS[track]} 트랙 ${
                techSelectionMode === 'track'
                  ? selectable ? '선택' : '더 이상 상승할 수 없음'
                  : '연구 — 지식 4'
              }`}
            />
          );
        })}
        {onPowerAction && POWER_ACTION_SPACES.map(({ id, label, x, y }) => {
          const used = usedPowerActions.includes(id);
          const available = isMyTurn && !used;
          const reason = used
            ? '이번 라운드에 다른 플레이어가 사용함'
            : isMyTurn
              ? '사용 가능'
              : '내 행동 턴이 아님';
          return (
            <button
              key={`power-action-space-${id}`}
              type="button"
              className={`board-action-hotspot research-board-action-space board-action-hotspot--${
                used ? 'used' : available ? 'available' : 'locked'
              }${selectedPowerActionId === id ? ' board-action-hotspot--selected' : ''}`}
              style={{ left: `${x}%`, top: `${y}%` }}
              disabled={!available}
              onClick={() => onPowerAction(id)}
              aria-label={`${label}: ${reason}`}
              title={`${label} — ${reason}`}
            >
              {used && <GamePieceIcon kind="action-used" />}
            </button>
          );
        })}
      </div>
    </section>
  );
}
