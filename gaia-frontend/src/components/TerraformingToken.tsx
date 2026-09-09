import { roundScoringTileImageSrc } from '../assets/roundScoringTileImages';

interface Props {
  steps: number;
}

export function TerraformingToken({ steps }: Props) {
  const label = `테라포밍 ${steps}단계`;
  return (
    <span className="interaction-terraforming-token" aria-label={label} title={label}>
      <svg viewBox="340 390 500 500" aria-hidden="true">
        <image
          href={roundScoringTileImageSrc(2)}
          width="1174"
          height="1340"
        />
      </svg>
      <strong>{steps}</strong>
    </span>
  );
}
