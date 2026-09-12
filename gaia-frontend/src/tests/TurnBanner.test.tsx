import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { TurnBanner } from '../components/TurnBanner';

describe('TurnBanner', () => {
  it('renders nothing without a status', () => {
    const { container } = render(<TurnBanner status={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("marks the viewing player's own turn and shows its hint", () => {
    render(<TurnBanner status={{ text: '내 차례입니다', mine: true, hint: '주요 행동 1개' }} />);

    const banner = screen.getByRole('status');
    expect(banner).toHaveTextContent('내 차례입니다');
    expect(banner).toHaveTextContent('주요 행동 1개');
    expect(banner).toHaveClass('turn-banner--mine');
  });

  it("shows another player's turn without the own-turn styling", () => {
    render(<TurnBanner status={{ text: '영희님 차례 — 기다리는 중', mine: false }} />);

    const banner = screen.getByRole('status');
    expect(banner).toHaveTextContent('영희님 차례 — 기다리는 중');
    expect(banner).not.toHaveClass('turn-banner--mine');
  });
});
