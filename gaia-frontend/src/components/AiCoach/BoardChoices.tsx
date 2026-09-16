import type { FactionId, GameState, StructureType } from '../../types/game';
import { FACTION_STRUCTURE_COLOR, structureAssetName, structureImageSrc } from '../../assets/structureImages';
import { standardTechTileImageSrc } from '../../assets/techTileImages';
import { roundBoosterImageSrc } from '../../assets/roundBoosterImages';
import { GamePieceIcon } from '../GamePieceIcon';
import { candidateLabel, type Candidate } from './protocol';

export function BoardChoices({ choices, state, faction, onChoose, recommended }: {
  choices: { index: number; candidate: Candidate }[]; state: GameState;
  faction: FactionId | null; onChoose: (index: number) => void;
  recommended?: number;
}) {
  return <div className="coach-board-choices" aria-label="보드에서 고른 대상의 합법 행동">
    {choices.map(({ index, candidate }) => {
      const a = candidate.action;
      const structure = a.to ? structureAssetName(a.to as StructureType)
        : /GaiaFormation/.test(a.type) ? 'gaiaformer'
          : /Build|PlaceStartingStructure/.test(a.type) ? 'mine' : null;
      const tile = a.tile as { pool?: string; tile?: number } | undefined;
      const image = structure && faction ? structureImageSrc(FACTION_STRUCTURE_COLOR[faction], structure)
        : typeof a.booster_id === 'number' ? roundBoosterImageSrc(a.booster_id)
          : tile?.pool === 'Standard' && tile.tile ? standardTechTileImageSrc(tile.tile) : undefined;
      return <button type="button" key={index} data-coach-recommended={index === recommended || undefined} onClick={() => onChoose(index)}>
        {image ? <img src={image} alt="" /> : <GamePieceIcon kind={a.type.includes('Research') ? 'knowledge' : 'power'} />}
        <span>{index === recommended ? '★ AI 추천 · ' : ''}{candidateLabel(candidate, state)}</span>
      </button>;
    })}
  </div>;
}
