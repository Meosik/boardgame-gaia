import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { GameLog } from '../components/GameLog';
import type { PlayerState } from '../types/game';

describe('GameLog', () => {
  it('renders a persisted free-action event with player and batch count', () => {
    const players = [{ player_id: 0, nickname: 'Gaia' }] as PlayerState[];
    render(
      <GameLog
        players={players}
        events={[{ FreeActionTaken: { player: 0, kind: 'OreToCredit', count: 3 } }]}
      />,
    );

    expect(screen.getByRole('listitem')).toHaveTextContent('Gaia: 광석 → 크레딧 ×3');
  });

  it('stays hidden when there are no supported log entries', () => {
    const { container } = render(<GameLog players={[]} events={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders regular actions, scoring, rounds, and game end events', () => {
    const players = [{ player_id: 0, nickname: 'Gaia' }] as PlayerState[];
    render(
      <GameLog
        players={players}
        events={[
          { StructureBuilt: { player: 0, hex: '1,-1', kind: 'Mine' } },
          { ResearchAdvanced: { player: 0, track: 'Navigation', level: 2 } },
          { VpAwarded: { player: 0, amount: 3, reason: { RoundTile: { tile_id: 4 } } } },
          { BoosterSelected: { player: 0, booster: 9 } },
          { PlayerPassed: { player: 0, booster: 7 } },
          { RoundEnded: { round: 1 } },
          { GameEnded: { final_scores: [100, 90, 80, 70] } },
        ]}
      />,
    );

    expect(screen.getByText(/Gaia: \(1,-1\)에 광산 건설/)).toBeInTheDocument();
    expect(screen.getByText(/Gaia: 항법 연구 2단계/)).toBeInTheDocument();
    expect(screen.getByText(/라운드 타일 #4로 3 VP/)).toBeInTheDocument();
    expect(screen.getByText(/Gaia: 초기 부스터 #9 선택/)).toBeInTheDocument();
    expect(screen.getByText(/Gaia: 패스 \(부스터 #7 반납\)/)).toBeInTheDocument();
    expect(screen.getByText('1라운드 종료')).toBeInTheDocument();
    expect(screen.getByText(/게임 종료 — 최종 점수 100 \/ 90 \/ 80 \/ 70/)).toBeInTheDocument();
  });
});
