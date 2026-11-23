import { useEffect, useState } from 'react';
import { roundBoosterImageSrc } from '../assets/roundBoosterImages';
import { finalPassConversionGain } from './freeActions';
import type { PlayerState } from '../types/game';

interface TopPassControlProps {
  player: PlayerState;
  round: number;
  availableBoosters: number[];
  isMyTurn: boolean;
  onPass: (boosterId: number | null) => void;
  onChooseBooster?: () => void;
}

export function TopPassControl({
  player,
  round,
  availableBoosters,
  isMyTurn,
  onPass,
  onChooseBooster,
}: TopPassControlProps) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const [selectedBoosterId, setSelectedBoosterId] = useState<number | null>(null);
  const [conversionPromptOpen, setConversionPromptOpen] = useState(false);
  const controlsDisabled = !isMyTurn || player.passed;
  const requiresBoosterChoice = round < 6 && player.booster != null;
  const selectedImageSrc = selectedBoosterId === null ? null : roundBoosterImageSrc(selectedBoosterId);
  const conversionGain = finalPassConversionGain(player);
  const conversionParts = [
    conversionGain.power > 0 ? `3구역 파워 ${conversionGain.power}(→ 돈)` : null,
    conversionGain.qic > 0 ? `정보 큐브 ${conversionGain.qic}(→ 광석)` : null,
  ].filter((part): part is string => part !== null);

  useEffect(() => {
    setPickerOpen(false);
    setSelectedBoosterId(null);
    setConversionPromptOpen(false);
  }, [round, player.booster]);

  useEffect(() => {
    if (selectedBoosterId !== null && !availableBoosters.includes(selectedBoosterId)) {
      setSelectedBoosterId(availableBoosters[0] ?? null);
    }
  }, [availableBoosters, selectedBoosterId]);

  const handlePassClick = () => {
    if (!requiresBoosterChoice) {
      if (round >= 6 && conversionGain.vp > 0) {
        setConversionPromptOpen(true);
        return;
      }
      onPass(null);
      return;
    }
    if (onChooseBooster) {
      onChooseBooster();
      return;
    }
    setSelectedBoosterId(availableBoosters[0] ?? null);
    setPickerOpen(true);
  };

  return (
    <>
      <button
        type="button"
        className="game-top-control game-top-pass-control"
        disabled={controlsDisabled || (requiresBoosterChoice && availableBoosters.length === 0)}
        data-tutorial-target="pass"
        onClick={handlePassClick}
      >
        패스
      </button>

      {pickerOpen && (
        <div className="booster-preview-scrim" role="presentation" onMouseDown={() => setPickerOpen(false)}>
          <section
            className="booster-preview-dialog pass-booster-dialog"
            role="dialog"
            aria-modal="true"
            aria-label="패스 후 받을 라운드 부스터 선택"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <h2>패스 · 라운드 부스터 선택</h2>
            <div className="pass-booster-picker">
              <div className="pass-booster-options" aria-label="선택 가능한 라운드 부스터">
                {availableBoosters.map((boosterId) => {
                  const imageSrc = roundBoosterImageSrc(boosterId);
                  return (
                    <button
                      key={boosterId}
                      type="button"
                      className={`pass-booster-option${selectedBoosterId === boosterId ? ' selected' : ''}`}
                      aria-label={`라운드 부스터 ${boosterId} 미리 보기`}
                      aria-pressed={selectedBoosterId === boosterId}
                      onClick={() => setSelectedBoosterId(boosterId)}
                    >
                      {imageSrc ? <img src={imageSrc} alt="" /> : <span>{boosterId}</span>}
                    </button>
                  );
                })}
              </div>
              <div className="pass-booster-large-preview">
                {selectedBoosterId !== null && selectedImageSrc ? (
                  <img src={selectedImageSrc} alt={`라운드 부스터 ${selectedBoosterId}`} />
                ) : (
                  <p>확인할 부스터를 선택하세요.</p>
                )}
              </div>
            </div>
            <div className="booster-preview-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setPickerOpen(false)}>
                닫기
              </button>
              <button
                type="button"
                className="btn btn-primary"
                disabled={selectedBoosterId === null}
                onClick={() => {
                  if (selectedBoosterId === null) return;
                  onPass(selectedBoosterId);
                  setPickerOpen(false);
                }}
              >
                이 부스터로 패스
              </button>
            </div>
          </section>
        </div>
      )}

      {conversionPromptOpen && (
        <div
          className="booster-preview-scrim"
          role="presentation"
          onMouseDown={() => setConversionPromptOpen(false)}
        >
          <section
            className="booster-preview-dialog"
            role="dialog"
            aria-modal="true"
            aria-label="패스 전 자원 환전 안내"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <h2>패스 전에 바꾸면 +{conversionGain.vp}점</h2>
            <p>
              남은 {conversionParts.join('·')}를 바꾸면 게임 종료 자원 점수가 {conversionGain.vp}점
              늘어납니다. 패스한 뒤에는 바꿀 수 없습니다.
            </p>
            <div className="booster-preview-actions">
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setConversionPromptOpen(false)}
              >
                돌아가서 바꾸기
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  setConversionPromptOpen(false);
                  onPass(null);
                }}
              >
                그대로 패스
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}
