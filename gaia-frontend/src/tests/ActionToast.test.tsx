import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ActionToast } from '../components/ActionToast';

describe('ActionToast', () => {
  it('renders nothing when there is no recent action', () => {
    const { container } = render(<ActionToast entry={null} myPlayerId={0} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("labels an opponent's action and lists its details", () => {
    render(
      <ActionToast
        entry={{ index: 4, player: 1, text: '영희: (1,-1)에 광산 건설', details: ['영희: 광석 -1, 크레딧 -2'] }}
        myPlayerId={0}
      />,
    );

    const toast = screen.getByRole('status');
    expect(toast).toHaveTextContent('방금');
    expect(toast).toHaveTextContent('영희: (1,-1)에 광산 건설');
    expect(toast).toHaveTextContent('영희: 광석 -1, 크레딧 -2');
    expect(toast).not.toHaveClass('action-toast--mine');
  });

  it('marks the viewing player as the actor', () => {
    render(
      <ActionToast entry={{ index: 7, player: 0, text: '나: 패스', details: [] }} myPlayerId={0} />,
    );

    expect(screen.getByRole('status')).toHaveClass('action-toast--mine');
    expect(screen.getByRole('status')).toHaveTextContent('내 행동');
  });
});
