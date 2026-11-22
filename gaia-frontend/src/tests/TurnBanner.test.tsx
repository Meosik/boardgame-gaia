import { act, fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
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

  it('shows a warning line under the turn sentence, and alone when there is no sentence', () => {
    const warning = '⚠ AI 교사 응답 없음 — 영희 차례에서 멈춤 (교사가 답하지 못함)';
    const { unmount } = render(<TurnBanner status={{ text: '영희님 차례 — 기다리는 중', mine: false }} warning={warning} />);
    expect(screen.getByRole('status')).toHaveTextContent('영희님 차례 — 기다리는 중');
    expect(screen.getByRole('status')).toHaveTextContent(warning);
    expect(screen.queryByRole('button')).toBeNull();
    unmount();

    render(<TurnBanner status={null} warning={warning} />);
    expect(screen.getByRole('status')).toHaveTextContent(warning);
    expect(screen.getByRole('status')).not.toHaveClass('turn-banner--mine');
  });

  it('offers the action that answers the warning, disabled while it runs', () => {
    const onClick = vi.fn();
    const warning = '⚠ AI 교사 응답 없음 — 영희 차례에서 멈춤 (교사가 답하지 못함)';
    const { rerender } = render(
      <TurnBanner status={null} warning={warning} warningAction={{ label: '다시 시도', onClick }} />,
    );
    fireEvent.click(screen.getByRole('button', { name: '다시 시도' }));
    expect(onClick).toHaveBeenCalledTimes(1);

    rerender(
      <TurnBanner status={null} warning={warning} warningAction={{ label: '교사 부르는 중…', busy: true, onClick }} />,
    );
    expect(screen.getByRole('button', { name: '교사 부르는 중…' })).toBeDisabled();
  });

  it("shows another player's turn without the own-turn styling", () => {
    render(<TurnBanner status={{ text: '영희님 차례 — 기다리는 중', mine: false }} />);

    const banner = screen.getByRole('status');
    expect(banner).toHaveTextContent('영희님 차례 — 기다리는 중');
    expect(banner).not.toHaveClass('turn-banner--mine');
  });

  it('counts the seconds the game has waited on another seat, and not beside a stall warning', () => {
    vi.useFakeTimers();
    try {
      const status = { text: '영희님 차례 — 기다리는 중', mine: false, waitingFor: 1 };
      const { rerender } = render(<TurnBanner status={status} waitKey="10" />);
      expect(screen.getByRole('status')).not.toHaveTextContent('경과');

      act(() => { vi.advanceTimersByTime(5000); });
      expect(screen.getByRole('status')).toHaveTextContent('5초 경과');

      // The game moved on: the count starts again.
      rerender(<TurnBanner status={status} waitKey="11" />);
      expect(screen.getByRole('status')).not.toHaveTextContent('경과');

      act(() => { vi.advanceTimersByTime(4000); });
      expect(screen.getByRole('status')).toHaveTextContent('4초 경과');
      rerender(<TurnBanner status={status} waitKey="11" warning="⚠ AI 교사 응답 없음" />);
      expect(screen.getByRole('status')).not.toHaveTextContent('경과');
    } finally {
      vi.useRealTimers();
    }
  });

  it('shows no count for a turn of the viewing player or without a wait key', () => {
    vi.useFakeTimers();
    try {
      const { unmount } = render(<TurnBanner status={{ text: '내 차례입니다', mine: true }} waitKey="10" />);
      act(() => { vi.advanceTimersByTime(5000); });
      expect(screen.getByRole('status')).not.toHaveTextContent('경과');
      unmount();

      render(<TurnBanner status={{ text: '영희님 차례 — 기다리는 중', mine: false, waitingFor: 1 }} />);
      act(() => { vi.advanceTimersByTime(5000); });
      expect(screen.getByRole('status')).not.toHaveTextContent('경과');
    } finally {
      vi.useRealTimers();
    }
  });
});
