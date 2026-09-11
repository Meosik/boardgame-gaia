import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { TerraformingSelectionBoard } from '../components/GameLobby/TerraformingSelectionBoard';

describe('TerraformingSelectionBoard', () => {
  it('places all seven randomized base colors in numbered board slots', () => {
    render(
      <TerraformingSelectionBoard
        colorOrder={['Ice', 'Terra', 'Oxide', 'Desert', 'Volcanic', 'Swamp', 'Titanium']}
      />,
    );

    expect(screen.getByAltText('모웨이드와 팅커로이드 테라포밍 색상 순서 보드')).toHaveAttribute(
      'src',
      expect.stringContaining('terraforming_selection_board'),
    );
    expect(screen.getByAltText('1번 얼음 색상 위성')).toBeInTheDocument();
    expect(screen.getByAltText('7번 티타늄 색상 위성')).toBeInTheDocument();
    expect(screen.getAllByAltText(/번 .* 색상 위성/)).toHaveLength(7);
  });

  it('keeps allocated colors visible and identifies their faction', () => {
    render(<TerraformingSelectionBoard
      colorOrder={['Ice', 'Titanium', 'Oxide', 'Desert', 'Swamp', 'Terra', 'Volcanic']}
      allocations={[{ faction: 'Moweyds', colors: ['Desert', 'Oxide', 'Ice'] }]}
    />);
    expect(screen.getAllByAltText(/번 .* 색상 위성/)).toHaveLength(7);
    expect(screen.getAllByText('모웨이드')).toHaveLength(3);
    expect(screen.getByTitle('얼음: 모웨이드 테라포밍 3단계')).toBeInTheDocument();
  });

  it('shows both owners on shared colors and clears ownership on reset', () => {
    const colorOrder = ['Ice', 'Terra', 'Oxide', 'Desert', 'Volcanic', 'Swamp', 'Titanium'] as const;
    const { rerender } = render(<TerraformingSelectionBoard
      colorOrder={[...colorOrder]}
      allocations={[
        { faction: 'Moweyds', colors: ['Ice', 'Terra', 'Titanium'] },
        { faction: 'Tinkeroids', colors: ['Oxide', 'Desert', 'Titanium'] },
      ]}
    />);
    const shared = screen.getByTitle('티타늄: 모웨이드 · 팅커로이드 테라포밍 3단계');
    expect(shared.textContent).toContain('모웨이드');
    expect(shared.textContent).toContain('팅커로이드');
    expect(shared.style.borderTopColor).not.toBe(shared.style.borderRightColor);
    expect(screen.getAllByAltText(/번 .* 색상 위성/)).toHaveLength(7);
    rerender(<TerraformingSelectionBoard colorOrder={[...colorOrder]} />);
    expect(screen.queryByText('모웨이드')).not.toBeInTheDocument();
    expect(screen.getAllByAltText(/번 .* 색상 위성/)).toHaveLength(7);
  });
});
