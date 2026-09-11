import { spendablePower } from './freeActions';
import type { BoardState, GameAction, PlayerState } from '../types/game';

// Only prerequisite checks: target/technology choices remain in their existing flows.
export function shipActionPrerequisiteNotice(
  action: GameAction['type'], player: PlayerState, board: BoardState,
): string | null {
  if (action === 'TwilightReplayFederationToken') {
    if (player.federation_tokens.length + (player.gray_federation_tokens?.length ?? 0) === 0) {
      return '복사할 연방 토큰이 없습니다.';
    }
    return player.resources.qic < 3 ? '연방 토큰 효과 복사에 정보 큐브 3개가 필요합니다.' : null;
  }
  if (action !== 'RebellionFreeTradingStation' && action !== 'TwilightFreeResearchLab') return null;
  const laboratory = action === 'TwilightFreeResearchLab';
  const from = laboratory ? 'TradingStation' : 'Mine';
  const to = laboratory ? 'ResearchLab' : 'TradingStation';
  const targetExists = player.structures.some(({ kind, hex }) => {
    if (kind !== from) return false;
    const target = board.hexes[`${hex.q},${hex.r}`];
    return player.faction !== 'Lantids'
      || !target?.structures.some(({ owner }) => owner !== player.player_id);
  });
  if (!targetExists) return `업그레이드할 수 있는 ${laboratory ? '교역소' : '광산'}이 없습니다.`;
  if (player.structures.filter(({ kind }) => kind === to).length >= (laboratory ? 3 : 4)) {
    return `남은 ${laboratory ? '연구소' : '교역소'} 건물이 없습니다.`;
  }
  const power = spendablePower(player);
  if (power < 3) return '이 행동에는 사용 가능한 파워 3이 필요합니다.';
  const ore = laboratory ? 2 : 1;
  if (player.resources.ore < ore) return `이 행동에는 광석 ${ore}개가 필요합니다.`;
  return null;
}
