import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { App } from '../App';
import { RoundOneGuide } from '../components/Tutorial/RoundOneGuide';
import { useGameStore } from '../store/gameStore';
import { useRoomStore } from '../store/roomStore';
import { GaiaWebSocket, decodeHexCoordinates } from '../api/websocket';
import { matchesTutorialAction, tutorialTargets, tutorialPanel } from '../tutorial/round1';
import type { GameState } from '../types/game';
import fixture from './fixtures/tutorial-round1.json';

vi.mock('../components/GameLobby', () => ({
  GameLobby: ({ onGameStart }: { onGameStart: () => void }) => <button onClick={onGameStart}>테스트 입장</button>,
}));

function frames(): GameState[] {
  const value = structuredClone(fixture.initial) as Record<string, unknown>;
  const states = [decodeHexCoordinates(structuredClone(value)) as GameState];
  for (const delta of fixture.changes) {
    for (const change of delta) {
      let object = value;
      for (const key of change.path.slice(0, -1)) object = object[key] as Record<string, unknown>;
      object[change.path[change.path.length - 1]] = structuredClone(change.value);
    }
    states.push(decodeHexCoordinates(structuredClone(value)) as GameState);
  }
  return states;
}

function initial() { return decodeHexCoordinates(structuredClone(fixture.initial)) as GameState; }
function target(value: string) {
  const element = document.querySelector(`[data-tutorial-target="${value}"]`);
  expect(element, value).not.toBeNull();
  return element!;
}

function finishBoardTour() {
  for (let page = 0; page < 6; page++) {
    fireEvent.click(screen.getByRole('button', { name: '다음 영역' }));
  }
  fireEvent.click(screen.getByRole('button', { name: '둘러보기 마치기' }));
}

beforeEach(() => {
  useGameStore.getState().actions.reset();
  useRoomStore.getState().actions.reset();
  window.history.replaceState({}, '', '/');
});

describe('shared round-one tutorial', () => {
  it.each(initial().tutorial!.steps.map((step, index) => ({ step, number: index + 1 })))
   ('shows card and target for $number: $step.title', async ({ step, number }) => {
      const state = initial();
      state.tutorial!.step = number;
      render(<><button data-tutorial-target={step.target}>대상</button><button data-tutorial-target="unrelated">다른 대상</button><RoundOneGuide state={state} /></>);
      if (number === 1) {
        expect(screen.getByText('0 / 29 · 판과 목표')).toBeInTheDocument();
        expect(screen.getByText('가이아 프로젝트의 목표')).toBeInTheDocument();
        expect(screen.getByText(/마지막에 VP가 가장 많은 사람이 승리합니다/)).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: '수입 받기' })).not.toBeInTheDocument();
        for (let page = 0; page < 6; page++) {
          expect(screen.getByText(`판 둘러보기 ${page + 1} / 7`)).toBeInTheDocument();
          fireEvent.click(screen.getByRole('button', { name: '다음 영역' }));
        }
        expect(screen.getByText('한 라운드의 네 단계')).toBeInTheDocument();
        expect(screen.getByText('연습이라 자원·건물·연구를 미리 받았습니다.')).toBeInTheDocument();
        fireEvent.click(screen.getByText('이번 연습의 특별 설정과 시작 자원'));
        expect(screen.getAllByText(/원래 규칙에서는 받지 않는 것/)).toHaveLength(3);
        fireEvent.click(screen.getByRole('button', { name: '둘러보기 마치기' }));
        expect(screen.getByRole('button', { name: '수입 받기' })).toBeInTheDocument();
      }
      expect(screen.getByText(`${number} / 29 · ${step.title}`)).toBeInTheDocument();
      expect(screen.getByText(step.instruction)).toBeInTheDocument();
      expect(screen.getByText(step.reason)).toBeInTheDocument();
      await waitFor(() => expect(target(step.target)).toHaveClass('tutorial-highlight'));
      expect(target('unrelated')).not.toHaveClass('tutorial-highlight');
      expect(matchesTutorialAction(state.tutorial!, step.action)).toBe(true);
    });

  it('shows actual charging movement, VP cost and all three bowls', () => {
    const state = frames()[2];
    render(<RoundOneGuide state={state} />);
    expect(screen.getByLabelText('파워 충전 전후')).toHaveTextContent('충전 2 − 1 = 1 VP 지불');
    expect(screen.getByLabelText('파워 충전 전후')).toHaveTextContent('2 → 0');
    expect(screen.getByLabelText('파워 충전 전후')).toHaveTextContent('7 → 9');
    expect(tutorialTargets(state)).toEqual(expect.arrayContaining(['power:I', 'power:II', 'power:III']));
  });

  it('shows the spending flow when power is used for the first time', () => {
    render(<RoundOneGuide state={frames()[4]} />);
    expect(screen.getByLabelText('파워 사용 순환')).toHaveTextContent('1구역');
    expect(screen.getByLabelText('파워 사용 순환')).toHaveTextContent('3구역');
    expect(screen.getByLabelText('파워 사용 순환')).toHaveTextContent('3구역의 토큰 1개를 써서 1구역으로 되돌립니다.');
  });

  it('teaches costs, power, tiles, federation, and scoring at their first use', () => {
    const states = frames();
    const checks: [number, RegExp][] = [
      [2, /삽: 얼음 행성 1단계 × 광석 3.*QIC 1개.*광석 1·크레딧 2/],
      [3, /내 교역소 파워값 2/],
      [4, /광석 2·크레딧 6.*크레딧 3/],
      [5, /3구역 토큰이 1구역으로/],
      [6, /표준 기술은 바로 위 연구 트랙만/],
      [8, /가이아 구역.*테란은 2구역/],
      [11, /파워 3 → 광석 1.*바로 다음 공용 칸은 파워 4 → 광석 2/],
      [12, /파워 4 → 광석 2/],
      [13, /연방.*파워값 합이 7 이상/],
      [15, /목표 \(5, -6\)까지 2칸.*QIC 1개/],
      [16, /교역소 → 의회: 광석 4·크레딧 6/],
      [17, /연구소 → 아카데미: 광석 6·크레딧 6/],
      [24, /위성 2개.*위성마다 파워 토큰 1개/],
      [26, /초록 연방 토큰을 회색으로/],
    ];
    for (const [number, copy] of checks) {
      const { unmount, container } = render(<RoundOneGuide state={states[number - 1]} />);
      expect(container).toHaveTextContent(copy);
      unmount();
    }
    const { container } = render(<RoundOneGuide state={states[states.length - 1]} />);
    expect(container).toHaveTextContent(/일곱 색 행성.*테라포밍/);
    expect(container).toHaveTextContent(/최종 점수 타일 2개.*연구 점수와 남은 자원 환산/);
  });

  it('highlights income sources, the charging neighbor, Gaia area, and the shared power slot', () => {
    const states = frames();
    expect(tutorialTargets(states[0])).toEqual(expect.arrayContaining(['income:building', 'income:research', 'income:booster']));
    expect(tutorialTargets(states[2])).toEqual(expect.arrayContaining(['hex:-2,0', 'hex:-1,-1', 'power:I', 'power:III']));
    expect(tutorialTargets(states[7])).toContain('power:G');
    useGameStore.setState({ gameState: states[0], myPlayerId: 0 });
    render(<App />);
    fireEvent.click(screen.getByText('테스트 입장'));
    finishBoardTour();
    for (const key of ['income:building', 'income:research', 'income:booster']) expect(target(key)).toHaveClass('tutorial-highlight');
    expect(target('income:building')).toHaveClass('faction-board-exposed-income');
    expect(document.querySelectorAll('.research-board-token[data-tutorial-target="income:research"]')).toHaveLength(1);
    expect(target('income:research')).toHaveAttribute('aria-label', expect.stringMatching(/과학 4레벨/));
    expect(document.querySelectorAll('.game-table-player-card:not(.game-table-player-card--me) .tutorial-highlight[data-tutorial-target="income:building"]')).toHaveLength(0);
    expect(document.querySelectorAll('.game-table-player-card:not(.game-table-player-card--me) .tutorial-highlight[data-tutorial-target="income:booster"]')).toHaveLength(0);
    act(() => useGameStore.getState().actions.setGameState(states[2]));
    expect(document.querySelector('.tutorial-charge-source')).toBeInTheDocument();
    expect(document.querySelector('.tutorial-charge-range')).toHaveAttribute('aria-label', '파워 충전 거리 2칸');
    act(() => useGameStore.getState().actions.setGameState(states[7]));
    expect(document.querySelector('.game-table-player-card--me [data-tutorial-target="power:G"]')).toHaveClass('tutorial-highlight');
    act(() => useGameStore.getState().actions.setGameState(states[11]));
    expect(target('power:3')).toHaveClass('tutorial-highlight');
  });

  it('marks the actual resource track and printed building costs on my faction board', () => {
    const states = frames();
    useGameStore.setState({ gameState: states[0], myPlayerId: 0 });
    render(<App />);
    fireEvent.click(screen.getByText('테스트 입장'));
    for (let page = 0; page < 5; page++) fireEvent.click(screen.getByRole('button', { name: '다음 영역' }));
    const mine = document.querySelector('.game-table-player-card--me');
    expect(mine?.querySelectorAll('.faction-board-resource-marker[data-tutorial-target="resource:track"]')).toHaveLength(4);
    expect(mine?.querySelectorAll('.faction-board-resource-marker.tutorial-highlight')).toHaveLength(4);
    expect(mine?.querySelector('.faction-board-side-rack-qic')).toHaveClass('tutorial-highlight');
    expect(document.querySelectorAll('.game-table-player-card:not(.game-table-player-card--me) .faction-board-resource-marker.tutorial-highlight')).toHaveLength(0);
    expect(document.querySelectorAll('.game-table-player-card:not(.game-table-player-card--me) .faction-board-side-rack-qic.tutorial-highlight')).toHaveLength(0);
    fireEvent.click(screen.getByRole('button', { name: '다음 영역' }));
    fireEvent.click(screen.getByRole('button', { name: '둘러보기 마치기' }));
    for (const [frame, cost] of [[1, 'Mine'], [3, 'TradingStation'], [5, 'ResearchLab'], [15, 'PlanetaryInstitute'], [16, 'Academy']] as const) {
      act(() => useGameStore.getState().actions.setGameState(states[frame]));
      const marked = mine?.querySelector(`.faction-board-cost-highlight[data-tutorial-target="cost:${cost}"]`);
      expect(marked, cost).toHaveClass('tutorial-highlight');
      expect(document.querySelectorAll(`.game-table-player-card:not(.game-table-player-card--me) .tutorial-highlight[data-tutorial-target="cost:${cost}"]`)).toHaveLength(0);
    }
  });

  it('keeps the guide beside the board and introduces each area before play', () => {
    useGameStore.setState({ gameState: initial(), myPlayerId: 0 });
    render(<App />);
    fireEvent.click(screen.getByText('테스트 입장'));
    const guide = screen.getByLabelText('1라운드 따라 하기');
    expect(guide.closest('aside')).toHaveClass('game-sidebar--tutorial');
    expect(screen.getByText('가이아 프로젝트의 목표')).toBeInTheDocument();
    expect(document.querySelector('.tutorial-tour-highlight')).toBeNull();
    expect(screen.queryByRole('button', { name: '도움말' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '다음 영역' }));
    expect(document.getElementById('game-overview')).toHaveClass('tutorial-tour-highlight');
    fireEvent.click(screen.getByRole('button', { name: '다음 영역' }));
    expect(document.getElementById('game-map')).toHaveClass('tutorial-tour-highlight');
    fireEvent.click(screen.getByRole('button', { name: '다음 영역' }));
    expect(document.getElementById('game-research-section')).toHaveClass('tutorial-tour-highlight');
    fireEvent.click(screen.getByRole('button', { name: '다음 영역' }));
    expect(document.querySelector('.game-table-player-card--me')).toHaveClass('tutorial-tour-highlight');
    fireEvent.click(screen.getByRole('button', { name: '다음 영역' }));
    expect(screen.getByText('자원 트랙·파워 순환·교환')).toBeInTheDocument();
    expect(document.querySelector('.game-table-player-card--me .faction-board-resource-marker[data-tutorial-target="resource:track"]')).toHaveClass('tutorial-highlight');
    expect(target('power:III')).toHaveClass('tutorial-highlight');
    fireEvent.click(screen.getByRole('button', { name: '다음 영역' }));
    expect(screen.getByText('한 라운드의 네 단계')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '둘러보기 마치기' })).toHaveClass('round-one-primary');
  });

  it('reveals each step board and reopens the free action list after the log tab', async () => {
    const states = frames();
    useGameStore.setState({ gameState: states[0], myPlayerId: 0 });
    const scroll = vi.fn();
    const original = HTMLElement.prototype.scrollIntoView;
    HTMLElement.prototype.scrollIntoView = scroll;
    try {
      render(<App />);
      fireEvent.click(screen.getByText('테스트 입장'));
      finishBoardTour();
      fireEvent.click(screen.getByRole('tab', { name: /로그/ }));
      act(() => useGameStore.getState().actions.setGameState(states[3]));
      expect(screen.getByRole('tab', { name: /정보/ })).toHaveAttribute('aria-selected', 'true');
      const panels = states.slice(0, -1).filter((state, index, all) =>
        all.findIndex(other => tutorialPanel(other) === tutorialPanel(state)) === index);
      for (const state of panels) {
        scroll.mockClear();
        act(() => useGameStore.getState().actions.setGameState(state));
        const panel = document.getElementById(tutorialPanel(state)!);
        expect(panel).toBeVisible();
        if (state.tutorial!.steps[state.tutorial!.step - 1].action.type === 'ChargePower') {
          const bowls = document.querySelectorAll('.game-table-player-card--me .faction-board-image-wrap [data-tutorial-target="power:I"], .game-table-player-card--me .faction-board-image-wrap [data-tutorial-target="power:II"], .game-table-player-card--me .faction-board-image-wrap [data-tutorial-target="power:III"]');
          expect(bowls).toHaveLength(3);
          bowls.forEach(bowl => expect(bowl).toHaveClass('tutorial-highlight'));
        }
        await waitFor(() => expect(scroll.mock.instances.some(node => node === panel || panel!.contains(node as Node))).toBe(true));
      }
    } finally {
      HTMLElement.prototype.scrollIntoView = original;
    }
  });

  it('uses ship coordinates and every federation satellite as highlight targets', () => {
    const state = initial();
    state.tutorial!.step = 21;
    expect(tutorialTargets(state)).toContain('hex:-1,3');
    expect(tutorialTargets(state)).toContain('booster');
    state.tutorial!.step = 24;
    expect(tutorialTargets(state)).toEqual(expect.arrayContaining(['hex:-1,-3', 'hex:-1,-1', 'hex:-1,1', 'hex:-1,-2', 'hex:-1,0', 'federation:5']));
  });

  it('rejects another action or coordinate before transport, and sends the exact action', () => {
    const state = initial();
    const client = new GaiaWebSocket('TUTOR');
    vi.spyOn(client, 'isReady', 'get').mockReturnValue(true);
    const send = vi.spyOn(client, 'sendCommand').mockReturnValue('test-command');
    useGameStore.setState({ gameState: state, wsClient: client });
    const { sendAction } = useGameStore.getState().actions;
    expect(sendAction({ type: 'AcademyQicAction' })).toBeNull();
    expect(sendAction({ type: 'Build', coord: { q: 5, r: -6 } })).toBeNull();
    expect(send).not.toHaveBeenCalled();
    expect(useRoomStore.getState().lastError).toEqual({ code: 'TutorialStepMismatch', message: `지금은 ${state.tutorial!.steps[0].instruction}` });
    sendAction(state.tutorial!.steps[0].action);
    expect(send).toHaveBeenCalledTimes(1);
    expect(send).toHaveBeenCalledWith({ type: 'place_game_action', action: state.tutorial!.steps[0].action }, 0);
  });

  it('blocks wrong board clicks with guidance and opens the correct planet popup', async () => {
    const state = frames()[1];
    useGameStore.setState({ gameState: state, myPlayerId: 0 });
    const send = vi.spyOn(useGameStore.getState().actions, 'sendAction');
    render(<App />);
    fireEvent.click(screen.getByText('테스트 입장'));
    fireEvent.click(target('hex:5,-6'));
    expect(send).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent(`지금은 ${state.tutorial!.steps[1].instruction}`);
    fireEvent.click(target('hex:-1,1'));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    await waitFor(() => expect(target('hex:-1,1')).toHaveClass('tutorial-highlight'));
    send.mockRestore();
  });

  it.each([0, 1])('selects advanced technology through the actual board flow (%s)', index => {
    const state = frames()[index === 0 ? 12 : 25];
    const expected = state.tutorial!.steps[state.tutorial!.step - 1].action;
    useGameStore.setState({ gameState: state, myPlayerId: 0 });
    const client = new GaiaWebSocket('TUTOR');
    vi.spyOn(client, 'isReady', 'get').mockReturnValue(true);
    const send = vi.spyOn(client, 'sendCommand').mockReturnValue('test-command');
    useGameStore.setState({ wsClient: client, connectionReady: true });
    render(<App />);
    fireEvent.click(screen.getByText('테스트 입장'));
    fireEvent.click(target(index === 0 ? 'hex:3,-5' : 'hex:2,-4'));
    fireEvent.click(target('upgrade:ResearchLab'));
    fireEvent.click(target(index === 0 ? 'advanced:Science' : 'advanced:LostFleet'));
    fireEvent.click(target(index === 0 ? 'cover:10' : 'cover:4'));
    fireEvent.click(target('research:Terraforming'));
    expect(send).toHaveBeenCalledTimes(1);
    expect(send).toHaveBeenCalledWith({ type: 'place_game_action', action: expected }, 0);
  });

  it('plays every scripted action through the real board controls', () => {
    const states = frames();
    useGameStore.setState({ gameState: states[0], myPlayerId: 0 });
    const client = new GaiaWebSocket('TUTOR');
    vi.spyOn(client, 'isReady', 'get').mockReturnValue(true);
    const send = vi.spyOn(client, 'sendCommand').mockReturnValue('test-command');
    useGameStore.setState({ wsClient: client, connectionReady: true });
    render(<App />);
    fireEvent.click(screen.getByText('테스트 입장'));
    finishBoardTour();
    const click = (key: string) => fireEvent.click(target(key));
    const planet = (key: string, gaia = false) => {
      click(key);
      fireEvent.click(screen.getByRole('button', { name: gaia ? '가이아 프로젝트 시작' : '광산 건설' }));
      fireEvent.click(screen.getByRole('button', { name: '행동 확정' }));
      const ore = screen.queryByRole('button', { name: /광석 .*개 사용 확인/ });
      if (ore) fireEvent.click(ore);
    };
    for (let index = 0; index < states.length - 1; index++) {
      const expected = states[index].tutorial!.steps[index].action;
      send.mockClear();
      switch (expected.type) {
        case 'Build': case 'GaiaFormation':
          planet(`hex:${expected.coord.q},${expected.coord.r}`, expected.type === 'GaiaFormation'); break;
        case 'ChargePower': click('charge'); break;
        case 'FreeAction': click(`free:${expected.kind}`); break;
        case 'PowerAction': click(`power:${expected.id}`); break;
        case 'ResearchAdvance': click(`research:${expected.track}`); break;
        case 'TechTileSpecialAction': click(expected.tile.pool === 'Standard' ? 'tech:10' : 'advanced:21'); break;
        case 'ChooseIncomeOrder': click('tutorial:income'); break;
        case 'AcademyQicAction': click('academy'); break;
        case 'Upgrade': {
          click(`hex:${expected.coord.q},${expected.coord.r}`);
          click(`upgrade:${typeof expected.to === 'string' ? expected.to : `Academy:${expected.to.Academy}`}`);
          const choice = expected.tech_tile_choice;
          if (choice?.kind === 'Standard') click(`tech:${choice.tile}`);
          else if (choice) {
            click(choice.kind === 'Advanced' ? `advanced:${choice.track}` : 'advanced:LostFleet');
            click(`cover:${choice.covered_tile}`);
            click(`research:${choice.advance_track}`);
          }
          break;
        }
        case 'ExploreSpaceship': {
          const coord = states[index].board.spaceship_tiles[expected.ship]!;
          click(`hex:${coord.q},${coord.r}`);
          fireEvent.click(screen.getByRole('button', { name: '함선 탐사' }));
          fireEvent.click(screen.getByRole('button', { name: '함선 탐사 확정' }));
          break;
        }
        case 'ExamineArtifact': click(`artifact:${expected.artifact}`); break;
        case 'RoundBoosterRangeExploreSpaceship': click('booster'); click('hex:-1,3'); break;
        case 'SpaceshipCreditTerraform': click('action:SpaceshipCreditTerraform'); planet('hex:-4,0'); break;
        case 'FormFederation':
          [...expected.hexes, ...(expected.satellite_hexes ?? [])].forEach(coord => click(`hex:${coord.q},${coord.r}`));
          click('federation:5');
          fireEvent.click(screen.getByRole('button', { name: '확인' }));
          break;
        case 'TwilightReplayFederationToken': click('action:TwilightReplayFederationToken'); click('federation:5'); break;
        case 'Pass':
          click('pass');
          fireEvent.click(screen.getByRole('button', { name: /부스터 1 선택/ }));
          break;
        default: throw new Error(`missing browser step ${expected.type}`);
      }
      expect(send, `step ${index + 1}`).toHaveBeenCalledTimes(1);
      expect(matchesTutorialAction(states[index].tutorial!, send.mock.calls[0][0].type === 'place_game_action' ? send.mock.calls[0][0].action : expected)).toBe(true);
      act(() => {
        useGameStore.getState().actions.acceptActionCommand('test-command');
        useGameStore.getState().actions.setGameState(states[index + 1]);
      });
    }
    expect(screen.getByText('29 / 29 · 지금 게임이 끝난다면')).toBeInTheDocument();
  });

  it('renders income, effect timings, score sources and pass arithmetic from the server', () => {
    const states = frames();
    const { rerender } = render(<RoundOneGuide state={states[1]} />);
    for (const state of states.slice(1)) {
      rerender(<RoundOneGuide state={state} />);
      const tutorial = state.tutorial!;
      const step = tutorial.steps[tutorial.step - 1];
      if (step) {
        for (const timing of step.timings) {
          expect(screen.getByLabelText('효과 적용 시점')).toHaveTextContent(timing);
        }
      }
      for (const score of tutorial.feedback.scores) {
        expect(screen.getByLabelText('점수 출처')).toHaveTextContent(`${score.amount > 0 ? '+' : ''}${score.amount}점 · ${score.source}`);
      }
      expect(screen.getByText(`${state.round}라운드 수입 내역 · 수입 때마다`)).toBeInTheDocument();
    }
    expect(screen.getByLabelText('패스 계산 내역')).toHaveTextContent('연구소 2개 × 3점 = 6점');
    expect(screen.getByLabelText('패스 계산 내역')).toHaveTextContent('부스터 8 반납');
    expect(screen.getByLabelText('패스 계산 내역')).toHaveTextContent('상대 C → 튜토리얼 상대 A → 튜토리얼 상대 B → 나');
  });

  it('shows the round transition and all four final-score totals without ending the game', () => {
    const state = frames()[fixture.changes.length];
    render(<RoundOneGuide state={state} />);
    expect(screen.getByText('28 / 29 · 2라운드 수입과 가이아')).toBeInTheDocument();
    expect(screen.getByText('29 / 29 · 지금 게임이 끝난다면')).toBeInTheDocument();
    expect(screen.getByRole('table', { name: /종료 점수 미리보기/ })).toHaveTextContent('연구 트랙');
    expect(screen.getByRole('table', { name: /종료 점수 미리보기/ })).toHaveTextContent('자원 환산');
    expect(screen.getByRole('table', { name: /종료 점수 미리보기/ }).querySelectorAll('thead th')).toHaveLength(5);
    expect(state.round).toBe(2);
    expect(state.phase).toHaveProperty('ActionPhase');
  });
});
