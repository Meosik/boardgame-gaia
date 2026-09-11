import { useId } from 'react';
import { GamePieceIcon } from './GamePieceIcon';

// User-mapped original-pixel octagons; keep source dimensions independent of display size.
export const ACTION_CROPS = {
  'faction-Firaks-downgrade': { width: 2323, height: 1489, points: [[553,670],[513,729],[513,823],[556,893],[777,903],[820,839],[820,752],[785,687]] },
  'faction-Ivits-space-station': { width: 2323, height: 1489, points: [[556,676],[518,737],[499,821],[548,888],[769,898],[820,833],[818,752],[774,684]] },
  'exploration-Gleens-range': { width: 884, height: 1778, points: [[361,474],[288,550],[280,649],[367,726],[511,725],[602,651],[600,546],[517,467]] },
  'exploration-SpaceGiants-build-mine': { width: 916, height: 1717, points: [[375,455],[298,533],[289,636],[379,717],[520,717],[607,640],[612,531],[525,449]] },
  'faction-BalTaks-credit-academy': { width: 2323, height: 1489, points: [[1447,782],[1414,811],[1414,852],[1449,887],[1503,887],[1533,852],[1535,814],[1508,783]] },
  'faction-Geodens-credit-academy': { width: 2323, height: 1489, points: [[1447,782],[1414,811],[1414,852],[1449,887],[1503,887],[1533,852],[1535,814],[1508,783]] },
  'faction-Moweyds-power-ring': { width: 2323, height: 1489, points: [[564,664],[526,736],[521,846],[561,892],[784,889],[832,838],[835,744],[799,667]] },
  'faction-Bescods-research': { width: 2323, height: 1489, points: [[1911,224],[1868,270],[1865,337],[1900,391],[2096,393],[2126,348],[2126,291],[2090,229]] },
  'standard-10': { width: 712, height: 536, points: [[268,106],[177,193],[178,307],[262,394],[422,393],[509,306],[508,192],[420,106]] },
  'advanced-20': { width: 668, height: 528, points: [[191,52],[87,156],[91,289],[190,401],[378,398],[480,297],[482,156],[378,52]] },
  'advanced-21': { width: 668, height: 528, points: [[189,54],[87,159],[86,297],[185,397],[374,397],[473,291],[469,161],[371,56]] },
  'advanced-22': { width: 668, height: 528, points: [[195,55],[92,157],[89,296],[188,397],[374,398],[476,297],[479,160],[373,57]] },
  'booster-5': { width: 720, height: 2104, points: [[255,385],[136,503],[135,662],[249,768],[467,770],[589,662],[587,506],[461,380]] },
  'booster-8': { width: 720, height: 2104, points: [[255,381],[135,500],[134,649],[254,764],[463,765],[586,645],[589,495],[467,384]] },
} as const;

export type ActionCropId = keyof typeof ACTION_CROPS;

export function ActionCrop({ id, src, used = false }: { id: ActionCropId; src: string; used?: boolean }) {
  const clipId = useId();
  const crop = ACTION_CROPS[id];
  const x = Math.min(...crop.points.map(([x]) => x));
  const y = Math.min(...crop.points.map(([, y]) => y));
  const width = Math.max(...crop.points.map(([x]) => x)) - x;
  const height = Math.max(...crop.points.map(([, y]) => y)) - y;
  return (
    <div className="action-crop">
      <svg role="img" aria-label="액션 그림" viewBox={`${x} ${y} ${width} ${height}`}>
        <defs><clipPath id={clipId}><polygon points={crop.points.map((point) => point.join(',')).join(' ')} /></clipPath></defs>
        <image href={src} width={crop.width} height={crop.height} clipPath={`url(#${clipId})`} />
      </svg>
      {used && <GamePieceIcon kind="action-used" className="action-crop-closed" />}
    </div>
  );
}
