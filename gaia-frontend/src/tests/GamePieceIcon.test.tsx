import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { GamePieceIcon, type GamePieceIconKind } from '../components/GamePieceIcon';

const EXPECTED_VIEW_BOX: Record<GamePieceIconKind, string> = {
  knowledge: '29 193 186 180',
  credits: '233 189 181 183',
  power: '428 188 183 185',
  qic: '628 179 168 211',
  ore: '814 177 193 196',
  vp: '1028 158 230 236',
  brainstone: '1273 163 189 227',
  'ivits-station': '1473 143 307 331',
  'action-used': '1789 129 363 364',
};

describe('GamePieceIcon', () => {
  it('maps every approved top-row component to its own crop', () => {
    render(
      <div>
        {(Object.keys(EXPECTED_VIEW_BOX) as GamePieceIconKind[]).map((kind) => (
          <GamePieceIcon key={kind} kind={kind} decorative={false} label={kind} />
        ))}
      </div>,
    );

    for (const [kind, viewBox] of Object.entries(EXPECTED_VIEW_BOX)) {
      expect(screen.getByRole('img', { name: kind })).toHaveAttribute('viewBox', viewBox);
    }
  });

  it('does not expose the excluded federation token as an icon kind', () => {
    expect(Object.keys(EXPECTED_VIEW_BOX)).not.toContain('federation');
  });
});
