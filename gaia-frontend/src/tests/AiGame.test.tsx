import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { AiTestView, startLine } from '../components/GameLobby/AiTestView';
import { CreateRoomView } from '../components/GameLobby/CreateRoomView';
import { LobbyHomeView } from '../components/GameLobby/LobbyHomeView';
import { api } from '../api/rest';
import { useRoomStore } from '../store/roomStore';
import { AI_TEST_FACTIONS, aiTestTurnOrder, otherBoardSide, readShownCounts } from '../aiTestDraw';
import type { FactionId } from '../types/game';

function dealtButtons(): HTMLElement[] {
  const group = screen.getByRole('group', { name: /이번 판 종족/ });
  return within(group).getAllByRole('button');
}

function dealtFactions(): FactionId[] {
  return dealtButtons().map((button) => button.dataset.faction as FactionId);
}

describe('AI test', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    useRoomStore.getState().actions.reset();
  });

  it('deals four factions of four different boards', () => {
    render(<AiTestView onGameCreated={vi.fn()} onBack={vi.fn()} />);
    const dealt = dealtFactions();
    expect(dealt).toHaveLength(4);
    expect(new Set(dealt).size).toBe(4);
    for (const faction of dealt) {
      expect(AI_TEST_FACTIONS).toContain(faction);
      expect(dealt).not.toContain(otherBoardSide(faction));
    }
  });

  it('starts a hard game on the fixed map with the picked faction and the other three as AI', async () => {
    const createAiGame = vi.spyOn(api, 'createAiGame').mockResolvedValue({
      room_code: 'AI1234',
      player_id: 5,
      session_token: 'token',
      game_setup: null as never,
      game_state: null as never,
      players: [{ player_id: 5, nickname: '나', ready: true }] as never,
      host_player_id: 5,
    });
    const onGameCreated = vi.fn();
    render(<AiTestView onGameCreated={onGameCreated} onBack={vi.fn()} />);
    fireEvent.change(screen.getByLabelText('닉네임'), { target: { value: '나' } });
    const dealt = dealtFactions();
    const order = aiTestTurnOrder(dealt);
    const picked = dealt[1];
    dealt.forEach((faction, index) => {
      expect(dealtButtons()[index]).toHaveTextContent(`${order.indexOf(faction) + 1}번 차례`);
    });
    fireEvent.click(dealtButtons()[1]);
    await waitFor(() => expect(onGameCreated).toHaveBeenCalled());
    expect(createAiGame).toHaveBeenCalledWith('나', 'hard', {
      seed: 'quartet-e-88365',
      faction: picked,
      aiFactions: order.filter((f) => f !== picked),
      seat: order.indexOf(picked) + 1,
    });
    const room = useRoomStore.getState();
    expect(room.roomCode).toBe('AI1234');
    expect(room.playerId).toBe(5);
    expect(room.manualControl).toBe(false);
    expect(room.roomState).toBe('faction_selection');
    // The started game's four factions are counted, so the next draw prefers the other fourteen.
    const shown = readShownCounts();
    expect(Object.keys(shown).sort()).toEqual([...dealt].sort());
    expect(Object.values(shown)).toEqual([1, 1, 1, 1]);
  });

  it('writes what a faction starts with as one line', () => {
    expect(startLine({
      faction: 'BalTaks',
      resources: {
        ore: 4,
        credits: 15,
        knowledge: 3,
        qic: 0,
        power: { bowl1: 2, bowl2: 4, bowl3: 0, gaia_bowl: 0, gaia_forming: 0 },
        spent_gaia_formers: 0,
      },
      research_tracks: { terraforming: 0, navigation: 0, ai: 0, gaia: 1, economy: 0, science: 0 },
    })).toBe('광석 4 · 크레딧 15 · 지식 3 · QIC 0 · 파워 2/4/0 · 시작 연구 가이아 1');
  });

  it('asks for a nickname before starting and counts nothing', () => {
    const createAiGame = vi.spyOn(api, 'createAiGame');
    render(<AiTestView onGameCreated={vi.fn()} onBack={vi.fn()} />);
    fireEvent.click(dealtButtons()[0]);
    expect(createAiGame).not.toHaveBeenCalled();
    expect(screen.getByText('닉네임을 입력해주세요')).toBeInTheDocument();
    expect(readShownCounts()).toEqual({});
  });

  it('sends setup_mode sequential with a fixed table and nothing extra without one', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation(async () => new Response('{}', { status: 200 }));
    await api.createAiGame('나', 'hard', { seed: 's1', faction: 'Ivits' });
    await api.createAiGame('나', 'normal');
    await api.createAiGame('나', 'hard', { seed: 's2', faction: 'Ivits', seat: 3 });
    const bodies = fetchMock.mock.calls.map(([, init]) => JSON.parse(String(init?.body)));
    expect(bodies[0]).not.toHaveProperty('human_seat');
    expect(bodies[1]).not.toHaveProperty('human_seat');
    expect(bodies[2]).toMatchObject({ seed: 's2', human_seat: 3 });
    expect(bodies[0]).toEqual({
      nickname: '나',
      ai_opponents: true,
      ai_level: 'hard',
      setup_mode: 'sequential',
      seed: 's1',
      faction: 'Ivits',
    });
    expect(bodies[1]).toEqual({ nickname: '나', ai_opponents: true, ai_level: 'normal' });
  });

  it('opens from its own entry on the lobby front page', async () => {
    vi.spyOn(api, 'listRooms').mockResolvedValue([]);
    const onAiTest = vi.fn();
    render(<LobbyHomeView onRoomJoined={vi.fn()} onCreateRoom={vi.fn()} onAiTest={onAiTest} />);
    fireEvent.click(await screen.findByRole('button', { name: /AI 테스트/ }));
    expect(onAiTest).toHaveBeenCalled();
  });

  it('is no longer part of the create-room view', () => {
    render(<CreateRoomView onRoomCreated={vi.fn()} onBack={vi.fn()} />);
    expect(screen.queryByRole('button', { name: /AI 3명과 대전/ })).not.toBeInTheDocument();
    expect(screen.queryByLabelText('종족 묶음')).not.toBeInTheDocument();
  });
});
