import { clsx } from 'clsx';
import { ExplorationBoard } from './ExplorationBoard';
import { FactionBoard } from './FactionBoard';
import { PowerCycle } from './PowerCycle';
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
        <div className="player-dashboard-content">
          {player.faction && (
            <div className="player-body-top">
              <FactionBoard
                faction={player.faction}
                structures={player.structures}
                resources={player.resources}
                power={player.resources.power}
                gaiaformersAvailable={Math.max(
                  0,
                  player.gaiaformers_total
                    - player.gaiaformers_deployed
                    - player.resources.spent_gaia_formers
                    - (player.gaiaformers_in_gaia_area ?? 0),
                )}
                techTiles={player.tech_tiles}
                advancedTechTiles={player.advanced_tech_tiles}
                coveredTechTiles={player.covered_tech_tiles}
                federationTokens={player.federation_tokens}
                grayFederationTokens={player.gray_federation_tokens}
                booster={player.booster}
                expensiveTerraformingPlanetTypes={player.expensive_terraforming_planet_types}
                selectedTinkeringTile={player.tinkeroids_selected_tile}
              />
              <ExplorationBoard
                faction={player.faction}
                shuttlesAvailable={player.exploration_shuttles_available}
              />
            </div>
          )}
          <aside className="player-personal-summary" aria-label="내 자원과 획득 타일">
            <div className="player-resource-summary">
              <PowerCycle power={player.resources.power} faction={player.faction ?? undefined} />
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
