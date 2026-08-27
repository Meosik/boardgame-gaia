import { researchBoardImageSrc } from '../../assets/researchBoardImage';
import { FACTION_VISUAL } from '../GameLobby/FactionBadge';
import { SatelliteToken } from './SatelliteToken';
import type { PlayerState, ResearchTracks } from '../../types/game';

interface Props {
  players: PlayerState[];
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
const TRACKS: { key: keyof ResearchTracks; xPct: number }[] = [
  { key: 'terraforming', xPct: 3.97 },
  { key: 'navigation', xPct: 20.64 },
  { key: 'ai', xPct: 37.31 },
  { key: 'gaia', xPct: 53.97 },
  { key: 'economy', xPct: 70.64 },
  { key: 'science', xPct: 87.31 },
];

const LEVEL_Y_PCT: Record<number, number> = {
  5: 3.81,
  4: 20.96,
  3: 28.20,
  2: 39.25,
  1: 46.11,
  0: 53.74,
};

export function ResearchBoard({ players }: Props) {
  const active = players.filter((p) => p.faction);

  return (
    <section className="research-board" aria-label="연구판">
      <div className="research-board-image-wrap">
        <img className="research-board-image" src={researchBoardImageSrc()} alt="연구판" />
        {TRACKS.map(({ key, xPct }) =>
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
            return (
              <span
                key={`${key}-${player.player_id}`}
                className="research-board-token"
                style={{ top: `${yPct}%`, left: `${xPct + fanOffset}%` }}
                aria-label={`${player.nickname} ${key} 레벨 ${level}`}
              >
                <SatelliteToken color={FACTION_VISUAL[player.faction!].color} faction={player.faction} size={16} />
              </span>
            );
          }),
        )}
      </div>
    </section>
  );
}
