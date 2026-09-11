import { useState, type ReactNode } from 'react';
import type { GameSetup, PreviewBoard } from '../../types/game';
import { GameBoard } from '../GameBoard';
import { ScoringBoard } from '../ScoringBoard';
import { RoundBoosters } from '../RoundBoosters';
import { FederationTokens } from '../FederationTokens';
import { SpaceshipBoards } from '../SpaceshipBoards';
import { BoardOverlay } from '../BoardOverlay';
import { PersonalBoardDrawer } from '../PersonalBoardDrawer';
import { FactionBoard } from '../PlayerDashboard/FactionBoard';
import { ResearchBoard } from '../PlayerDashboard/ResearchBoard';
import { LostFleetTechRequirementBoard } from '../LostFleetTechRequirementBoard';

interface Props {
  previewBoard: PreviewBoard | null;
  gameSetup: GameSetup | null;
  children: ReactNode;
}

/** Waiting and bidding share exactly the same board geometry and reference controls. */
export function SetupBoardLayout({ previewBoard, gameSetup, children }: Props) {
  const [activeOverlay, setActiveOverlay] = useState<'scoring' | 'boosters' | 'personal' | null>(null);
  return (
    <div className="waiting-room-view">
      {previewBoard && (
        <nav className="waiting-room-topbar" aria-label="게임 정보">
          <button
            className="waiting-room-top-control"
            onClick={() => setActiveOverlay((current) => current === 'scoring' ? null : 'scoring')}
          >
            라운드·게임 종료 목표
          </button>
          <button
            className="waiting-room-top-control"
            onClick={() => setActiveOverlay((current) => current === 'boosters' ? null : 'boosters')}
          >
            라운드 부스터
          </button>
          <button
            className="waiting-room-top-control"
            onClick={() => setActiveOverlay((current) => current === 'personal' ? null : 'personal')}
          >
            개인 보드
          </button>
        </nav>
      )}
      {previewBoard && (
        <aside className="waiting-room-board-rail" aria-label="게임 참조 보드">
          <section className="waiting-room-reference-card">
            <h3>연구 트랙</h3>
            <ResearchBoard players={[]} board={previewBoard.research_board} />
          </section>
          <section className="waiting-room-ship-list" aria-label="함선 보드 영역">
            <h3>함선 보드</h3>
            <SpaceshipBoards spaceshipBoards={previewBoard.spaceship_boards} players={[]} />
          </section>
        </aside>
      )}
      <div className="waiting-room-backdrop">
        {previewBoard ? (
          <>
            <GameBoard board={previewBoard.board} highlightDeepSpace highlightInterspace />
            <LostFleetTechRequirementBoard
              side={previewBoard.research_board?.lost_fleet_advanced_tech_requirement}
              tileId={previewBoard.research_board?.lost_fleet_advanced_tech_tile}
            />
          </>
        ) : (
          <p className="preview-loading">보드 미리보기 불러오는 중...</p>
        )}
      </div>
      <div className="waiting-room-overlay">
        <div className="waiting-room-panel">
          {children}
        </div>
      </div>
      {activeOverlay === 'scoring' && previewBoard && (
        <BoardOverlay title="라운드·게임 종료 목표" onClose={() => setActiveOverlay(null)}>
          <ScoringBoard
            roundTiles={previewBoard.round_tiles}
            finalScoringTiles={previewBoard.final_scoring_tiles}
            currentRound={0}
          />
        </BoardOverlay>
      )}
      {activeOverlay === 'boosters' && gameSetup && previewBoard && (
        <BoardOverlay title="라운드 부스터 · 연방 토큰" onClose={() => setActiveOverlay(null)}>
          <RoundBoosters availableBoosters={gameSetup.boosters} players={[]} />
          <FederationTokens
            availableTokens={previewBoard.research_board?.federation_tokens ?? []}
            players={[]}
          />
        </BoardOverlay>
      )}
      {activeOverlay === 'personal' && (
        <PersonalBoardDrawer onClose={() => setActiveOverlay(null)}>
          <div className="waiting-room-personal-board-example">
            <FactionBoard
              faction="Terrans"
              structures={[]}
              resources={{
                ore: 4,
                knowledge: 4,
                qic: 6,
                credits: 19,
                power: { bowl1: 4, bowl2: 4, bowl3: 0, gaia_bowl: 0, gaia_forming: 0 },
                spent_gaia_formers: 0,
              }}
              power={{ bowl1: 4, bowl2: 4, bowl3: 0, gaia_bowl: 0, gaia_forming: 0 }}
              gaiaformersAvailable={1}
              techTiles={[1, 2, 3, 4, 5, 6]}
              advancedTechTiles={[2, 3]}
              coveredTechTiles={[1, 2]}
              federationTokens={[1, 2, 3, 4, 5]}
              grayFederationTokens={[6]}
              booster={3}
              artifacts={[2, 7]}
            />
          </div>
        </PersonalBoardDrawer>
      )}
    </div>
  );
}
