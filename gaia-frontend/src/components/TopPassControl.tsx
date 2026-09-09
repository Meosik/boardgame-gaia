import { useEffect, useState } from 'react';
import { roundBoosterImageSrc } from '../assets/roundBoosterImages';
import type { PlayerState } from '../types/game';

interface TopPassControlProps {
  player: PlayerState;
  round: number;
  availableBoosters: number[];
  isMyTurn: boolean;
  onPass: (boosterId: number | null) => void;
}

export function TopPassControl({
  player,
  round,
  availableBoosters,
  isMyTurn,
  onPass,
}: TopPassControlProps) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const [selectedBoosterId, setSelectedBoosterId] = useState<number | null>(null);
  const controlsDisabled = !isMyTurn || player.passed;
  const requiresBoosterChoice = round < 6 && player.booster != null;
  const selectedImageSrc = selectedBoosterId === null ? null : roundBoosterImageSrc(selectedBoosterId);

  useEffect(() => {
    setPickerOpen(false);
    setSelectedBoosterId(null);
  }, [round, player.booster]);

  useEffect(() => {
    if (selectedBoosterId !== null && !availableBoosters.includes(selectedBoosterId)) {
      setSelectedBoosterId(availableBoosters[0] ?? null);
    }
  }, [availableBoosters, selectedBoosterId]);

  const handlePassClick = () => {
    if (!requiresBoosterChoice) {
      onPass(null);
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
    </>
  );
}
