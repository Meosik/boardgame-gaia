import { spaceshipBoardImageSrc } from '../../assets/spaceshipBoardImages';
import { FACTION_VISUAL } from '../GameLobby/FactionBadge';
import { SatelliteToken } from '../PlayerDashboard/SatelliteToken';
import { artifactImageSrc } from '../../assets/artifactImages';
import { federationTokenImageSrc } from '../../assets/federationTokenImages';
import { standardTechTileImageSrc } from '../../assets/techTileImages';
import type { PlayerState, SpaceshipBoard, SpaceshipId } from '../../types/game';

interface Props {
  spaceshipBoards: SpaceshipBoard[];
  players: PlayerState[];
}

const SHIPS: { id: SpaceshipId; label: string }[] = [
  { id: 'Twilight', label: 'Twilight' },
  { id: 'Rebellion', label: 'Rebellion' },
  { id: 'TFMars', label: 'T F Mars' },
  { id: 'Eclipse', label: 'Eclipse' },
];

/**
 * 4 explorer-shuttle slot positions, measured directly off
 * `ship_faction_board_01.jpg` (3411x1050) — confirmed against
 * `MapEngine::initial_spaceship_boards`'s `explorers: vec![None; 4]` (every
 * ship has exactly 4 slots). All 4 ship scans share this template (same
 * numbered-slot column on the left), so one set of positions covers all of
 * them. The federation-token slot's position wasn't identifiable on this
 * scan (no distinct printed marker for it) — left unmarked rather than
 * guessed.
 */
const EXPLORER_SLOTS_PCT = [
  { x: 28.0, y: 20.0 },
  { x: 28.0, y: 42.4 },
  { x: 28.0, y: 60.0 },
  { x: 28.0, y: 77.6 },
];

const TWILIGHT_ARTIFACT_SLOTS = [
  { x: 72.2, y: 27.0 },
  { x: 90.5, y: 27.0 },
  { x: 72.2, y: 72.0 },
  { x: 90.5, y: 72.0 },
];

const FEDERATION_SLOTS: Record<SpaceshipId, { x: number; y: number }> = {
  Twilight: { x: 61.2, y: 80.0 },
  Rebellion: { x: 68.5, y: 72.5 },
  TFMars: { x: 69.2, y: 75.0 },
  Eclipse: { x: 68.8, y: 75.0 },
};

export function SpaceshipBoards({ spaceshipBoards, players }: Props) {
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
              {board.tech_tiles?.[0] !== undefined && standardTechTileImageSrc(board.tech_tiles[0]) && (
                <img
                  className="spaceship-board-tech-tile"
                  src={standardTechTileImageSrc(board.tech_tiles[0])}
                  alt={`${label} 표준 기술 타일 ${board.tech_tiles[0]}`}
                />
              )}
              {id === 'Twilight' && board.artifact_pool.map((artifactId, index) => {
                const slot = TWILIGHT_ARTIFACT_SLOTS[index];
                const src = artifactImageSrc(artifactId);
                if (!slot || !src) return null;
                return (
                  <img
                    key={`artifact-${artifactId}`}
                    className="spaceship-board-artifact"
                    style={{ left: `${slot.x}%`, top: `${slot.y}%` }}
                    src={src}
                    alt={`아티팩트 ${artifactId}`}
                  />
                );
              })}
              {board.federation_token !== null && federationTokenImageSrc(board.federation_token) && (
                <img
                  className="spaceship-board-federation"
                  style={{
                    left: `${FEDERATION_SLOTS[id].x}%`,
                    top: `${FEDERATION_SLOTS[id].y}%`,
                  }}
                  src={federationTokenImageSrc(board.federation_token)}
                  alt={`${label} 연방 토큰 ${board.federation_token}`}
                />
              )}
              {board.explorers.map((playerId, i) => {
                if (playerId === null) return null;
                const faction = factionByPlayer.get(playerId) ?? null;
                const { x, y } = EXPLORER_SLOTS_PCT[i];
                return (
                  <span
                    key={i}
                    className="spaceship-board-explorer"
                    style={{ left: `${x}%`, top: `${y}%` }}
                    aria-label={`탐사 셔틀 ${i + 1} 슬롯 탐사 완료`}
                  >
                    <SatelliteToken color={faction ? FACTION_VISUAL[faction].color : '#888'} faction={faction} size={18} />
                  </span>
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
