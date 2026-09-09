import type { CSSProperties, SVGProps } from 'react';
import iconSheet from '../assets/icons/game-piece-icons.png';

export type GamePieceIconKind =
  | 'knowledge'
  | 'credits'
  | 'power'
  | 'qic'
  | 'ore'
  | 'vp'
  | 'brainstone'
  | 'ivits-station'
  | 'action-used';

interface Crop {
  x: number;
  y: number;
  width: number;
  height: number;
}

const ICON_SHEET_WIDTH = 2170;
const ICON_SHEET_HEIGHT = 725;

const ICON_CROPS: Record<GamePieceIconKind, Crop> = {
  knowledge: { x: 29, y: 193, width: 186, height: 180 },
  credits: { x: 233, y: 189, width: 181, height: 183 },
  power: { x: 428, y: 188, width: 183, height: 185 },
  qic: { x: 628, y: 179, width: 168, height: 211 },
  ore: { x: 814, y: 177, width: 193, height: 196 },
  vp: { x: 1028, y: 158, width: 230, height: 236 },
  brainstone: { x: 1273, y: 163, width: 189, height: 227 },
  'ivits-station': { x: 1473, y: 143, width: 307, height: 331 },
  'action-used': { x: 1789, y: 129, width: 363, height: 364 },
};

interface Props extends Omit<SVGProps<SVGSVGElement>, 'viewBox'> {
  kind: GamePieceIconKind;
  decorative?: boolean;
  label?: string;
  title?: string;
}

export function GamePieceIcon({
  kind,
  decorative = true,
  label,
  title,
  className,
  style,
  ...svgProps
}: Props) {
  const crop = ICON_CROPS[kind];
  const accessibilityProps = decorative
    ? { 'aria-hidden': true as const }
    : { role: 'img' as const, 'aria-label': label ?? kind };

  return (
    <svg
      {...svgProps}
      {...accessibilityProps}
      className={`game-piece-icon game-piece-icon--${kind}${className ? ` ${className}` : ''}`}
      viewBox={`${crop.x} ${crop.y} ${crop.width} ${crop.height}`}
      preserveAspectRatio="xMidYMid meet"
      style={{ aspectRatio: `${crop.width} / ${crop.height}`, ...style } as CSSProperties}
    >
      {title && <title>{title}</title>}
      <image href={iconSheet} x="0" y="0" width={ICON_SHEET_WIDTH} height={ICON_SHEET_HEIGHT} />
    </svg>
  );
}
