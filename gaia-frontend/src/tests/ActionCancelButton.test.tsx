import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { ActionCancelButton } from '../components/ActionCancelButton';

it('places cancel beside the action and follows scrolling without covering its bounds', () => {
  const anchor = document.createElement('button');
  document.body.append(anchor);
  let top = 200;
  vi.spyOn(anchor, 'getBoundingClientRect').mockImplementation(() => ({
    x: 100, y: top, left: 100, right: 200, top, bottom: top + 40,
    width: 100, height: 40, toJSON: () => ({}),
  }));
  const onCancel = vi.fn();
  render(<ActionCancelButton anchor={anchor} onCancel={onCancel} />);
  const button = screen.getByRole('button', { name: '행동 취소' });
  expect(button).toHaveStyle({ left: '212px', top: '200px' });
  top = 300;
  fireEvent.scroll(window);
  expect(button).toHaveStyle({ top: '300px' });
  fireEvent.click(button);
  expect(onCancel).toHaveBeenCalledOnce();
  anchor.remove();
});
