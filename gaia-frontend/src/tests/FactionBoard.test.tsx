import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { FactionBoard } from '../components/PlayerDashboard/FactionBoard';
import { factionBoardImageSrc } from '../assets/factionBoardImages';
import type { Structure } from '../types/game';

const resources = {
  ore: 4,
  credits: 15,
  knowledge: 3,
  qic: 1,
  power: { bowl1: 4, bowl2: 4, bowl3: 0, gaia_bowl: 0, gaia_forming: 0 },
  spent_gaia_formers: 0,
};

function structure(kind: Structure['kind']): Structure {
  return { hex: { q: 0, r: 0 }, kind };
}

describe('FactionBoard', () => {
  it('uses the normalized physical board coordinate system', () => {
    expect(factionBoardImageSrc('Ivits')).toContain('faction_boards/normalized/ivits.webp');
    expect(factionBoardImageSrc('Bescods')).toContain('faction_boards/normalized/bescods.webp');
    expect(factionBoardImageSrc('Firaks')).toContain('faction_boards/normalized/firaks.webp');
    expect(factionBoardImageSrc('Tinkeroids')).toContain('faction_boards/normalized/tinkeroids.webp');
  });

  it('renders the faction-specific board image and every unbuilt supply piece', () => {
    render(<FactionBoard faction="Terrans" structures={[]} />);

    expect(screen.getByRole('img', { name: 'Terrans 종족 보드' })).toBeInTheDocument();
    expect(screen.getAllByLabelText(/보유/)).toHaveLength(18);
    expect(screen.getAllByLabelText(/광산 보유/)).toHaveLength(8);
    expect(screen.getAllByLabelText(/교역소 보유/)).toHaveLength(4);
    expect(screen.getAllByLabelText(/연구소 보유/)).toHaveLength(3);
    expect(screen.getByLabelText('행성 의회 보유')).toBeInTheDocument();
    expect(screen.getByLabelText('과학 아카데미 보유')).toBeInTheDocument();
    expect(screen.getByLabelText('정보 큐브 아카데미 보유')).toBeInTheDocument();
  });

  it('removes built structures from the supply tracks left to right', () => {
    const structures = [
      structure('Mine'),
      structure('TradingStation'),
      structure('TradingStation'),
      structure('ResearchLab'),
      structure('PlanetaryInstitute'),
    ];
    render(<FactionBoard faction="Ivits" structures={structures} />);

    expect(screen.queryByLabelText('광산 보유 1')).not.toBeInTheDocument();
    expect(screen.getByLabelText('광산 보유 2')).toBeInTheDocument();
    expect(screen.queryByLabelText('교역소 보유 1')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('교역소 보유 2')).not.toBeInTheDocument();
    expect(screen.getByLabelText('교역소 보유 3')).toBeInTheDocument();
    expect(screen.queryByLabelText('연구소 보유 1')).not.toBeInTheDocument();
    expect(screen.getByLabelText('연구소 보유 2')).toBeInTheDocument();
    expect(screen.queryByLabelText('행성 의회 보유')).not.toBeInTheDocument();
  });

  it('removes only the matching academy type', () => {
    render(<FactionBoard faction="Xenos" structures={[structure({ Academy: 'Science' })]} />);

    expect(screen.queryByLabelText('과학 아카데미 보유')).not.toBeInTheDocument();
    expect(screen.getByLabelText('정보 큐브 아카데미 보유')).toBeInTheDocument();
  });

  it('places the current power tokens in their printed bowls', () => {
    render(
      <FactionBoard
        faction="Terrans"
        structures={[]}
        power={{ bowl1: 2, bowl2: 4, bowl3: 1, gaia_bowl: 3, gaia_forming: 0 }}
      />,
    );

    expect(screen.getAllByLabelText(/파워 영역 I 토큰/)).toHaveLength(2);
    expect(screen.getAllByLabelText(/파워 영역 II 토큰/)).toHaveLength(4);
    expect(screen.getAllByLabelText(/파워 영역 III 토큰/)).toHaveLength(1);
    expect(screen.getAllByLabelText(/파워 영역 G 토큰/)).toHaveLength(3);
  });

  it('places only currently available Gaiaformers in the faction-board slots', () => {
    render(<FactionBoard faction="Terrans" structures={[]} gaiaformersAvailable={2} />);

    expect(screen.getAllByLabelText(/사용 가능한 가이아포머/)).toHaveLength(2);
  });

  it('shows current resources directly above the faction board', () => {
    render(<FactionBoard faction="Terrans" structures={[]} resources={resources} />);

    const currentResources = screen.getByLabelText('현재 자원');
    expect(currentResources).toHaveTextContent('광석4');
    expect(currentResources).toHaveTextContent('크레딧15');
    expect(currentResources).toHaveTextContent('지식3');
    expect(currentResources).toHaveTextContent('정보 큐브1');
  });

  it('shows the three expensive planet colors and current Tinkering tile', () => {
    render(
      <FactionBoard
        faction="Tinkeroids"
        structures={[]}
        resources={resources}
        expensiveTerraformingPlanetTypes={['Terra', 'Ice', 'Titanium']}
        selectedTinkeringTile={2}
      />,
    );

    expect(screen.getByLabelText('테라포밍 3단계 색상: Terra, Ice, Titanium')).toBeInTheDocument();
    expect(screen.getByAltText('Terra 색상 위성')).toBeInTheDocument();
    expect(screen.getByAltText('Ice 색상 위성')).toBeInTheDocument();
    expect(screen.getByAltText('Titanium 색상 위성')).toBeInTheDocument();
    expect(screen.getByAltText('현재 팅커링 타일 2')).toBeInTheDocument();
  });

  it('places ore, knowledge and both 15-credit markers on the board resource track', () => {
    render(<FactionBoard faction="Terrans" structures={[]} resources={resources} />);

    expect(screen.getByLabelText('광석 트랙 4')).toBeInTheDocument();
    expect(screen.getByLabelText('지식 트랙 3')).toBeInTheDocument();
    expect(screen.getByLabelText('크레딧 첫 번째 마커 15')).toBeInTheDocument();
    expect(screen.getByLabelText('크레딧 두 번째 마커 0')).toBeInTheDocument();
  });

  it('fans out resource markers that occupy the same track value', () => {
    const overlappingResources = { ...resources, knowledge: 4, credits: 19 };
    render(<FactionBoard faction="Terrans" structures={[]} resources={overlappingResources} />);

    const leftPositions = [
      screen.getByLabelText('광석 트랙 4'),
      screen.getByLabelText('지식 트랙 4'),
      screen.getByLabelText('크레딧 두 번째 마커 4'),
    ].map((marker) => marker.style.left);
    expect(new Set(leftPositions)).toHaveProperty('size', 3);
  });

  it('keeps owned 정보 큐브 tokens in a separate personal supply beside the board', () => {
    render(<FactionBoard faction="Terrans" structures={[]} resources={{ ...resources, qic: 2 }} />);

    expect(screen.getByLabelText('개인 컴포넌트 보관 랙')).toBeInTheDocument();
    expect(screen.getAllByLabelText(/정보 큐브 보관 토큰/)).toHaveLength(2);
    expect(screen.getAllByLabelText(/정보 큐브 보관 토큰/)).toHaveLength(2);
  });

  it('renders owned tiles in the full-height side rack', () => {
    render(
      <FactionBoard
        faction="Terrans"
        structures={[]}
        resources={resources}
        techTiles={[5]}
        advancedTechTiles={[2]}
        federationTokens={[1]}
        booster={3}
        artifacts={[2]}
      />,
    );

    expect(screen.getByLabelText('개인 컴포넌트 보관 랙')).toBeInTheDocument();
    expect(screen.getByAltText('일반 기술 타일 5')).toBeInTheDocument();
    expect(screen.getByAltText('고급 기술 타일 2')).toBeInTheDocument();
    expect(screen.getByAltText('연방 토큰 1')).toBeInTheDocument();
    expect(screen.getByAltText('라운드 부스터 3')).toBeInTheDocument();
    expect(screen.getByAltText('아티팩트 2')).toBeInTheDocument();
  });
});
