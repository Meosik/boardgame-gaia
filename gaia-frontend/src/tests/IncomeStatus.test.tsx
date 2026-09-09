import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { IncomeStatus } from '../components/IncomeStatus';

describe('IncomeStatus', () => {
  it('shows the resources and power received once the round income transition is complete', () => {
    render(
      <IncomeStatus
        events={[
          { IncomeReceived: {
            player: 0,
            round: 1,
            ore: 2,
            credits: 4,
            knowledge: 1,
            qic: 0,
            power_charge: 3,
            power_tokens: 1,
            vp: 0,
          } },
          { RoundStarted: { round: 1 } },
        ]}
        phase={{ ActionPhase: { active_player: 0 } }}
        playerId={0}
        round={1}
      />,
    );

    expect(screen.getByLabelText('1라운드 수입 적용 완료')).toBeInTheDocument();
    expect(screen.getByLabelText('광석 2')).toBeInTheDocument();
    expect(screen.getByLabelText('크레딧 4')).toBeInTheDocument();
    expect(screen.getByLabelText('지식 1')).toBeInTheDocument();
    expect(screen.getByLabelText('파워 3 충전')).toBeInTheDocument();
    expect(screen.getByLabelText('파워 토큰 1개 획득')).toBeInTheDocument();
  });

  it('does not claim completion while an income decision is still pending', () => {
    render(
      <IncomeStatus
        events={[
          { IncomeReceived: {
            player: 0,
            round: 1,
            ore: 1,
            credits: 0,
            knowledge: 0,
            qic: 0,
            power_charge: 0,
            power_tokens: 0,
            vp: 0,
          } },
          { RoundStarted: { round: 1 } },
        ]}
        phase={{ IncomeOrderPending: { queue: [], round: 0 } }}
        playerId={0}
        round={1}
      />,
    );

    expect(screen.queryByLabelText('1라운드 수입 적용 완료')).not.toBeInTheDocument();
  });
});
