import { GamePieceIcon } from '../GamePieceIcon';
import { artifactImageSrc } from '../../assets/artifactImages';
import {
  federationTokenBackImageSrc,
  federationTokenImageSrc,
} from '../../assets/federationTokenImages';
import { roundBoosterImageSrc } from '../../assets/roundBoosterImages';
import { advancedTechTileImageSrc, standardTechTileImageSrc } from '../../assets/techTileImages';
import type { ReactNode } from 'react';

interface Props {
  qic: number;
  techTiles: number[];
  advancedTechTiles: number[];
  coveredTechTiles: number[];
  federationTokens: number[];
  grayFederationTokens: number[];
  booster: number | null;
  artifacts: number[];
}

export function FactionBoardSideRack({
  qic,
  techTiles,
  advancedTechTiles,
  coveredTechTiles,
  federationTokens,
  grayFederationTokens,
  booster,
  artifacts,
}: Props) {
  const boosterSrc = booster === null ? undefined : roundBoosterImageSrc(booster);
  const uncoveredTechTiles = techTiles.filter((id) => !coveredTechTiles.includes(id));
  const visibleTechTileCount = uncoveredTechTiles.length + advancedTechTiles.length;
  const federationTokenCount = federationTokens.length + grayFederationTokens.length;

  return (
    <aside className="faction-board-side-rack" aria-label="개인 컴포넌트 보관 랙">
      <RackSection label="정보 큐브" className="faction-board-side-rack-qic">
        {qic > 0 ? (
          <div className="faction-board-side-rack-qic-tokens">
            {Array.from({ length: qic }, (_, index) => (
              <GamePieceIcon
                key={index}
                kind="qic"
                decorative={false}
                label={`정보 큐브 보관 토큰 ${index + 1}`}
              />
            ))}
          </div>
        ) : <EmptyRackSlot />}
      </RackSection>

      <RackSection label="기술" className="faction-board-side-rack-tech">
        <div className={`faction-board-side-rack-tiles${visibleTechTileCount > 2 ? ' faction-board-side-rack-tiles--dense' : ''}`}>
          {uncoveredTechTiles.map((id, index) => {
            const src = standardTechTileImageSrc(id);
            return src ? <img key={`std-${index}`} src={src} alt={`일반 기술 타일 ${id}`} /> : null;
          })}
          {advancedTechTiles.map((id, index) => {
            const advancedSrc = advancedTechTileImageSrc(id);
            const coveredId = coveredTechTiles[index];
            const coveredSrc = coveredId === undefined ? undefined : standardTechTileImageSrc(coveredId);
            if (!advancedSrc) return null;
            if (!coveredSrc) {
              return <img key={`adv-${index}`} src={advancedSrc} alt={`고급 기술 타일 ${id}`} />;
            }
            return (
              <span
                key={`covered-${index}`}
                className="faction-board-side-rack-tech-stack"
                aria-label={`일반 기술 타일 ${coveredId}를 덮은 고급 기술 타일 ${id}`}
              >
                <img
                  className="faction-board-side-rack-tech-covered"
                  src={coveredSrc}
                  alt={`덮인 일반 기술 타일 ${coveredId}`}
                />
                <img
                  className="faction-board-side-rack-tech-advanced"
                  src={advancedSrc}
                  alt={`고급 기술 타일 ${id}`}
                />
              </span>
            );
          })}
          {techTiles.length === 0 && advancedTechTiles.length === 0 && <EmptyRackSlot />}
        </div>
      </RackSection>

      <RackSection label="연방" className="faction-board-side-rack-federation">
        <div className={`faction-board-side-rack-tiles${federationTokenCount > 2 ? ' faction-board-side-rack-tiles--dense' : ''}`}>
          {federationTokens.map((id, index) => {
            const src = federationTokenImageSrc(id);
            return src ? <img key={`green-${index}`} src={src} alt={`연방 토큰 ${id}`} /> : null;
          })}
          {grayFederationTokens.map((id, index) => {
            const src = federationTokenBackImageSrc(id);
            return src ? (
              <img
                key={`gray-${index}`}
                className="faction-board-side-rack-tile--flipped"
                src={src}
                alt={`사용한 연방 토큰 ${id}`}
              />
            ) : null;
          })}
          {federationTokens.length === 0 && grayFederationTokens.length === 0 && <EmptyRackSlot />}
        </div>
      </RackSection>

      <RackSection label="부스터" className="faction-board-side-rack-booster">
        {boosterSrc ? <img src={boosterSrc} alt={`라운드 부스터 ${booster}`} /> : <EmptyRackSlot />}
      </RackSection>

      <RackSection label="아티팩트" className="faction-board-side-rack-artifact">
        <div className="faction-board-side-rack-tiles">
          {artifacts.map((id, index) => {
            const src = artifactImageSrc(id);
            return src ? (
              <span key={index} className="faction-board-side-rack-artifact-slot">
                <img src={src} alt={`아티팩트 ${id}`} />
              </span>
            ) : null;
          })}
          {artifacts.length === 0 && <EmptyRackSlot />}
        </div>
      </RackSection>
    </aside>
  );
}

function RackSection({
  label,
  className,
  children,
}: {
  label: string;
  className: string;
  children: ReactNode;
}) {
  return (
    <section className={`faction-board-side-rack-section ${className}`}>
      <strong>{label}</strong>
      <div className="faction-board-side-rack-content">{children}</div>
    </section>
  );
}

function EmptyRackSlot() {
  return <small className="faction-board-side-rack-empty">비어 있음</small>;
}
