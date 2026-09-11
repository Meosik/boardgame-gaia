import {
  federationTokenBackImageSrc,
  federationTokenImageSrc,
} from '../../assets/federationTokenImages';
import { FACTION_VISUAL } from '../GameLobby/FactionBadge';
import { SatelliteToken } from '../PlayerDashboard/SatelliteToken';
import type {
  FederationTokenChoice,
  PlayerState,
  SpaceshipId,
} from '../../types/game';

interface Props {
  /** The remaining base-game supply — `gameState.research_board.federation_tokens` (18 tokens
   * shuffled across 6 reward kinds at setup; repeated ids are separate physical tokens of the
   * same kind, shown here as one stack with a count). */
  availableTokens: number[];
  players: PlayerState[];
  selectionMode?: boolean;
  selectedToken?: FederationTokenChoice | null;
  spaceshipTokens?: { ship: SpaceshipId; kind: number }[];
  onSelectToken?: (token: FederationTokenChoice) => void;
  showHoldings?: boolean;
}

/**
 * Base-game federation tokens rendered as their actual tile images instead of bare "F#" text:
 * the shared supply grouped into per-kind stacks, plus every player's claimed tokens (green =
 * still spendable, gray = the actual flipped face used for an Advanced Tech tile or level-5 research). Mirrors
 * `RoundBoosters`' real-tile treatment for the same "no UI, just an id" gap.
 */
export function FederationTokens({
  availableTokens,
  players,
  selectionMode = false,
  selectedToken = null,
  spaceshipTokens = [],
  onSelectToken,
  showHoldings = true,
}: Props) {
  const supplyCounts = new Map<number, number>();
  for (const id of availableTokens) {
    if (id === 7) continue;
    supplyCounts.set(id, (supplyCounts.get(id) ?? 0) + 1);
  }
  const supplyKinds = [...supplyCounts.keys()].sort((a, b) => a - b);

  const holders = players.filter((player) =>
    [...player.federation_tokens, ...(player.gray_federation_tokens ?? [])].some(
      (id) => federationTokenImageSrc(id) !== undefined,
    ),
  );

  if (supplyKinds.length === 0 && holders.length === 0 && spaceshipTokens.length === 0) return null;

  return (
    <section
      className={`federation-tokens${selectionMode ? ' federation-tokens--selecting' : ''}`}
      aria-label="연방 토큰"
    >
      <div className="federation-tokens-supply" aria-label="남은 연방 토큰 보급">
        {supplyKinds.map((id) => {
          const src = federationTokenImageSrc(id);
          if (!src) return null;
          const count = supplyCounts.get(id) ?? 0;
          return (
            <figure
              key={`supply-${id}`}
              className={`federation-token-tile${
                selectedToken?.source === 'Supply' && selectedToken.kind === id
                  ? ' federation-token-tile--selected'
                  : ''
              }`}
              aria-label={`연방 토큰 ${id} 보급 ${count}개`}
            >
              {selectionMode && onSelectToken ? (
                <button
                  type="button"
                  className="federation-token-select-button"
                  aria-label={`연방 토큰 ${id} 선택`}
                  aria-pressed={selectedToken?.source === 'Supply' && selectedToken.kind === id}
                  onClick={() => onSelectToken({ source: 'Supply', kind: id })}
                >
                  <img src={src} alt={`연방 토큰 ${id}`} />
                </button>
              ) : (
                <img src={src} alt={`연방 토큰 ${id}`} />
              )}
              <span className="federation-token-count">×{count}</span>
            </figure>
          );
        })}
      </div>
      {selectionMode && spaceshipTokens.length > 0 && onSelectToken && (
        <aside className="federation-expansion-tab" aria-label="획득 가능한 확장 연방 토큰">
          <span className="federation-expansion-tab-label">확장 연방</span>
          <div className="federation-expansion-token-list">
            {spaceshipTokens.map(({ ship, kind }) => {
              const src = federationTokenImageSrc(kind);
              if (!src) return null;
              const selected = selectedToken?.source === 'Spaceship' && selectedToken.ship === ship;
              return (
                <button
                  key={ship}
                  type="button"
                  className={`federation-expansion-token${selected ? ' is-selected' : ''}`}
                  aria-label={`${ship} 확장 연방 토큰 ${kind} 선택`}
                  aria-pressed={selected}
                  onClick={() => onSelectToken({ source: 'Spaceship', ship })}
                >
                  <img src={src} alt={`확장 연방 토큰 ${kind}`} />
                  <span>{ship}</span>
                </button>
              );
            })}
          </div>
        </aside>
      )}
      {showHoldings && holders.length > 0 && (
        <div className="federation-tokens-holdings" aria-label="플레이어별 보유 연방 토큰">
          {holders.map((player) => (
            <div key={player.player_id} className="federation-token-holder">
              <span className="federation-token-holder-name">
                {player.faction && (
                  <SatelliteToken color={FACTION_VISUAL[player.faction].color} faction={player.faction} size={14} />
                )}
                {player.nickname}
              </span>
              <div className="federation-token-holder-tiles">
                {player.federation_tokens.map((id, index) => {
                  const src = federationTokenImageSrc(id);
                  if (!src) return null;
                  return (
                    <img
                      key={`green-${player.player_id}-${index}`}
                      className="federation-token-mini"
                      src={src}
                      alt={`${player.nickname} 보유 연방 토큰 ${id}`}
                    />
                  );
                })}
                {(player.gray_federation_tokens ?? []).map((id, index) => {
                  const src = federationTokenBackImageSrc(id);
                  if (!src) return null;
                  return (
                    <img
                      key={`gray-${player.player_id}-${index}`}
                      className="federation-token-mini federation-token-mini--flipped"
                      src={src}
                      alt={`${player.nickname} 사용(회색면) 연방 토큰 ${id}`}
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
