import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AiCoach } from '../components/AiCoach';
import { parseCoach } from '../components/AiCoach/protocol';
import type { Candidate } from '../components/AiCoach/protocol';
import { EMPTY_TECHNOLOGY, resolveTechnology, technologyVariants } from '../components/AiCoach/technology';
import { useGameStore } from '../store/gameStore';
import fixture from './fixtures/replay.json';
import type { ReactNode } from 'react';

vi.mock('../App', () => ({ App: ({ sidePanel }: { sidePanel: ReactNode }) => <main>{sidePanel}</main> }));
function response(status = 'ready', decision = 0, player = 0) {
  return { schema: 1, token: 'test-token', session_id: 'test', status,
    snapshot: { decision_id: decision, steps: decision, player, state: fixture.frames[0].state,
      candidates: [
        { phase: 'Setup', action: { type: 'PlaceStartingStructure', coord: '1,2' } },
        { phase: 'Action', action: { type: 'Upgrade', coord: '2,3', to: { Academy: 'Income' } } },
      ] },
    recommendation: status === 'ready' ? { index: 0, scores: [
      { value: 2, reason: 'real root score', excluded: false },
      { value: -1, reason: 'real lower score', excluded: false },
    ], audit: { ranking_mode: 'control', value_model: 'control' } } : null,
    config: { seed: 'test', delta_factions: ['Taklons'] }, error: null as string | null,
    recorded: decision, corrections: 0, last_feedback: null };
}
let current: ReturnType<typeof response>;
let requests: { url: string; init?: RequestInit }[];
function technologyResponse() {
  const value = structuredClone(response());
  value.snapshot.state.research_board.tech_tile_slots = [5, 10, 4, 9, 2, 3, 8, 7, 6];
  const variants: Candidate[] = [
    { kind: 'Standard', tile: 2, advance_track: null },
    { kind: 'Standard', tile: 10, advance_track: null },
    { kind: 'Standard', tile: 6, advance_track: 'Navigation' },
    { kind: 'Standard', tile: 6, advance_track: 'Economy' },
    { kind: 'Standard', tile: 6, advance_track: null },
  ].map(tech_tile_choice => ({ phase: 'Action', action: {
    type: 'Upgrade', coord: '2,3', to: 'ResearchLab', tech_tile_choice,
  } }));
  value.snapshot.candidates = variants as typeof value.snapshot.candidates;
  value.recommendation!.scores = variants.map((_, i) => ({ value: 10-i, reason: 'test', excluded: false }));
  return value;
}
beforeEach(() => {
  current = response(); requests = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    requests.push({ url, init });
    if (init?.method === 'POST') current = response('thinking', 1, 1);
    return { ok: true, json: async () => structuredClone(current) };
  }));
});
afterEach(() => { vi.unstubAllGlobals(); useGameStore.getState().actions.reset(); });

describe('approval-only coaching', () => {
  it('finds the standard power-charge action by its effect without executing it', async () => {
    current.snapshot.candidates[1] = { phase: 'Game', action: {
      type: 'TechTileSpecialAction', tile: { pool: 'Standard', tile: 10 },
    } } as unknown as typeof current.snapshot.candidates[number];
    render(<AiCoach />);
    const filter = await screen.findByLabelText('다른 합법 행동 찾기');
    fireEvent.change(filter, { target: { value: '파워 4 충전' } });
    expect(screen.getByRole('option', { name: /파워 4 충전 · 일반 10번 기술 행동/ })).toHaveValue('1');
    expect(screen.getByLabelText('합법 행동 선택').querySelectorAll('option')).toHaveLength(1);
    fireEvent.change(screen.getByRole('listbox'), { target: { value: '1' } });
    expect(requests.every(r => r.init?.method !== 'POST')).toBe(true);
  });
  it('groups upgrades but never preselects or implicitly accepts the recommended technology', async () => {
    current = technologyResponse();
    render(<AiCoach />);
    const picker = await screen.findByLabelText('받을 기술');
    expect(picker).toHaveValue('');
    expect(screen.getByLabelText('합법 행동 선택').querySelectorAll('option')).toHaveLength(1);
    const approve = screen.getByRole('button', { name: 'AI 추천 승인 · 한 수 실행' });
    expect(approve).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'AI 추천 수 선택' }));
    expect(approve).toBeDisabled();
    const economy = [...picker.querySelectorAll('option')].find(o => o.textContent?.includes('일반 2번'))!;
    fireEvent.change(picker, { target: { value: economy.value } });
    expect(screen.getByText('연결 트랙: 경제 (고정)')).toBeInTheDocument();
    expect(approve).toBeEnabled();
    fireEvent.click(approve);
    await screen.findByText('승인 1수 · 다른 선택 0건');
    expect(JSON.parse(String(requests.find(r => r.init?.method === 'POST')?.init?.body)))
      .toMatchObject({ index: 0, technology_confirmed: true });
  });
  it('requires an explicit free track and records the exact alternative with its rationale', async () => {
    current = technologyResponse();
    render(<AiCoach />);
    const picker = await screen.findByLabelText('받을 기술');
    const free = [...picker.querySelectorAll('option')].find(o => o.textContent?.includes('일반 6번'))!;
    fireEvent.change(picker, { target: { value: free.value } });
    const track = screen.getByLabelText('올릴 연구 트랙');
    expect(track).toHaveValue('');
    expect(screen.getByRole('button', { name: 'AI 추천 승인 · 한 수 실행' })).toBeDisabled();
    fireEvent.change(track, { target: { value: 'Navigation' } });
    const approve = screen.getByRole('button', { name: '이유 저장 후 이 수 실행' });
    expect(approve).toBeDisabled();
    fireEvent.change(screen.getByLabelText('선택 이유'), { target: { value: '인근 포밍 후보에 접근' } });
    fireEvent.change(screen.getByLabelText('다음 계획'), { target: { value: '항해 2레벨 후 포밍' } });
    fireEvent.click(screen.getByRole('button', { name: '입력 완료 · 선택 유지' }));
    fireEvent.click(approve);
    await screen.findByText('승인 1수 · 다른 선택 0건');
    expect(JSON.parse(String(requests.find(r => r.init?.method === 'POST')?.init?.body)))
      .toMatchObject({ index: 2, technology_confirmed: true, plan: '항해 2레벨 후 포밍' });
  });
  it('resolves fixed tracks, explicit no-advance, and bonus destinations without guessing', () => {
    const data = parseCoach(technologyResponse());
    const variants = technologyVariants(data.snapshot.candidates, 0, data.snapshot.state);
    expect(variants[1]).toMatchObject({ fixedTrack: true, track: 'Navigation' });
    expect(resolveTechnology(variants, EMPTY_TECHNOLOGY)).toBeNull();
    expect(resolveTechnology(variants, { tileKey: variants[4].tileKey, track: 'none', detail: null })).toBe(4);
    const bonus = ['1,2', '2,3'].map(bonus_build_coord => ({ phase: 'Action', action: {
      type: 'RebellionGainTechTile', tile: 11, track: 'Navigation', bonus_build_coord,
    } }));
    const details = technologyVariants(bonus, 0, data.snapshot.state);
    const selected = { tileKey: details[0].tileKey, track: 'Navigation', detail: null };
    expect(resolveTechnology(details, selected)).toBeNull();
    expect(resolveTechnology(details, { ...selected, detail: 1 })).toBe(1);
  });
  it('never executes on load or selection; the board is read-only with no game socket', async () => {
    render(<AiCoach />);
    await screen.findByRole('button', { name: 'AI 추천 승인 · 한 수 실행' });
    expect(requests.every(r => r.init?.method !== 'POST')).toBe(true);
    expect(useGameStore.getState().readOnly).toBe(true);
    expect(useGameStore.getState().wsClient).toBeNull();
    fireEvent.change(screen.getByRole('listbox'), { target: { value: '1' } });
    expect(requests.every(r => r.init?.method !== 'POST')).toBe(true);
    expect(screen.getByRole('group', { name: '이 수가 더 좋은 이유와 다음 계획은?' })).toBeInTheDocument();
  });
  it('requires reason and next plan, and double-click executes only once', async () => {
    render(<AiCoach />);
    await screen.findByRole('listbox');
    fireEvent.change(screen.getByRole('listbox'), { target: { value: '1' } });
    const button = screen.getByRole('button', { name: '이유 저장 후 이 수 실행' });
    expect(button).toBeDisabled();
    fireEvent.change(screen.getByLabelText('선택 이유'), { target: { value: '지식 생산이 필요함' } });
    expect(button).toBeDisabled();
    fireEvent.change(screen.getByLabelText('다음 계획'), { target: { value: '기술로 자원을 보충' } });
    fireEvent.click(screen.getByRole('button', { name: '입력 완료 · 선택 유지' }));
    expect(button).toBeEnabled();
    fireEvent.click(button); fireEvent.click(button);
    await screen.findByText('승인 1수 · 다른 선택 0건');
    const posts = requests.filter(r => r.init?.method === 'POST');
    expect(posts).toHaveLength(1);
    expect(JSON.parse(String(posts[0].init?.body))).toEqual({ decision_id: 0, index: 1,
      reason: '지식 생산이 필요함', plan: '기술로 자원을 보충' });
    expect(posts[0].init?.headers).toMatchObject({ 'X-Coach-Token': 'test-token' });
    expect(screen.queryByLabelText('선택 이유')).not.toBeInTheDocument();
  });
  it('accepts the recommendation with no fabricated human rationale', async () => {
    render(<AiCoach />);
    fireEvent.click(await screen.findByRole('button', { name: 'AI 추천 승인 · 한 수 실행' }));
    await screen.findByText('승인 1수 · 다른 선택 0건');
    expect(JSON.parse(String(requests.find(r => r.init?.method === 'POST')?.init?.body)))
      .toEqual({ decision_id: 0, index: 0, reason: '', plan: '' });
  });
  it.each([0, 1, 2, 3])('controls seat %i without advancing it', async player => {
    current = response('ready', player, player);
    render(<AiCoach />);
    await screen.findByRole('listbox');
    expect(useGameStore.getState().myPlayerId).toBe(player);
    expect(requests.some(r => r.init?.method === 'POST')).toBe(false);
  });
  it('shows inference failure without a fallback move', async () => {
    current = { ...response('error'), error: 'test inference failed' };
    render(<AiCoach />);
    expect(await screen.findByRole('alert')).toHaveTextContent('test inference failed');
    expect(screen.getByRole('button', { name: '추천 다시 계산' })).toBeInTheDocument();
    expect(requests.some(r => r.init?.method === 'POST')).toBe(false);
  });
  it('keeps the explanation when approval fails', async () => {
    vi.stubGlobal('fetch', vi.fn(async (_url: string, init?: RequestInit) => ({
      ok: init?.method !== 'POST', json: async () => init?.method === 'POST'
        ? { error: '이미 처리된 결정' } : structuredClone(current),
    })));
    render(<AiCoach />);
    await screen.findByRole('listbox');
    fireEvent.change(screen.getByRole('listbox'), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText('선택 이유'), { target: { value: '이유' } });
    fireEvent.change(screen.getByLabelText('다음 계획'), { target: { value: '계획' } });
    fireEvent.click(screen.getByRole('button', { name: '입력 완료 · 선택 유지' }));
    fireEvent.click(screen.getByRole('button', { name: '이유 저장 후 이 수 실행' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('이미 처리된 결정');
    fireEvent.click(screen.getByRole('button', { name: '선택 이유·계획 확인' }));
    expect(screen.getByLabelText('선택 이유')).toHaveValue('이유');
    expect(useGameStore.getState().gameState).toEqual(parseCoach(response()).snapshot.state);
  });
  it('rejects recommendation indices outside the legal list', () => {
    const value = response(); value.recommendation!.index = 500;
    expect(() => parseCoach(value)).toThrow('일치하지');
  });
  it('does not decode a human explanation as coordinates', () => {
    const value = { ...response(), last_feedback: { controller: 'human_override', reason: '1,2', plan: '3,4', player: 0, decision_id: 0 } };
    expect(parseCoach(value).last_feedback?.reason).toBe('1,2');
  });
});
