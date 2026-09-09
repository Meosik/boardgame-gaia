import { clsx } from 'clsx';
import { ResourceToken, VictoryPointToken, type DisplayResource } from '../ResourceTokens';
import { GamePieceIcon } from '../GamePieceIcon';
import {
  FACTION_STRUCTURE_COLOR,
  STRUCTURE_COLOR_HEX,
} from '../../assets/structureImages';
import type {
  EconomyResearchTileSide,
  GameEvent,
  IncomeReceivedEvent,
  PlayerState,
  ResearchTrack,
  ResearchTracks,
} from '../../types/game';

interface Props {
  players: PlayerState[];
  myPlayerId?: number;
  activePlayerId?: number | null;
  events?: GameEvent[];
  round?: number;
  economyResearchTileSide?: EconomyResearchTileSide;
  onPlayerSelect?: (player: PlayerState) => void;
}

interface IndexedIncome {
  income: IncomeReceivedEvent['IncomeReceived'];
  eventIndex: number;
}

interface RecurringTrackIncome {
  ore: number;
  credits: number;
  knowledge: number;
  qic: number;
  power_charge: number;
}

const EMPTY_TRACK_INCOME: RecurringTrackIncome = {
  ore: 0,
  credits: 0,
  knowledge: 0,
  qic: 0,
  power_charge: 0,
};

function latestIncome(
  events: GameEvent[],
  playerId: number,
  round: number | undefined,
): IndexedIncome | null {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index];
    if (!('IncomeReceived' in event)) continue;
    const income = event.IncomeReceived as IncomeReceivedEvent['IncomeReceived'] | undefined;
    if (!income) continue;
    if (income.player === playerId && (round === undefined || income.round === round)) {
      return { income, eventIndex: index };
    }
  }
  return null;
}

function trackLevel(tracks: ResearchTracks, track: ResearchTrack): number {
  switch (track) {
    case 'Terraforming': return tracks.terraforming;
    case 'Navigation': return tracks.navigation;
    case 'ArtificialIntelligence': return tracks.ai;
    case 'GaiaProject': return tracks.gaia;
    case 'Economy': return tracks.economy;
    case 'Science': return tracks.science;
  }
}

function trackIncome(
  tracks: ResearchTracks,
  economySide: EconomyResearchTileSide,
): RecurringTrackIncome {
  const result = { ...EMPTY_TRACK_INCOME };
  const economy = tracks.economy;
  if (economy === 1) {
    result.credits += 2;
    result.power_charge += 1;
  } else if (economy === 2) {
    result.ore += 1;
    result.credits += 2;
    result.power_charge += 2;
  } else if (economy === 3) {
    result.ore += 1;
    result.credits += economySide === 'VictoryPoints' ? 3 : 2;
    result.power_charge += economySide === 'VictoryPoints' ? 0 : 3;
  } else if (economy === 4) {
    result.ore += 2;
    result.credits += economySide === 'VictoryPoints' ? 4 : 2;
    result.power_charge += economySide === 'VictoryPoints' ? 0 : 2;
  }
  if (tracks.science >= 1 && tracks.science <= 4) {
    result.knowledge += tracks.science;
  }
  return result;
}

function projectedIncome(
  events: GameEvent[],
  player: PlayerState,
  round: number | undefined,
  economySide: EconomyResearchTileSide,
): IncomeReceivedEvent['IncomeReceived'] | null {
  const latest = latestIncome(events, player.player_id, round);
  if (!latest) return null;

  const incomeTimeTracks = { ...player.research_tracks };
  for (let index = latest.eventIndex + 1; index < events.length; index += 1) {
    const event = events[index];
    if (!('ResearchAdvanced' in event)) continue;
    const advance = event.ResearchAdvanced as {
      player?: number;
      track?: ResearchTrack;
    } | undefined;
    if (advance?.player !== player.player_id || !advance.track) continue;
    const current = trackLevel(incomeTimeTracks, advance.track);
    const previous = Math.max(0, current - 1);
    switch (advance.track) {
      case 'Terraforming': incomeTimeTracks.terraforming = previous; break;
      case 'Navigation': incomeTimeTracks.navigation = previous; break;
      case 'ArtificialIntelligence': incomeTimeTracks.ai = previous; break;
      case 'GaiaProject': incomeTimeTracks.gaia = previous; break;
      case 'Economy': incomeTimeTracks.economy = previous; break;
      case 'Science': incomeTimeTracks.science = previous; break;
    }
  }

  const before = trackIncome(incomeTimeTracks, economySide);
  const after = trackIncome(player.research_tracks, economySide);
  return {
    ...latest.income,
    ore: latest.income.ore + after.ore - before.ore,
    credits: latest.income.credits + after.credits - before.credits,
    knowledge: latest.income.knowledge + after.knowledge - before.knowledge,
    qic: latest.income.qic + after.qic - before.qic,
    power_charge: latest.income.power_charge + after.power_charge - before.power_charge,
  };
}

/** BGA-style always-open player status cards. The caller supplies the players
 * in turn order, including the controlled player. */
export function OpponentPanels({
  players,
  myPlayerId,
  activePlayerId = null,
  events = [],
  round,
  economyResearchTileSide = 'Power',
  onPlayerSelect,
}: Props) {
  if (players.length === 0) return null;

  return (
    <section className="opponent-panels" aria-label="플레이어 현황">
      {players.map((player, index) => {
        const income = projectedIncome(
          events,
          player,
          round,
          economyResearchTileSide,
        );
        const factionColor = player.faction
          ? STRUCTURE_COLOR_HEX[FACTION_STRUCTURE_COLOR[player.faction]]
          : '#64748b';
        const power = player.resources.power;

        return (
          <button
            type="button"
            key={player.player_id}
            className={clsx(
              'opponent-panel',
              player.player_id === myPlayerId && 'opponent-panel--me',
              player.player_id === activePlayerId && 'opponent-panel--active',
              player.passed && 'player-panel--passed',
            )}
            style={{ '--player-color': factionColor } as React.CSSProperties}
            aria-label={`${player.nickname} 개인 보드 보기`}
            onClick={() => onPlayerSelect?.(player)}
          >
            <span className="opponent-heading">
              <span className="opponent-turn-order" aria-label={`${index + 1}번째 행동 순서`}>
                {index + 1}
              </span>
              <span className="player-name">{player.nickname}</span>
              {player.player_id === myPlayerId && <span className="opponent-me-label">나</span>}
              {player.setup_bid_vp > 0 && (
                <span className="opponent-bid" aria-label={`비딩 감점 ${player.setup_bid_vp}점`}>
                  -{player.setup_bid_vp}점
                </span>
              )}
              <VictoryPointToken value={player.vp} />
            </span>
            <span className="opponent-resources" aria-label="보유 자원">
              <PlayerResource resource="credits" value={player.resources.credits} income={income?.credits ?? 0} />
              <PlayerResource resource="ore" value={player.resources.ore} income={income?.ore ?? 0} />
              <PlayerResource
                resource="knowledge"
                value={player.resources.knowledge}
                income={income?.knowledge ?? 0}
              />
              <PlayerResource resource="qic" value={player.resources.qic} income={income?.qic ?? 0} />
            </span>
            <span className="opponent-power-row" aria-label="파워 영역">
              <PowerBowl label="G" value={power.gaia_bowl} tone="gaia" brainstone={power.brainstone === 'Gaia'} />
              <PowerBowl label="I" value={power.bowl1} tone="one" brainstone={power.brainstone === 'Area1'} />
              <PowerBowl label="II" value={power.bowl2} tone="two" brainstone={power.brainstone === 'Area2'} />
              <PowerBowl label="III" value={power.bowl3} tone="three" brainstone={power.brainstone === 'Area3'} />
            </span>
            <span className="opponent-footer">
              <span className="opponent-income-power">이번 수입 충전 {income?.power_charge ?? 0}</span>
              {player.passed && <span className="passed-badge">패스</span>}
              <span className="opponent-board-link" aria-hidden>
                개인 보드 ›
              </span>
            </span>
          </button>
        );
      })}
    </section>
  );
}

function PlayerResource({
  resource,
  value,
  income,
}: {
  resource: DisplayResource;
  value: number;
  income: number;
}) {
  const labels: Record<DisplayResource, string> = {
    credits: '크레딧',
    ore: '광석',
    knowledge: '지식',
    qic: '정보 큐브',
    power: '파워',
  };

  return (
    <span className="opponent-resource-item">
      <ResourceToken resource={resource} value={value} />
      <small aria-label={`이번 수입 ${labels[resource]} ${income}`}>+{income}</small>
    </span>
  );
}

function PowerBowl({
  label,
  value,
  tone,
  brainstone,
}: {
  label: 'G' | 'I' | 'II' | 'III';
  value: number;
  tone: 'gaia' | 'one' | 'two' | 'three';
  brainstone: boolean;
}) {
  return (
    <span className={`opponent-power-bowl opponent-power-bowl--${tone}`} aria-label={`파워 ${label} 영역 ${value}`}>
      <b aria-hidden>
        <GamePieceIcon kind="power" className="opponent-power-token" />
        <span>{label}</span>
      </b>
      <strong>{value}</strong>
      {brainstone && (
        <GamePieceIcon
          kind="brainstone"
          className="opponent-brainstone"
          decorative={false}
          label="브레인스톤"
        />
      )}
    </span>
  );
}
