import { roundBoosterImageSrc } from '../../assets/roundBoosterImages';
import { FACTION_VISUAL } from '../GameLobby/FactionBadge';
import { SatelliteToken } from '../PlayerDashboard/SatelliteToken';
import type { PlayerState } from '../../types/game';

interface Props {
  /** The currently *available* (untaken) booster pool — `gameState.boosters`. */
  availableBoosters: number[];
  players: PlayerState[];
}

/**
 * The real round-booster tiles instead of bare "#id" text — every booster dealt into this game
 * (the available pool plus whichever one each player currently holds; a player's old booster
 * always returns to `availableBoosters` the moment they take a new one at Pass, so the union of
 * these two is exactly the full in-play set) rendered as its actual tile image, with a
 * faction-colored marker on whichever tile a player currently holds.
 */
export function RoundBoosters({ availableBoosters, players }: Props) {
  const ownerByBooster = new Map<number, PlayerState>();
  for (const player of players) {
    if (player.booster != null) ownerByBooster.set(player.booster, player);
  }
  const allIds = [...new Set([...availableBoosters, ...ownerByBooster.keys()])].sort((a, b) => a - b);

  if (allIds.length === 0) return null;

  return (
    <section className="round-boosters" aria-label="라운드 부스터">
      {allIds.map((id) => {
        const src = roundBoosterImageSrc(id);
        if (!src) return null;
        const owner = ownerByBooster.get(id);
        return (
          <figure
            key={id}
            className={`round-booster-tile ${[5, 14].includes(id) ? 'round-booster-tile--wide' : ''}`}
          >
            <img src={src} alt={`라운드 부스터 ${id}`} />
            {owner?.faction && (
              <span
                className="round-booster-owner"
                aria-label={`${owner.nickname} 보유 중`}
              >
                <SatelliteToken color={FACTION_VISUAL[owner.faction].color} faction={owner.faction} size={16} />
              </span>
            )}
          </figure>
        );
      })}
    </section>
  );
}
