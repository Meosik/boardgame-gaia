import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { FactionTipCard } from '../components/FactionTipCard';
import { CreateRoomView } from '../components/GameLobby/CreateRoomView';
import { FACTION_DISPLAY_NAMES } from '../displayNames';
import { FACTION_TIPS } from '../factionTips';
import type { FactionId } from '../types/game';

describe('FactionTipCard', () => {
  it('has a tip with four non-empty parts for every faction', () => {
    const factions = Object.keys(FACTION_DISPLAY_NAMES) as FactionId[];
    for (const faction of factions) {
      const tip = FACTION_TIPS[faction];
      expect(tip, faction).toBeDefined();
      for (const part of [tip.ability, tip.institute, tip.tracks, tip.opening]) {
        expect(typeof part).toBe('string');
        expect(part.length).toBeGreaterThan(0);
      }
    }
    expect(Object.keys(FACTION_TIPS).length).toBe(Object.keys(FACTION_DISPLAY_NAMES).length);
  });

  it("shows the chosen faction's tip", () => {
    render(<FactionTipCard faction="Ivits" defaultOpen />);
    expect(screen.getByText('하이브 종족 팁')).toBeInTheDocument();
    expect(screen.getByText(FACTION_TIPS.Ivits.institute)).toBeInTheDocument();
  });

  it('follows the faction picked on the create-room view', () => {
    render(<CreateRoomView onRoomCreated={vi.fn()} onBack={vi.fn()} />);
    expect(screen.getByText('다카니안 종족 팁')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('내 종족'), { target: { value: 'BalTaks' } });
    expect(screen.getByText('발 타크 종족 팁')).toBeInTheDocument();
  });
});
