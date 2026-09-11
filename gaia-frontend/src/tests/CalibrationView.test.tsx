import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { CalibrationView } from '../components/CalibrationView';

describe('CalibrationView action sources', () => {
  it('offers named action sources and copies source identity with coordinates', () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
    render(<CalibrationView />);
    const selector = screen.getByRole('combobox', { name: '이미지 (배치할 소스) 액션 이미지' });
    expect(within(selector).getByRole('option', { name: '부스터 8 · 사거리 +3' })).toBeInTheDocument();
    expect(within(selector).getByRole('option', { name: '하이브 · 확장 종족 보드' })).toBeInTheDocument();
    expect(within(selector).getByRole('option', { name: '스페이스자이언트 · 확장 보드 행동 · 광산 건설 (테라포밍 2단계 무료)' })).toBeInTheDocument();
    expect(within(selector).getByRole('option', { name: '글린 · 확장 보드 행동 · 사거리 +2 (광산·가이아 프로젝트·함선 탐사)' })).toBeInTheDocument();
    fireEvent.change(selector, { target: { value: 'ship-Twilight-11' } });
    const img = screen.getByRole('img', { name: '트와일라잇 · +3 사거리 행동' });
    Object.defineProperties(img, {
      naturalWidth: { value: 1000 },
      naturalHeight: { value: 500 },
    });
    vi.spyOn(img, 'getBoundingClientRect').mockReturnValue({
      left: 0, top: 0, width: 500, height: 250,
      right: 500, bottom: 250, x: 0, y: 0, toJSON: () => ({}),
    });
    fireEvent.click(img, { clientX: 100, clientY: 50 });
    const panel = selector.closest('.calibration-panel') as HTMLElement;
    fireEvent.click(within(panel).getByRole('button', { name: 'px 좌표 복사' }));
    expect(writeText).toHaveBeenCalledWith(
      '트와일라잇 · +3 사거리 행동 [ship-Twilight-11]\n원본: 1000 × 500\n200, 100',
    );
    fireEvent.change(selector, { target: { value: 'standard-10' } });
    expect(within(panel).getByRole('button', { name: 'px 좌표 복사' })).toBeDisabled();
  });
  it('opens the large Moweyds board and keeps coordinates invariant at 200%', () => {
    window.history.replaceState({}, '', '/?calibrate=1&asset=Moweyds');
    try {
      render(<CalibrationView />);
      const img = screen.getByRole('img', { name: '모웨이드 · 의회 능력 · 파워 링 설치' });
      const zoom = screen.getByRole('combobox', { name: '모웨이드 보드 확대' });
      expect(zoom).toHaveValue('1');
      expect(img.parentElement).toHaveStyle({ width: '2323px' });
      Object.defineProperties(img, { naturalWidth: { value: 2323 }, naturalHeight: { value: 1489 } });
      fireEvent.change(zoom, { target: { value: '2' } });
      expect(img.parentElement).toHaveStyle({ width: '4646px' });
      vi.spyOn(img, 'getBoundingClientRect').mockReturnValue({
        left: -1000, top: -500, width: 4646, height: 2978,
        right: 3646, bottom: 2478, x: -1000, y: -500, toJSON: () => ({}),
      });
      fireEvent.click(img, { clientX: 246, clientY: 920 });
      expect(screen.getByText(/px \(623, 710\)/)).toBeInTheDocument();
      fireEvent.change(zoom, { target: { value: '1' } });
      expect(screen.getByText(/px \(623, 710\)/)).toBeInTheDocument();
    } finally {
      window.history.replaceState({}, '', '/');
    }
  });

});
