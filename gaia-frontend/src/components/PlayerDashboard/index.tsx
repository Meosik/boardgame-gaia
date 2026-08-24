import { clsx } from 'clsx';
import { ResourcePanel } from './ResourcePanel';
import { PowerCycle } from './PowerCycle';
import { ResearchTrack } from './ResearchTrack';
import { useGameStore } from '../../store/gameStore';
import type { PlayerState } from '../../types/game';

interface Props {
  players: PlayerState[];
}

export function PlayerDashboard({ players }: Props) {
  const myPlayerId = useGameStore((s) => s.myPlayerId);

  return (
    <div className="player-dashboard">
      {players.map((player) => (
        <PlayerPanel
          key={player.player_id}
          player={player}
          isMe={player.player_id === myPlayerId}
        />
      ))}
    </div>
  );
}

interface PanelProps {
  player: PlayerState;
  isMe: boolean;
}

function PlayerPanel({ player, isMe }: PanelProps) {
  return (
    <div className={clsx('player-panel', isMe && 'player-panel--me', player.passed && 'player-panel--passed')}>
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
      <div className="player-body">
        <ResourcePanel resources={player.resources} />
        <PowerCycle power={player.resources.power} />
        <ResearchTrack tracks={player.research_tracks} />
      </div>
    </div>
  );
}
