import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { IncomeStatus } from '../components/IncomeStatus';
import { OpponentPanels } from '../components/OpponentPanels';
import { projectedIncome } from '../income';
import { GameLog } from '../components/GameLog';
import { frameForEvent, parseReplay } from '../replay/records';
import fixture from './fixtures/replay.json';

describe('income-enriched replay timeline', () => {
  it('keeps received income historical while sidebar production is independent of event playback', () => {
    const raw = structuredClone(fixture);
    const replay = parseReplay(raw);
    const player = replay.frames[1].state.players[0];
    const production = projectedIncome(player);
    replay.events = [
      { ReplayDecision: { player: 0, step: 1, round: 0,
        action: { type: 'SelectStartingBooster', booster_id: 4 }, net_changes: [] } },
      { IncomeReceived: { player: 0, round: 1, ore: 2, credits: 4, knowledge: 1,
        qic: 1, power_charge: 5, power_tokens: 2, vp: 0 } },
      { RoundStarted: { round: 1 } },
    ];
    replay.frames[0].event_end = 0;
    for (const frame of replay.frames.slice(1)) frame.event_end = 3;
    const View = ({ index }: { index: number }) => {
      const events = replay.events.slice(0, replay.frames[index].event_end);
      return <>
        <IncomeStatus events={events} phase={{ ActionPhase: { active_player: 0 } }} playerId={0} round={1} />
        <OpponentPanels players={[player]} events={events} round={1} />
        <GameLog players={[player]} events={events} />
      </>;
    };
    const { rerender } = render(<View index={0} />);
    expect(screen.queryByLabelText('1라운드 수입 적용 완료')).not.toBeInTheDocument();
    expect(screen.getByLabelText(`예상 수입 광석 ${production.ore}`)).toBeInTheDocument();
    rerender(<View index={1} />);
    expect(screen.getByLabelText('1라운드 수입 적용 완료')).toBeInTheDocument();
    expect(screen.getByLabelText(`예상 수입 광석 ${production.ore}`)).toBeInTheDocument();
    expect(screen.getByLabelText(`예상 수입 크레딧 ${production.credits}`)).toBeInTheDocument();
    expect(screen.getByLabelText('파워 5 충전')).toBeInTheDocument();
    expect(screen.getByLabelText('파워 토큰 2개 획득')).toBeInTheDocument();
    expect(screen.getByRole('listitem', { name: /1라운드 수입.*파워 충전 \+5.*파워 토큰 \+2/ })).toBeInTheDocument();
    expect(frameForEvent(replay.frames, 1)).toBe(1);
    expect(frameForEvent(replay.frames, 2)).toBe(1);
    rerender(<View index={0} />);
    expect(screen.queryByLabelText('1라운드 수입 적용 완료')).not.toBeInTheDocument();
    expect(screen.getByLabelText(`예상 수입 광석 ${production.ore}`)).toBeInTheDocument();
  });
});
