import { FACTION_STRUCTURE_COLOR, structureImageSrc } from '../../assets/structureImages';
import { factionDisplayName } from '../../displayNames';
import { FINAL_SCORING_LABELS, finalScoringMetric, type FinalScoringState } from '../../finalScoring';
import type { FinalScoringTile } from '../../types/game';

// Centers of the existing printed columns on the 1254px board, not a new track.
const COLUMNS = [245, 299, 343, 387, 431, 475, 519, 563, 607, 651, 695];
const ROWS = [701, 920];
const MARKER_SIZE = 32;

interface Props {
  state: FinalScoringState;
  tiles: FinalScoringTile[];
}

export function FinalGoalMarkers({ state, tiles }: Props) {
  return (
    <svg className="scoring-board-goal-markers" viewBox="0 0 1254 1254" aria-label="게임 종료 목표 달성량">
      {tiles.slice(0, 2).map((tile, goal) => {
        const markers = state.players.filter(p => p.faction !== null).map(player => {
          const value = finalScoringMetric(state, player.player_id, tile.condition);
          return { player, value, column: Math.min(10, value) };
        }).sort((a, b) => a.player.player_id - b.player.player_id);
        return markers.map(({ player, value, column }) => {
          const peers = markers.filter(m => m.column === column);
          const position = peers.findIndex(m => m.player.player_id === player.player_id);
          const y = ROWS[goal] + (position - (peers.length - 1) / 2) * (MARKER_SIZE + 4);
          const label = `목표 ${goal + 1} · ${FINAL_SCORING_LABELS[tile.condition]} · ${player.nickname} (${factionDisplayName(player.faction!)}) ${value}`;
          return (
            <g key={`${goal}-${player.player_id}`} role="img" aria-label={label}
              data-goal-index={goal} data-player={player.player_id} data-value={value} data-column={column}
              transform={`translate(${COLUMNS[column]} ${y})`}>
              <title>{label}</title>
              <image href={structureImageSrc(FACTION_STRUCTURE_COLOR[player.faction!], 'marker')}
                x={-MARKER_SIZE / 2} y={-MARKER_SIZE / 2} width={MARKER_SIZE} height={MARKER_SIZE}
                className="scoring-board-goal-marker" />
              {value > 10 && <text className="scoring-board-goal-overflow" textAnchor="middle" dominantBaseline="central">{value}</text>}
            </g>
          );
        });
      })}
    </svg>
  );
}
