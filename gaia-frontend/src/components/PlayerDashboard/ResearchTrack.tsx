import type { ResearchTracks } from '../../types/game';

const TRACKS = [
  { key: 'terraforming' as const, label: 'TF', color: '#8d6e63' },
  { key: 'navigation' as const, label: 'NAV', color: '#5c6bc0' },
  { key: 'ai' as const, label: 'AI', color: '#00897b' },
  { key: 'gaia' as const, label: 'GP', color: '#43a047' },
  { key: 'economy' as const, label: 'ECO', color: '#fb8c00' },
  { key: 'science' as const, label: 'SCI', color: '#e53935' },
];

interface Props {
  tracks: ResearchTracks;
}

export function ResearchTrack({ tracks }: Props) {
  return (
    <div className="research-track">
      {TRACKS.map(({ key, label, color }) => (
        <TrackRow
          key={key}
          label={label}
          level={tracks[key]}
          color={color}
        />
      ))}
    </div>
  );
}

function TrackRow({
  label,
  level,
  color,
}: {
  label: string;
  level: number;
  color: string;
}) {
  return (
    <div className="track-row">
      <span className="track-label" style={{ color }}>{label}</span>
      <div className="track-pips">
        {[0, 1, 2, 3, 4, 5].map((pip) => (
          <div
            key={pip}
            className={`track-pip ${pip <= level ? 'active' : ''}`}
            style={{ backgroundColor: pip <= level ? color : undefined }}
          />
        ))}
      </div>
      <span className="track-level">{level}</span>
    </div>
  );
}
