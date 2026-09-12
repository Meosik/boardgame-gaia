import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { Tutorial } from '../components/Tutorial';
import { GUIDE_CATEGORIES, GUIDE_ENTRIES, searchGuide } from '../tutorial/guide';
import { FREE_ACTIONS } from '../components/freeActions';
import { POWER_ACTION_SPACES } from '../components/boardActionSpaces';
import { FACTION_DISPLAY_NAMES } from '../displayNames';

describe('guide content', () => {
  it('gives every entry a title, a one-line summary and details', () => {
    for (const entry of GUIDE_ENTRIES) {
      expect(entry.title, entry.id).not.toBe('');
      expect(entry.summary, entry.id).not.toBe('');
      expect(entry.detail.length, entry.id).toBeGreaterThan(0);
      expect(entry.detail.every((line) => line.trim() !== ''), entry.id).toBe(true);
    }
  });

  it('covers every category the tabs offer, with unique ids', () => {
    for (const category of GUIDE_CATEGORIES) {
      expect(GUIDE_ENTRIES.some((entry) => entry.category === category.id), category.id).toBe(true);
    }
    expect(new Set(GUIDE_ENTRIES.map((entry) => entry.id)).size).toBe(GUIDE_ENTRIES.length);
  });

  it('reads the shared tables rather than restating them, so costs cannot drift', () => {
    const powerEntry = GUIDE_ENTRIES.find((entry) => entry.id === 'action-power');
    for (const space of POWER_ACTION_SPACES) {
      expect(powerEntry?.detail.some((line) => line.includes(space.label)), space.label).toBe(true);
    }
    const freeEntry = GUIDE_ENTRIES.find((entry) => entry.id === 'free-conversions');
    for (const option of FREE_ACTIONS.filter((item) => !item.faction)) {
      expect(freeEntry?.detail.includes(option.label), option.label).toBe(true);
    }
  });

  it('describes every faction that can be dealt, under its shared display name', () => {
    const factionEntries = GUIDE_ENTRIES.filter((entry) => entry.category === 'faction');
    const ids = new Set(factionEntries.map((entry) => entry.id));
    const factions = Object.keys(FACTION_DISPLAY_NAMES) as (keyof typeof FACTION_DISPLAY_NAMES)[];

    for (const faction of factions) {
      expect(ids.has(`faction-${faction}`), faction).toBe(true);
      expect(
        factionEntries.some((entry) => entry.title === FACTION_DISPLAY_NAMES[faction]),
        faction,
      ).toBe(true);
    }
    expect(ids.size).toBe(factions.length);
  });

  it('carries the costs the engine actually charges', () => {
    const text = GUIDE_ENTRIES
      .map((entry) => [entry.title, entry.cost, entry.requires, ...entry.detail].join(' '))
      .join('\n');
    expect(text).toContain('광석 1 + 크레딧 2');   // MINE_ORE_COST / MINE_CREDITS_COST
    expect(text).toContain('지식 4');              // RESEARCH_KNOWLEDGE_COST
    expect(text).toContain('7 이상');              // FEDERATION_MIN_POWER
    expect(text).toContain('3 → 3 → 2 → 1 → 1 → 1'); // terraforming COST_PER_STEP
    expect(text).toContain('승점 5');              // SPACESHIP_DEPLOY_VP_COST
    expect(text).toContain('파워 6');              // ARTIFACT_EXAMINE_POWER_COST
  });
});

describe('searchGuide', () => {
  it('matches a word from any field and returns everything for a blank query', () => {
    expect(searchGuide(GUIDE_ENTRIES, '   ')).toHaveLength(GUIDE_ENTRIES.length);
    const federation = searchGuide(GUIDE_ENTRIES, '연방');
    expect(federation.some((entry) => entry.id === 'action-federation')).toBe(true);
    expect(federation.length).toBeLessThan(GUIDE_ENTRIES.length);
    expect(searchGuide(GUIDE_ENTRIES, '존재하지않는낱말')).toHaveLength(0);
  });
});

describe('Tutorial', () => {
  it('opens on the round flow and switches category on tab click', () => {
    render(<Tutorial />);
    expect(screen.getByText('게임 전체 구조')).toBeInTheDocument();
    expect(screen.queryByText('광산 건설')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: '주요 행동' }));
    expect(screen.getByText('광산 건설')).toBeInTheDocument();
    expect(screen.queryByText('게임 전체 구조')).not.toBeInTheDocument();
  });

  it('searches across categories, not just the open one', () => {
    render(<Tutorial />);
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: '아티팩트' } });

    expect(screen.getByText('아티팩트 조사')).toBeInTheDocument();
    expect(screen.getByText(/검색 결과/)).toBeInTheDocument();
  });

  it('says so when a search finds nothing', () => {
    render(<Tutorial />);
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'zzzz' } });
    expect(screen.getByText('찾는 내용이 없습니다. 다른 낱말로 검색해보세요.')).toBeInTheDocument();
  });

  it('shows a close button only when the caller can close it', () => {
    const onClose = vi.fn();
    const { rerender } = render(<Tutorial />);
    expect(screen.queryByRole('button', { name: '닫기' })).not.toBeInTheDocument();

    rerender(<Tutorial compact onClose={onClose} />);
    fireEvent.click(screen.getByRole('button', { name: '닫기' }));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
