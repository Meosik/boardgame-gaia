import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
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

  it('shows an empty state when there are no supported log entries', () => {
    render(<GameLog players={[]} events={[]} />);
    expect(screen.getByText('아직 기록된 행동이 없습니다.')).toBeInTheDocument();
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

    expect(screen.getByRole('listitem', { name: /Gaia: \(1,-1\)에 광산 건설/ })).toBeInTheDocument();
    expect(screen.getByRole('listitem', { name: /Gaia: 항법 연구 2단계/ })).toBeInTheDocument();
    expect(screen.queryByText(/라운드 타일 #4로 승점 3점/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Gaia: 항법 연구 2단계/ }));
    expect(screen.getByText(/라운드 타일 #4로 승점 3점/)).toBeInTheDocument();
    expect(screen.getByRole('listitem', { name: /Gaia: 초기 부스터 #9 선택/ })).toBeInTheDocument();
    expect(screen.getByRole('listitem', { name: /Gaia: 패스 \(부스터 #7 반납\)/ })).toBeInTheDocument();
    expect(screen.getByRole('listitem', { name: '1라운드 종료' })).toBeInTheDocument();
    expect(screen.getByRole('listitem', { name: /게임 종료 — 최종 점수 100 \/ 90 \/ 80 \/ 70/ })).toBeInTheDocument();
  });
  it('shows protoplanet, QIC, federation copy, and tech VP reasons', () => {
    const players = [{ player_id: 0, nickname: 'Gaia' }] as PlayerState[];
    render(<GameLog players={players} events={[
      { VpAwarded: { player: 0, amount: 6, reason: 'ProtoPlanetColony' } },
      { VpAwarded: { player: 0, amount: 2, reason: 'QicAction' } },
      { VpAwarded: { player: 0, amount: 7, reason: { FederationToken: { token_kind: 3 } } } },
      { VpAwarded: { player: 0, amount: 4, reason: { TechTile: { tile_id: 16 } } } },
    ]} />);
    for (const label of ['원시 행성 식민지로 승점 6점', 'QIC 행동으로 승점 2점', '연방 토큰 #3 효과로 승점 7점', '기술 타일 #16로 승점 4점']) {
      expect(screen.getByRole('listitem', { name: new RegExp(label) })).toBeInTheDocument();
    }
  });

});


describe('collapsible action groups', () => {
  const players = [{ player_id: 0, nickname: 'Gaia' }, { player_id: 1, nickname: 'Other' }] as PlayerState[];
  it('folds each legacy Gaiaformer conversion separately and toggles its resource detail', () => {
    render(<GameLog players={players} events={Array.from({ length: 3 }, () => [
      { FreeActionTaken: { player: 0, kind: 'GaiaformerToQic', count: 1 } },
      { ResourceChanged: { player: 0, delta: { qic: 1 } } },
    ]).flat()} />);
    expect(screen.getAllByRole('listitem')).toHaveLength(3);
    const buttons = screen.getAllByRole('button');
    expect(buttons[0]).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText(/자원 변화/)).not.toBeInTheDocument();
    fireEvent.click(buttons[0]);
    expect(screen.getAllByText(/자원 변화 정보 큐브 \+1/)).toHaveLength(1);
    fireEvent.click(buttons[0]);
    expect(screen.queryByText(/자원 변화/)).not.toBeInTheDocument();
  });
  it('groups legacy research cost and VP but does not swallow another player or orphan reward', () => {
    render(<GameLog players={players} events={[
      { ResourceChanged: { player: 0, delta: { knowledge: -4 } } },
      { ResearchAdvanced: { player: 0, track: 'Navigation', level: 2 } },
      { VpAwarded: { player: 0, amount: 2, reason: 'QicAction' } },
      { ResourceChanged: { player: 1, delta: { qic: 1 } } },
    ]} />);
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
    expect(screen.getByRole('listitem', { name: /Other: 자원 변화/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /항법 연구/ }));
    expect(screen.getByText(/지식 -4/)).toBeInTheDocument();
    expect(screen.getByText(/승점 2점/)).toBeInTheDocument();
  });
  it('uses durable boundaries for same-player actions and resource-only power actions', () => {
    render(<GameLog players={players} events={[
      { ResourceChanged: { player: 0, delta: { knowledge: -4 } } },
      { ResearchAdvanced: { player: 0, track: 'Navigation', level: 1 } },
      { ResourceChanged: { player: 0, delta: { qic: 1 } } },
      { ActionLog: { player: 0, action: 'ResearchAdvance', event_count: 3 } },
      { ResourceChanged: { player: 0, delta: { ore: 2 } } },
      { ActionLog: { player: 0, action: 'PowerAction', event_count: 1 } },
    ]} />);
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
    fireEvent.click(screen.getByRole('button', { name: 'Gaia: 파워 행동' }));
    expect(screen.getByText(/광석 \+2/)).toBeInTheDocument();
    expect(screen.queryByText(/정보 큐브 \+1/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /항법 연구/ }));
    expect(screen.getByText(/정보 큐브 \+1/)).toBeInTheDocument();
  });
  it('retains 30 complete actions rather than 30 individual effects after reload', () => {
    const events = Array.from({ length: 31 }, (_, i) => [
      { FreeActionTaken: { player: 0, kind: 'OreToCredit', count: i + 1 } },
      { ResourceChanged: { player: 0, delta: { credits: i + 1 } } },
      { ActionLog: { player: 0, action: 'FreeAction', event_count: 2 } },
    ]).flat();
    render(<GameLog players={players} events={JSON.parse(JSON.stringify(events))} />);
    expect(screen.getAllByRole('listitem')).toHaveLength(30);
    expect(screen.getAllByRole('button')[0]).toHaveTextContent('×31');
  });
});

it('replay log retains old entries and seeks to source event indices', () => {
  const onSelect = vi.fn();
  const events = Array.from({ length: 35 }, (_, index) => ({ RoundStarted: { round: index + 1 } }));
  render(<GameLog players={[]} events={events} onEventSelect={onSelect} activeEventRange={[0, 1]} />);
  expect(screen.getAllByRole('listitem')).toHaveLength(35);
  fireEvent.click(screen.getByRole('button', { name: '1라운드 시작 시점으로 이동' }));
  expect(onSelect).toHaveBeenCalledWith(0);
});

it('labels replay state changes as net observations and exposes selected action details', () => {
  const players = [{ player_id: 0, nickname: 'Gaia' }] as PlayerState[];
  render(<GameLog players={players} onEventSelect={vi.fn()} events={[{
    ReplayDecision: { player: 0, step: 1, round: 1, action: { type: 'ResearchAdvance', track: 'Economy' },
      net_changes: [{ player: 0, delta: { vp: 3, knowledge: -4 } }] },
  }]} />);
  fireEvent.click(screen.getByRole('button', { name: '#1 · 1R Gaia: 연구 진전 · 경제' }));
  expect(screen.getByRole('listitem')).toHaveTextContent('Gaia 순변화: 승점 +3, 지식 -4');
  expect(screen.getByText(/자동 수입·라운드 전환·최종 정산/)).toBeInTheDocument();
  expect(screen.getByText(/선택 데이터:/)).toHaveTextContent('Economy');
});

describe('replay log follows the current action inside its own panel', () => {
  const events = Array.from({ length: 35 }, (_, index) => ({ RoundStarted: { round: index + 1 } }));
  const onSelect = vi.fn();
  const view = (range?: [number, number], replay = true) => (
    <div className="game-sidebar-tab-panel--log">
      <GameLog events={events} players={[]} onEventSelect={replay ? onSelect : undefined} activeEventRange={range} />
    </div>
  );

  beforeEach(() => {
    vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockReturnValue(200);
    vi.spyOn(HTMLElement.prototype, 'scrollHeight', 'get').mockReturnValue(1400);
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
      const panel = this.closest<HTMLElement>('.game-sidebar-tab-panel--log');
      const index = Number(this.getAttribute('aria-label')?.match(/^(\d+)라운드/)?.[1]) - 1;
      const top = this.tagName === 'LI' ? 100 + index * 40 - (panel?.scrollTop ?? 0) : 100;
      const height = this.tagName === 'LI' ? 40 : this.tagName === 'H3' ? 30 : 200;
      return { top, bottom: top + height, height } as DOMRect;
    });
  });
  afterEach(() => { vi.restoreAllMocks(); });

  it('reveals the current row on opening, then follows forward and backward seeks', () => {
    const { container, rerender } = render(view([20, 21]));
    const panel = container.firstElementChild as HTMLElement;
    expect(panel.scrollTop).toBe(640);
    rerender(view([30, 31]));
    expect(panel.scrollTop).toBe(1040);
    rerender(view([2, 3]));
    expect(panel.scrollTop).toBe(50); // Keep the row below the sticky log title.
    expect(screen.getByRole('listitem', { name: '3라운드 시작' })).toHaveAttribute('aria-current', 'step');
  });

  it('does not move visible rows or undo a manual scroll on unrelated renders', () => {
    const { container, rerender } = render(view([2, 3]));
    const panel = container.firstElementChild as HTMLElement;
    expect(panel.scrollTop).toBe(0);
    panel.scrollTop = 600;
    rerender(view([2, 3]));
    expect(panel.scrollTop).toBe(600);
    rerender(view([2, 4]));
    expect(panel.scrollTop).toBe(50);
  });

  it('leaves the live log and empty replay ranges alone', () => {
    const { container, rerender } = render(view([20, 21], false));
    const panel = container.firstElementChild as HTMLElement;
    expect(panel.scrollTop).toBe(0);
    rerender(view([0, 0]));
    expect(panel.scrollTop).toBe(0);
    rerender(view());
    expect(panel.scrollTop).toBe(0);
  });

  it('does not scroll the board/page when the log has no independently overflowing viewport', () => {
    vi.spyOn(HTMLElement.prototype, 'scrollHeight', 'get').mockReturnValue(200);
    const { container } = render(view([20, 21]));
    expect((container.firstElementChild as HTMLElement).scrollTop).toBe(0);
  });
});
