import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AiCoach } from '../components/AiCoach';
import { useGameStore } from '../store/gameStore';
import { useRoomStore } from '../store/roomStore';
import fixture from './fixtures/replay.json';
import type { Candidate } from '../components/AiCoach/protocol';

function position() {
  const state = structuredClone(fixture.frames[0].state);
  Object.assign(state.players[0], { tech_tiles: [10] });
  state.research_board.tech_tile_slots = [5, 10, 4, 9, 2, 3, 8, 7, 6];
  const candidates: Candidate[] = [
    { phase: 'Game', action: { type: 'Build', coord: '-3,-4' } },
    { phase: 'Game', action: { type: 'TechTileSpecialAction', tile: { pool: 'Standard', tile: 10 } } },
    ...[2, 4].map(tile => ({ phase: 'Game', action: { type: 'Upgrade', coord: '-1,-6', to: 'ResearchLab',
      tech_tile_choice: { kind: 'Standard', tile, advance_track: null } } })),
    ...['Navigation', 'Economy'].map(advance_track => ({ phase: 'Game', action: { type: 'Upgrade', coord: '-1,-6', to: 'ResearchLab',
      tech_tile_choice: { kind: 'Standard', tile: 6, advance_track } } })),
    { phase: 'Game', action: { type: 'Upgrade', coord: '-1,-6', to: 'PlanetaryInstitute', tech_tile_choice: null } },
    { phase: 'Game', action: { type: 'ResearchAdvance', track: 'Navigation' } },
    { phase: 'Game', action: { type: 'PowerAction', id: 3, coord: null } },
  ];
  return { schema: 1, session_id: 'board-test', token: 'test', status: 'ready',
    snapshot: { decision_id: 38, steps: 38, player: 0, state, candidates },
    recommendation: { index: 0, scores: candidates.map(() => ({ value: 1, reason: 'fixture', excluded: false })), audit: {} },
    config: { seed: 'board-test', delta_factions: [] }, recorded: 38, corrections: 0, last_feedback: null, error: null };
}
let data: ReturnType<typeof position>;
let posts: Record<string, unknown>[];
beforeEach(() => {
  useGameStore.getState().actions.reset(); useRoomStore.getState().actions.reset();
  data = position(); posts = [];
  vi.stubGlobal('fetch', vi.fn(async (_url: string, init?: RequestInit) => {
    if (init?.method === 'POST') posts.push(JSON.parse(String(init.body)));
    return { ok: true, json: async () => structuredClone(data) };
  }));
  Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() });
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); useGameStore.getState().actions.reset(); });

function hex(key: string) {
  const element = document.querySelector(`[aria-label="hex ${key}"]`);
  if (!element) throw Error(`Missing hex ${key}`);
  fireEvent.click(element);
}

describe('real coaching board selects without transport', () => {
  it('clicks the real four-power image without executing or opening a game socket', async () => {
    render(<AiCoach />);
    fireEvent.click(await screen.findByRole('button', { name: '기술 타일 · 파워 4 충전' }));
    expect(screen.getByRole('heading', { name: '사용자 선택' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '이유 저장 후 이 수 실행' })).toBeDisabled();
    expect(posts).toEqual([]);
    expect(useGameStore.getState().readOnly).toBe(true);
    expect(useGameStore.getState().wsClient).toBeNull();
    fireEvent.change(screen.getByLabelText('선택 이유'), { target: { value: '충전 확보' } });
    fireEvent.change(screen.getByLabelText('다음 계획'), { target: { value: '파워 행동' } });
    fireEvent.click(screen.getByRole('button', { name: '입력 완료 · 선택 유지' }));
    fireEvent.click(screen.getByRole('button', { name: '이유 저장 후 이 수 실행' }));
    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0]).toMatchObject({ decision_id: 38, index: 1 });
  });
  it('chooses an upgrade, a technology image and a free track through the actual board', async () => {
    render(<AiCoach />);
    await screen.findByText('보드에서 직접 선택');
    hex('-1,-6');
    expect(screen.getByRole('button', { name: 'AI 추천 승인 · 한 수 실행' })).toBeDisabled();
    const choices = document.querySelector('.coach-board-instructions .coach-board-choices')!;
    const researchLab = [...choices.querySelectorAll('button')].find(b => b.textContent?.includes('연구소'))!;
    expect(researchLab.querySelector('img')).not.toBeNull();
    fireEvent.click(researchLab);
    expect(screen.getByLabelText('받을 기술')).toHaveValue('');
    fireEvent.click(screen.getByRole('button', { name: '표준 기술 타일 6 선택' }));
    expect(screen.getByLabelText('올릴 연구 트랙')).toHaveValue('');
    expect(screen.getByRole('button', { name: 'AI 추천 승인 · 한 수 실행' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: '항법 트랙 선택' }));
    expect(screen.getByLabelText('올릴 연구 트랙')).toHaveValue('Navigation');
    fireEvent.change(screen.getByLabelText('선택 이유'), { target: { value: '확장 경로' } });
    fireEvent.change(screen.getByLabelText('다음 계획'), { target: { value: '가이아포밍' } });
    fireEvent.click(screen.getByRole('button', { name: '입력 완료 · 선택 유지' }));
    expect(posts).toHaveLength(0);
    fireEvent.click(screen.getByRole('button', { name: '이유 저장 후 이 수 실행' }));
    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0]).toMatchObject({ index: 4, technology_confirmed: true });
  });
  it('routes a research-board track click to the exact paid research candidate', async () => {
    render(<AiCoach />);
    fireEvent.click(await screen.findByRole('button', { name: '항법 트랙 연구 (지식 4)' }));
    expect(screen.getByRole('heading', { name: '사용자 선택' })).toBeInTheDocument();
    expect(posts).toHaveLength(0);
    fireEvent.change(screen.getByLabelText('선택 이유'), { target: { value: '사거리' } });
    fireEvent.change(screen.getByLabelText('다음 계획'), { target: { value: '광산' } });
    fireEvent.click(screen.getByRole('button', { name: '입력 완료 · 선택 유지' }));
    fireEvent.click(screen.getByRole('button', { name: '이유 저장 후 이 수 실행' }));
    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0]).toMatchObject({ index: 7 });
  });
  it('rejects a board action absent from native candidates instead of approving the previous suggestion', async () => {
    render(<AiCoach />);
    fireEvent.click(await screen.findByRole('button', { name: '경제 트랙 연구 (지식 4)' }));
    expect(screen.getByText('현재 합법 후보에 없는 선택입니다. 다른 대상을 골라 주세요.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'AI 추천 승인 · 한 수 실행' })).toBeDisabled();
    expect(posts).toHaveLength(0);
  });
});
