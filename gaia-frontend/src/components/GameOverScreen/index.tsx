import { FACTION_VISUAL } from '../GameLobby/FactionBadge';
import type { FinalResult } from '../../store/gameStore';
import type { PlayerState } from '../../types/game';

interface Props {
  result: FinalResult;
  players: PlayerState[];
  myPlayerId: number;
  onReturnToLobby: () => void;
}

export function GameOverScreen({ result, players, myPlayerId, onReturnToLobby }: Props) {
  const playerById = new Map(players.map((p) => [p.player_id, p]));
  const ranked = [...result.finalScores].sort((a, b) => b[1] - a[1]);

  return (
    <div className="app app--game-over">
      <div className="game-over-card">
        <span className="game-over-eyebrow">GAME OVER</span>
        <h1 className="game-over-title">게임 종료</h1>
        <ol className="game-over-standings">
          {ranked.map(([playerId, vp], index) => {
            const player = playerById.get(playerId);
            const vis = player?.faction ? FACTION_VISUAL[player.faction] : null;
            const isWinner = playerId === result.winner;
            const isMe = playerId === myPlayerId;
            return (
              <li
                key={playerId}
                className={`game-over-row${isWinner ? ' game-over-row--winner' : ''}${isMe ? ' game-over-row--me' : ''}`}
              >
                <span className="game-over-rank">{index + 1}</span>
                <span
                  className="game-over-swatch"
                  style={{ background: vis?.color ?? 'var(--color-border)' }}
                  aria-hidden
                >
                  {vis?.initials ?? '?'}
                </span>
                <span className="game-over-name">
                  {player?.nickname ?? `Player ${playerId}`}
                  {isWinner && <span className="game-over-crown" aria-label="승자">👑</span>}
                </span>
                <span className="game-over-vp">{vp} VP</span>
              </li>
            );
          })}
        </ol>
        <button type="button" className="btn btn-primary game-over-return-btn" onClick={onReturnToLobby}>
          로비로 돌아가기
        </button>
      </div>
    </div>
  );
}
