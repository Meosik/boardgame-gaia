import { factionDisplayName } from '../../displayNames';
import { projectedIncome } from '../../income';
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
  PlayerState,
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

/** BGA-style always-open player status cards. The caller supplies the players
 * in turn order, including the controlled player. */
export function OpponentPanels({
  players,
  myPlayerId,
  activePlayerId = null,
  economyResearchTileSide = 'Power',
  onPlayerSelect,
}: Props) {
  if (players.length === 0) return null;

  return (
    <section className="opponent-panels" aria-label="플레이어 현황">
      {players.map((player, index) => {
        const income = projectedIncome(player, economyResearchTileSide);
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
            data-reward-player={player.player_id}
            aria-label={`${player.nickname} 개인 보드 보기`}
            onClick={() => onPlayerSelect?.(player)}
          >
            <span className="opponent-heading">
              <span className="opponent-turn-order" aria-label={`${index + 1}번째 행동 순서`}>
                {index + 1}
              </span>
              <span className="player-name">{player.nickname}</span>
              {player.faction && <span className="opponent-faction-name">{factionDisplayName(player.faction)}</span>}
              {player.player_id === myPlayerId && <span className="opponent-me-label">나</span>}
              {player.faction !== null && (
                <span className="opponent-bid" title={`종족 비딩 ${player.setup_bid_vp}점 · 최종 점수에서 차감`} aria-label={`비딩 감점 ${player.setup_bid_vp}점`}>
                  -{player.setup_bid_vp}점
                </span>
              )}
              <VictoryPointToken value={player.vp} rewardTarget />
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
              <PowerBowl
                label="G"
                value={power.gaia_bowl + power.gaia_forming}
                tone="gaia"
                brainstone={power.brainstone === 'Gaia'}
              />
              <PowerBowl label="I" value={power.bowl1} tone="one" brainstone={power.brainstone === 'Area1'} />
              <PowerBowl label="II" value={power.bowl2} tone="two" brainstone={power.brainstone === 'Area2'} />
              <PowerBowl label="III" value={power.bowl3} tone="three" brainstone={power.brainstone === 'Area3'} />
            </span>
            <span className="opponent-footer">
              <span className="opponent-income-power">예상 수입 충전 {income?.power_charge ?? 0}</span>
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
      <ResourceToken resource={resource} value={value} rewardTarget />
      <small title="현재 건물·기술·부스터 기준 수입. 이후 행동과 자원 보유 한도에 따라 실제 획득량은 달라질 수 있습니다." aria-label={`예상 수입 ${labels[resource]} ${income}`}>+{income}</small>
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
