import { clsx } from 'clsx';
import { ExplorationBoard } from './ExplorationBoard';
import { FactionBoard } from './FactionBoard';
import { PowerCycle } from './PowerCycle';
import { ResourcePanel } from './ResourcePanel';
import type { PlayerState } from '../../types/game';

interface Props {
  player: PlayerState;
}

/** The controlled player's own panel — large, prominent, board-first. The
 * other 3 players get the compact `OpponentPanels` list instead. */
export function PlayerDashboard({ player }: Props) {
  return (
    <div className="player-dashboard">
      <div className={clsx('player-panel', 'player-panel--me', player.passed && 'player-panel--passed')}>
        <div className="player-header">
          <span className="player-name">{player.nickname}</span>
          {player.faction && (
            <span className={`faction-badge faction-${player.faction.toLowerCase()}`}>
              {player.faction}
            </span>
          )}
          <span className="player-vp">{player.vp} VP</span>
          {player.passed && <span className="passed-badge">패스</span>}
        </div>
        <div className="player-dashboard-content">
          {player.faction && (
            <div className="player-body-top">
              <FactionBoard faction={player.faction} structures={player.structures} />
              <ExplorationBoard
                faction={player.faction}
                shuttlesAvailable={player.exploration_shuttles_available}
              />
            </div>
          )}
          <aside className="player-personal-summary" aria-label="내 자원과 획득 타일">
            <div className="player-resource-summary">
              <ResourcePanel resources={player.resources} />
              <PowerCycle power={player.resources.power} faction={player.faction ?? undefined} />
            </div>
            <PersonalHoldings
              label="기술"
              values={[
                ...(player.tech_tiles ?? []).map((id) => `T${id}`),
                ...(player.advanced_tech_tiles ?? []).map((id) => `A${id}`),
              ]}
            />
            <PersonalHoldings
              label="연방"
              values={player.federation_tokens.map((id) => `F${id}`)}
            />
          </aside>
        </div>
      </div>
    </div>
  );
}

function PersonalHoldings({ label, values }: { label: string; values: string[] }) {
  return (
    <section className="personal-holdings">
      <strong>{label}</strong>
      <div className="personal-holdings-list">
        {values.length > 0 ? (
          values.map((value) => <span key={value}>{value}</span>)
        ) : (
          <small>없음</small>
        )}
      </div>
    </section>
  );
}
