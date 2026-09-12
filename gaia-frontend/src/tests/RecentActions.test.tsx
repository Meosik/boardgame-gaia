import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { RecentActions } from '../components/RecentActions';

describe('RecentActions', () => {
  it('shows the supplied entries in order', () => {
    render(
      <RecentActions
        entries={[
          { index: 9, player: 1, text: '영희: 패스', details: [] },
          { index: 5, player: 0, text: '나: 항법 연구 2단계', details: [] },
        ]}
        onOpenLog={() => {}}
      />,
    );

    const items = screen.getAllByRole('listitem');
    expect(items[0]).toHaveTextContent('영희: 패스');
    expect(items[1]).toHaveTextContent('나: 항법 연구 2단계');
  });

  it('shows an empty state and opens the full log on request', () => {
    const onOpenLog = vi.fn();
    render(<RecentActions entries={[]} onOpenLog={onOpenLog} />);

    expect(screen.getByText('아직 기록된 행동이 없습니다.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '전체 기록' }));
    expect(onOpenLog).toHaveBeenCalledTimes(1);
  });
});
