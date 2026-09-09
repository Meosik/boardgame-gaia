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
    expect(screen.getByAltText('1번 Ice 색상 위성')).toBeInTheDocument();
    expect(screen.getByAltText('7번 Titanium 색상 위성')).toBeInTheDocument();
    expect(screen.getAllByAltText(/번 .* 색상 위성/)).toHaveLength(7);
  });
});
