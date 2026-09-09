import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { LostFleetTechRequirementBoard } from '../components/LostFleetTechRequirementBoard';

describe('LostFleetTechRequirementBoard', () => {
  it('places the assigned Advanced Tech tile on the selected requirement side', () => {
    render(<LostFleetTechRequirementBoard side="25-vp" tileId={7} />);

    expect(screen.getByAltText('승점 25점 이상 고급 기술 조건 보드')).toBeInTheDocument();
    expect(screen.getByAltText('Lost Fleet 조건 고급 기술 타일 7')).toBeInTheDocument();
  });

  it('does not invent a tile when the setup has none', () => {
    render(<LostFleetTechRequirementBoard side="exploration-shuttles" />);

    expect(screen.getByAltText('함선 3곳 탐사 고급 기술 조건 보드')).toBeInTheDocument();
    expect(screen.queryByAltText(/Lost Fleet 조건 고급 기술 타일/)).not.toBeInTheDocument();
  });
});
