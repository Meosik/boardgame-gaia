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
        expect(screen.getByText('0 / 30 · 판과 목표')).toBeInTheDocument();
        expect(screen.getAllByText(/원래 규칙에서는 받지 않는 것/)).toHaveLength(3);
        fireEvent.click(screen.getByRole('button', { name: '첫 수입 받기' }));
      }
      expect(screen.getByText(`${number} / 30 · ${step.title}`)).toBeInTheDocument();
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

  it('reveals each step board and reopens the free action list after the log tab', async () => {
    const states = frames();
    useGameStore.setState({ gameState: states[0], myPlayerId: 0 });
    const scroll = vi.fn();
    const original = HTMLElement.prototype.scrollIntoView;
    HTMLElement.prototype.scrollIntoView = scroll;
    try {
      render(<App />);
      fireEvent.click(screen.getByText('테스트 입장'));
      fireEvent.click(screen.getByText('첫 수입 받기'));
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
          const bowls = document.querySelectorAll('.game-table-player-card--me .faction-board-image-wrap [data-tutorial-target^="power:"]');
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
    state.tutorial!.step = 22;
    expect(tutorialTargets(state)).toContain('hex:-1,3');
    expect(tutorialTargets(state)).toContain('booster');
    state.tutorial!.step = 25;
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
    const state = frames()[index === 0 ? 13 : 26];
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
    fireEvent.click(screen.getByText('첫 수입 받기'));
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
    expect(screen.getByText('30 / 30 · 지금 게임이 끝난다면')).toBeInTheDocument();
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
    expect(screen.getByText('29 / 30 · 2라운드 수입과 가이아')).toBeInTheDocument();
    expect(screen.getByText('30 / 30 · 지금 게임이 끝난다면')).toBeInTheDocument();
    expect(screen.getByRole('table', { name: /종료 점수 미리보기/ })).toHaveTextContent('연구 트랙');
    expect(screen.getByRole('table', { name: /종료 점수 미리보기/ })).toHaveTextContent('자원 환산');
    expect(screen.getByRole('table', { name: /종료 점수 미리보기/ }).querySelectorAll('thead th')).toHaveLength(5);
    expect(state.round).toBe(2);
    expect(state.phase).toHaveProperty('ActionPhase');
  });
});
