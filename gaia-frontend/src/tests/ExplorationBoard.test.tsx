import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ExplorationBoard } from '../components/PlayerDashboard/ExplorationBoard';

describe('ExplorationBoard', () => {
  it('uses the faction-specific exploration board image and shows all starting shuttles', () => {
    render(<ExplorationBoard faction="Ambas" shuttlesAvailable={3} />);

    expect(screen.getByRole('img', { name: 'Ambas 탐사 보드' })).toBeInTheDocument();
    expect(screen.getAllByLabelText(/대기 중인 탐사 셔틀/)).toHaveLength(3);
    expect(screen.getByText('셔틀 3/3')).toBeInTheDocument();
  });

  it('removes deployed shuttles from the personal board and clamps invalid snapshots', () => {
    const { rerender } = render(<ExplorationBoard faction="Ambas" shuttlesAvailable={1} />);

    expect(screen.getAllByLabelText(/대기 중인 탐사 셔틀/)).toHaveLength(1);
    expect(screen.getByText('셔틀 1/3')).toBeInTheDocument();

    rerender(<ExplorationBoard faction="Ambas" shuttlesAvailable={8} />);
    expect(screen.getAllByLabelText(/대기 중인 탐사 셔틀/)).toHaveLength(3);
  });
});
