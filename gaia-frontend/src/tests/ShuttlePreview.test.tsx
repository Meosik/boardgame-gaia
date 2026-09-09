import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ShuttlePreview } from '../components/ShuttlePreview';

describe('ShuttlePreview interaction prototype', () => {
  it('shows resource counts directly on their physical resource tokens', () => {
    render(<ShuttlePreview />);

    const interaction = screen.getByLabelText('보드 직접 조작 미리보기');
    const resources = within(interaction).getByLabelText('현재 자원');
    expect(within(resources).getByLabelText('광석 6')).toBeInTheDocument();
    expect(within(resources).getByLabelText('크레딧 15')).toBeInTheDocument();
    expect(within(resources).getByLabelText('지식 4')).toBeInTheDocument();
    expect(within(resources).getByLabelText('정보 큐브 3')).toBeInTheDocument();
  });

  it('shows building identity without a navigation-range overlay', () => {
    const { container } = render(<ShuttlePreview />);

    expect(container.querySelector('.structure-owner-ring')).not.toBeInTheDocument();
    expect(container.querySelector('.structure-type-badge')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('건설 사거리 미리보기')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '사거리 보기' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '사거리 숨기기' })).not.toBeInTheDocument();
    expect(container.querySelector('.range-overlay-active')).not.toBeInTheDocument();
  });

  it('separates mine construction cost from terraforming steps', () => {
    render(<ShuttlePreview />);

    fireEvent.click(screen.getByRole('button', { name: '빈 일반 행성 — 행동 보기' }));
    fireEvent.click(screen.getByRole('button', { name: '광산 건설' }));

    expect(screen.getByLabelText('광산 건설비: 광석 1, 크레딧 2')).toBeInTheDocument();
    expect(screen.getByLabelText('테라포밍 2단계')).toBeInTheDocument();
    expect(screen.queryByLabelText(/광산 건설비:.*정보 큐브/)).not.toBeInTheDocument();
  });

  it('opens contextual actions from a structure on the sector image', () => {
    render(<ShuttlePreview />);

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '내 광산 — 관련 행동 열기' }));

    expect(screen.getByRole('dialog', { name: '내 광산 행동 팝업' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '내 광산' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /교역소로 업그레이드/ })).toBeEnabled();
    expect(screen.getByRole('button', { name: /연방에 포함/ })).toBeEnabled();

    fireEvent.click(screen.getByRole('button', { name: '행동 취소' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('connects a spaceship action to an eligible planet target and confirmation tray', () => {
    render(<ShuttlePreview />);

    fireEvent.click(screen.getByRole('button', {
      name: /T F Mars — 크레딧 행동: 테라포밍 1단계 무료 광산.*사용 가능/,
    }));

    expect(screen.getByText('행성 선택')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '주황 행성 — 건설 대상' }));

    expect(screen.getByText('함선 크레딧 테라포밍')).toBeInTheDocument();
    expect(screen.getByText('테라포밍 1 무료')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '행동 확정' })).toBeEnabled();
  });

  it('shows one icon and the rulebook action name for each planet type', () => {
    render(<ShuttlePreview />);

    fireEvent.click(screen.getByRole('button', { name: '차원 변환 행성 — 행동 보기' }));
    expect(screen.getByRole('button', { name: '가이아 프로젝트 시작' })).toBeEnabled();

    fireEvent.click(screen.getByRole('button', { name: '소행성 — 행동 보기' }));
    expect(screen.getByRole('button', { name: '광산 건설' })).toBeEnabled();

    expect(screen.queryByText('행동 조합')).not.toBeInTheDocument();
    expect(screen.queryByText('선택한 대상')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '초기화' })).not.toBeInTheDocument();
    expect(screen.getByRole('tooltip')).toHaveTextContent('가이아포머 1개를 영구 소모');
    expect(screen.queryByText(/비용:/)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /함선 크레딧 행동/ })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '행동 취소' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('automatically places the unique shortest satellite route', () => {
    render(<ShuttlePreview />);

    fireEvent.click(screen.getByRole('button', { name: '내 광산 — 관련 행동 열기' }));
    fireEvent.click(screen.getByRole('button', { name: /연방에 포함/ }));

    expect(screen.getByLabelText('연방 파워 3 / 7')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '내 교역소 — 연방에서 제외' })).toBeEnabled();
    expect(screen.getByText(/인접 자동/)).toBeInTheDocument();
    expect(screen.getByText('인접 건물 자동 포함')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /건물을 더 선택하세요/ })).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: '내 아카데미 — 연방에서 포함' }));

    expect(screen.getByLabelText('연방 파워 8 / 7')).toBeInTheDocument();
    expect(screen.getByText(/내 아카데미 3 \+ 내 연구소 2 = 5/)).toBeInTheDocument();
    expect(screen.queryByText('내 아카데미 3 = 3')).not.toBeInTheDocument();
    expect(screen.getByText('최단 경로 자동 연결')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: '중앙 위성 자동 배치' })).toBeInTheDocument();
    expect(screen.getByLabelText('위성 1, 파워 1')).toBeInTheDocument();
    expect(screen.queryByLabelText('동일한 최단 위성 경로')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '연방 확정' })).toBeEnabled();
  });

  it('automatically toggles directly adjacent own structures as one federation group', () => {
    render(<ShuttlePreview />);

    fireEvent.click(screen.getByRole('button', { name: '내 광산 — 관련 행동 열기' }));
    fireEvent.click(screen.getByRole('button', { name: /연방에 포함/ }));

    expect(screen.getByLabelText('연방 파워 3 / 7')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '내 광산 — 연방에서 제외' })).toBeEnabled();
    expect(screen.getByRole('button', { name: '내 교역소 — 연방에서 제외' })).toBeEnabled();

    fireEvent.click(screen.getByRole('button', { name: '내 교역소 — 연방에서 제외' }));
    expect(screen.getByLabelText('연방 파워 0 / 7')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '내 광산 — 연방에서 포함' })).toBeEnabled();
  });

  it('automatically includes the adjacent academy and research lab from either endpoint', () => {
    render(<ShuttlePreview />);

    fireEvent.click(screen.getByRole('button', { name: '내 아카데미 — 관련 행동 열기' }));
    fireEvent.click(screen.getByRole('button', { name: /연방에 포함/ }));

    expect(screen.getByLabelText('연방 파워 5 / 7')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '내 아카데미 — 연방에서 제외' })).toBeEnabled();
    expect(screen.getByRole('button', { name: '내 연구소 — 연방에서 제외' })).toBeEnabled();
    expect(screen.getByText('인접 건물 자동 포함')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '내 연구소 — 연방에서 제외' }));

    expect(screen.getByLabelText('연방 파워 0 / 7')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '내 아카데미 — 연방에서 포함' })).toBeEnabled();
  });
});
