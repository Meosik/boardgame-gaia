import { standardTechTileImageSrc, advancedTechTileImageSrc } from '../../assets/techTileImages';
import type { GameState } from '../../types/game';
import { candidateLabel } from './protocol';
import { TRACK_NAMES, type TechnologySelection, type TechVariant } from './technology';

export function TechnologyPicker({ variants, selection, onChange, state, disabled }: {
  variants: TechVariant[]; selection: TechnologySelection; onChange: (value: TechnologySelection) => void;
  state: GameState; disabled: boolean;
}) {
  const tiles = [...new Map(variants.map(v => [v.tileKey, v])).values()];
  const tile = tiles.find(v => v.tileKey === selection.tileKey);
  const matching = variants.filter(v => v.tileKey === selection.tileKey);
  const tracks = [...new Set(matching.map(v => v.track))];
  const details = matching.filter(v => v.fixedTrack || v.track === selection.track);
  const image = tile?.tileId == null ? undefined : tile.advanced
    ? advancedTechTileImageSrc(tile.tileId) : standardTechTileImageSrc(tile.tileId);
  return <fieldset className="coach-technology"><legend>기술은 직접 선택해야 합니다</legend>
    <label>받을 기술<select aria-label="받을 기술" disabled={disabled} value={selection.tileKey}
      onChange={e => onChange({ tileKey: e.target.value, track: '', detail: null })}>
      <option value="" disabled>기술을 선택하세요 — AI 추천 자동 확정 없음</option>
      {tiles.map(v => <option key={v.tileKey} value={v.tileKey}>{v.tileLabel}
        {v.fixedTrack ? ` → ${TRACK_NAMES[v.track]}${v.track === 'none' ? '' : ' (고정)'}` : ' → 연구 트랙 직접 선택'}</option>)}
    </select></label>
    {image && <img className="coach-tech-image" src={image} alt={tile!.tileLabel} />}
    {tile && (tile.fixedTrack ? <p className="coach-track-result"><strong>
      {tile.track === 'none' ? '기술·연구 보너스를 받지 않습니다.' : `연결 트랙: ${TRACK_NAMES[tile.track]} (고정)`}
    </strong>{tile.track !== 'none' && <><br />다른 트랙을 원하면 다른 기술을 선택하세요. 상승 가능 여부는 엔진 규칙을 따릅니다.</>}</p>
      : <label>올릴 연구 트랙<select aria-label="올릴 연구 트랙" value={selection.track} disabled={disabled}
        onChange={e => onChange({ ...selection, track: e.target.value, detail: null })}>
        <option value="" disabled>트랙을 직접 선택하세요</option>
        {tracks.map(track => <option key={track} value={track}>{TRACK_NAMES[track] ?? track}</option>)}
      </select></label>)}
    {details.length > 1 && <label>추가 선택 · 광산 위치 등<select aria-label="기술 추가 선택" value={selection.detail ?? ''}
      disabled={disabled} onChange={e => onChange({ ...selection, detail: Number(e.target.value) })}>
      <option value="" disabled>정확한 후속 대상을 선택하세요</option>
      {details.map(v => <option key={v.index} value={v.index}>{candidateLabel(v.candidate, state)}</option>)}
    </select></label>}
  </fieldset>;
}
