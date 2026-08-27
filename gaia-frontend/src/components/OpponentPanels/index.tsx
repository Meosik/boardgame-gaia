import { clsx } from 'clsx';
import { FactionBoard } from '../PlayerDashboard/FactionBoard';
import type { PlayerState } from '../../types/game';

interface Props {
  players: PlayerState[];
}

/** Compact status rows for the other players. Their faction boards stay one
 * click away instead of permanently consuming the narrow right column. */
export function OpponentPanels({ players }: Props) {
  if (players.length === 0) return null;

  return (
    <section className="opponent-panels" aria-label="상대 플레이어">
      {players.map((player) => (
        <details
          key={player.player_id}
          className={clsx('opponent-panel', player.passed && 'player-panel--passed')}
        >
          <summary>
            <span className="opponent-heading">
              <span className="player-name">{player.nickname}</span>
              <span className="player-vp">{player.vp} VP</span>
            </span>
            <span className="opponent-meta">
              {player.faction && (
                <span className={`faction-badge faction-${player.faction.toLowerCase()}`}>
                  {player.faction}
                </span>
              )}
              <span>O {player.resources.ore}</span>
              <span>C {player.resources.credits}</span>
              <span>K {player.resources.knowledge}</span>
              <span>QIC {player.resources.qic}</span>
              {player.passed && <span className="passed-badge">패스</span>}
            </span>
          </summary>
          {player.faction && (
            <div className="opponent-board-detail">
              <FactionBoard faction={player.faction} structures={player.structures} />
            </div>
          )}
        </details>
      ))}
    </section>
  );
}
