import { ResourceTokens } from './ResourceTokens';
import { GamePieceIcon } from './GamePieceIcon';
import type { GameEvent, GamePhase, IncomeReceivedEvent, PlayerId } from '../types/game';

interface Props {
  events: GameEvent[];
  phase: GamePhase;
  playerId: PlayerId;
  round: number;
}

function hasStartedRound(events: GameEvent[], round: number): boolean {
  return events.some((event) => {
    if (typeof event !== 'object' || event === null || !('RoundStarted' in event)) return false;
    const payload = event.RoundStarted;
    return typeof payload === 'object' && payload !== null && 'round' in payload && payload.round === round;
  });
}

function incomeFor(
  events: GameEvent[],
  playerId: PlayerId,
  round: number,
): IncomeReceivedEvent['IncomeReceived'] | null {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index];
    if (typeof event !== 'object' || event === null || !('IncomeReceived' in event)) continue;
    const income = event.IncomeReceived as IncomeReceivedEvent['IncomeReceived'] | null;
    if (!income) continue;
    if (income.player === playerId && income.round === round) return income;
  }
  return null;
}

export function IncomeStatus({ events, phase, playerId, round }: Props) {
  const incomeFinished =
    typeof phase === 'object' &&
    phase !== null &&
    'ActionPhase' in phase &&
    hasStartedRound(events, round);
  const income = incomeFor(events, playerId, round);

  if (!incomeFinished || !income) return null;

  const resourceIncome = {
    ...(income.ore > 0 ? { ore: income.ore } : {}),
    ...(income.credits > 0 ? { credits: income.credits } : {}),
    ...(income.knowledge > 0 ? { knowledge: income.knowledge } : {}),
    ...(income.qic > 0 ? { qic: income.qic } : {}),
  };

  return (
    <div className="income-status" aria-label={`${round}라운드 수입 적용 완료`}>
      <span className="income-status-label">
        <b>{round === 1 ? '초기 수입' : `${round}R 수입`}</b>
        <span>받은 수입</span>
      </span>
      {Object.keys(resourceIncome).length > 0 && (
        <ResourceTokens compact label="이번 라운드 자원 수입" values={resourceIncome} />
      )}
      {income.power_charge > 0 && (
        <span className="income-power" aria-label={`파워 ${income.power_charge} 충전`}>
          <GamePieceIcon kind="power" /><strong>+{income.power_charge}</strong><small>충전</small>
        </span>
      )}
      {income.power_tokens > 0 && (
        <span className="income-power income-power--token" aria-label={`파워 토큰 ${income.power_tokens}개 획득`}>
          <GamePieceIcon kind="power" /><strong>+{income.power_tokens}</strong><small>토큰</small>
        </span>
      )}
      {income.vp > 0 && (
        <span className="income-vp" aria-label={`승점 ${income.vp}점 획득`}>
          <GamePieceIcon kind="vp" />
          승점 +{income.vp}점
        </span>
      )}
    </div>
  );
}
