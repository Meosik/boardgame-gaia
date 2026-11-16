"""Behaviour cloning: bc_dataset shards -> a policy checkpoint (inference.pt + metadata.json) that
gaia_rl.evaluation.OfflinePolicy loads (HANDOFF E128 step 2, user 2026-11-12 "모델 업그레이드 진행").

  bc_train.py SHARDS_DIR --out CHECKPOINT_DIR [--epochs 4] [--batch 256] [--lr 0.0003] [--width W]
              [--val-every 5 | --val-games 3,8,...] [--val-shards 1] [--seed 0] [--value-weight 0]

SHARDS_DIR holds shard-*.npz from `bc_dataset.py export` (observation, ragged candidate features cand +
cand_offsets, chosen index, value, and from 2026-11-16 the game of every sample). The network is
gaia_rl.network's (state trunk, candidate scoring head, value head), the layers gaia_rl.module.CandidateModule
(ray) builds under the same parameter names, so training needs torch only and the saved state_dict loads into
CandidateModule for OfflinePolicy and as the PPO starting point.
Encoding: read from the shards' row sizes. Encoding 3 (FeatureEncoder) keeps width 64, the width of the earlier
PPO runs (Codex debate 2026-11-14). Encoding 4 (FeatureEncoderV4; `bc_dataset.py export --encoding 4`) defaults
to width 256 (cycle 117). OfflinePolicy (and with it tools/policy_teacher.py) reads encoding_version and
model.width from the checkpoint's metadata, so it plays both; PPO starts from a checkpoint with
`python -m gaia_rl.training --encoding 4 --init <checkpoint>` (same encoding, width and capacity).
Loss: cross-entropy of the chosen candidate over the legal candidates (padded per batch to the largest list, not
to the encoder capacity 2048). --value-weight > 0 adds MSE on value/100 for samples of finished 6-round games
(value is NaN otherwise); 0 leaves the value head at its initial weights.
Defaults: 4 epochs as in the earlier strategy pilot, lr 0.0003 as in gaia_rl.training (cycles 115-117 measured
9 epochs at lr 0.001).
Validation: shards with game ids hold out whole games — every --val-every-th game in id order (0: none), or the
games listed in --val-games. Older
shards without game ids fall back to the last --val-shards shards; those are cut by sample count, so a game can
straddle the boundary and that validation accuracy is optimistic. With validation the saved weights are those of
the epoch with the lowest validation loss (cycle 117: width 256 was lowest at epoch 5 of 9), so the validation
figures of that epoch are picked on the same games and read slightly optimistic; without, the last epoch.
'chance' is the mean of 1/candidates over the validation samples (candidate order is the engine's, not a ranking).
The shard reader and batcher need numpy only; training needs torch (pyproject extra `train`).
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np

_HEADS = ('policy_head.0.weight', 'policy_head.0.bias', 'policy_head.2.weight', 'policy_head.2.bias',
          'value_head.weight', 'value_head.bias')
PARAMETERS = {     # by encoding: the state_dict of gaia_rl.network.build (= CandidateModule.setup)
    3: ('state_encoder.0.weight', 'state_encoder.0.bias', 'action_encoder.0.weight', 'action_encoder.0.bias') + _HEADS,
    4: ('state_encoder.0.weight', 'state_encoder.0.bias', 'field_embedding.weight', 'board_encoder.weight',
        'board_encoder.bias', 'outcome_encoder.weight', 'outcome_encoder.bias') + _HEADS,
}
# Encoding 3 stays at the width of the earlier PPO runs and checkpoints (64).
WIDTHS = {3: 64, 4: 256}


def shard_paths(directory):
    paths = sorted(Path(directory).glob('shard-*.npz'))
    if not paths:
        raise FileNotFoundError(f'no shard-*.npz in {directory}')
    return paths


def load_shard(path):
    with np.load(path) as data:
        shard = {key: data[key] for key in ('observation', 'cand', 'cand_offsets', 'chosen', 'value')}
        if 'game' in data.files:
            shard['game'] = data['game']
    counts = np.diff(shard['cand_offsets'])
    if len(counts) != len(shard['chosen']) or (counts < 1).any() or (shard['chosen'] >= counts).any():
        raise ValueError(f'{path}: chosen index outside its candidate list')
    return shard


def held_out_games(paths, every):
    """Game ids held out for validation: every `every`-th game in id order. None: a shard carries no game ids."""
    games = set()
    for path in paths:
        with np.load(path) as data:
            if 'game' not in data.files:
                return None
            games.update(data['game'].tolist())
    return set(sorted(games)[every-1::every]) if every else set()


def batches(shard, size, rng=None, rows=None):
    """Padded numpy batches of one shard: observation [B, O], candidates [B, K, F] (K = largest list in the batch,
    zero padded), mask [B, K], chosen [B], value [B]. rng shuffles the sample order; rows keeps only these samples."""
    offsets, total = shard['cand_offsets'], len(shard['chosen'])
    if rows is None:
        order = np.arange(total) if rng is None else rng.permutation(total)
    else:
        order = np.asarray(rows) if rng is None else rng.permutation(np.asarray(rows))
        total = len(order)
    for start in range(0, total, size):
        rows = order[start:start+size]
        counts = offsets[rows+1]-offsets[rows]
        candidates = np.zeros((len(rows), int(counts.max()), shard['cand'].shape[1]), dtype=np.float32)
        mask = np.zeros(candidates.shape[:2], dtype=bool)
        for i, (row, count) in enumerate(zip(rows, counts)):
            candidates[i, :count] = shard['cand'][offsets[row]:offsets[row]+count]
            mask[i, :count] = True
        yield {'observation': shard['observation'][rows].astype(np.float32), 'candidates': candidates, 'mask': mask,
               'chosen': shard['chosen'][rows].astype(np.int64), 'value': shard['value'][rows].astype(np.float32)}


def build_model(observation_size, candidate_size, width=WIDTHS[3], encoding=3):
    from torch import nn
    from gaia_rl import network

    class CandidateNet(nn.Module):
        def __init__(self):
            super().__init__()
            network.build(self, observation_size, candidate_size, width, encoding)

        def forward(self, observation, candidates, mask):
            logits, state = network.score(self, observation, candidates, mask)
            return logits, self.value_head(state).squeeze(-1)

    return CandidateNet()


def _run(model, shards, size, value_weight, optimizer=None, rng=None, select=None):
    """One pass over the shard files. Returns mean policy loss, top-1 accuracy, chance level, samples.
    select(shard) -> the sample rows of the shard to use (None: all)."""
    import torch
    loss_sum = correct = chance = samples = 0
    for path in shards:
        shard = load_shard(path)
        for batch in batches(shard, size, rng, None if select is None else select(shard)):
            tensors = {key: torch.from_numpy(value) for key, value in batch.items()}
            with torch.set_grad_enabled(optimizer is not None):
                logits, value = model(tensors['observation'], tensors['candidates'], tensors['mask'])
                policy_loss = torch.nn.functional.cross_entropy(logits, tensors['chosen'], reduction='sum')
                loss = policy_loss/len(tensors['chosen'])
                known = ~torch.isnan(tensors['value'])
                if value_weight and known.any():
                    loss = loss+value_weight*torch.nn.functional.mse_loss(value[known], tensors['value'][known]/100)
            if optimizer is not None:
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
            loss_sum += float(policy_loss.detach())
            correct += int((logits.argmax(dim=-1) == tensors['chosen']).sum())
            chance += float((1/batch['mask'].sum(axis=1)).sum())
            samples += len(batch['chosen'])
    if not samples:
        raise ValueError('no samples in this pass')
    return {'loss': loss_sum/samples, 'accuracy': correct/samples, 'chance': chance/samples, 'samples': samples}


def train(shards_dir, out, epochs=4, batch=256, lr=0.0003, val_shards=1, seed=0, value_weight=0.0, width=None,
          val_every=5, val_games=None):
    import torch
    from gaia_rl.encoding import FeatureEncoder, FeatureEncoderV4
    from gaia_rl.versions import model_build_id, runtime_versions
    out = Path(out)
    if (out/'metadata.json').exists():
        raise FileExistsError(f'{out} already holds a checkpoint')
    paths = shard_paths(shards_dir)
    first = load_shard(paths[0])
    sizes = (first['observation'].shape[1], first['cand'].shape[1])
    encoders = {3: FeatureEncoder(), 4: FeatureEncoderV4()}
    encoding = next((version for version, encoder in encoders.items()
                     if sizes == (encoder.state_size, encoder.candidate_size)), None)
    if encoding is None:
        raise ValueError(f'shards were exported with another encoding: {sizes}')
    width = width or WIDTHS[encoding]
    if encoding == 3 and width != WIDTHS[3]:
        raise ValueError('encoding 3 checkpoints are loaded at width 64 (OfflinePolicy, PPO)')
    held = held_out_games(paths, val_every)
    if val_games is not None:
        if held is None:
            raise ValueError('--val-games needs shards with game ids')
        held = set(val_games)
    if held is None:      # shards without game ids: the last shards are the validation set
        if not 0 <= val_shards < len(paths):
            raise ValueError('--val-shards must leave at least one training shard')
        training, validation = paths[:len(paths)-val_shards], paths[len(paths)-val_shards:]
        train_rows = val_rows = None
    else:                 # a pass without samples (every game held out, or none of --val-games present) is an error
        training, validation = paths, (paths if held else [])
        members = np.array(sorted(held))
        train_rows = lambda shard: np.flatnonzero(~np.isin(shard['game'], members))
        val_rows = lambda shard: np.flatnonzero(np.isin(shard['game'], members))
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = build_model(*sizes, width, encoding)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    history, best = [], None
    for epoch in range(1, epochs+1):
        model.train()
        row = {'epoch': epoch, 'train': _run(model, training, batch, value_weight, optimizer, rng, train_rows)}
        if validation:
            model.eval()
            row['validation'] = _run(model, validation, batch, value_weight, select=val_rows)
            if best is None or row['validation']['loss'] < best[0]:
                best = (row['validation']['loss'], epoch,
                        {key: value.detach().clone() for key, value in model.state_dict().items()})
        history.append(row)
        print(json.dumps(row), flush=True)
    if not all(math.isfinite(row['train']['loss']) for row in history):
        raise RuntimeError('non-finite training loss; no checkpoint written')
    out.mkdir(parents=True, exist_ok=True)
    saved_epoch, state = (best[1], best[2]) if best else (epochs, model.state_dict())
    assert tuple(state) == PARAMETERS[encoding], tuple(state)
    torch.save(state, out/'inference.pt')
    # versions = the full record of this run; model_build_id = what OfflinePolicy checks before loading the weights
    # (gaia_rl.versions.require_loadable_checkpoint: vocabulary, encoding, network, module + engine + dependencies).
    metadata = {'versions': runtime_versions(), 'model_build_id': model_build_id(), 'encoding_version': encoding,
                'settings': {'capacity': encoders[encoding].candidate_capacity},
                'model': {'width': width, 'encoding': encoding}, 'iteration': 0,
                'behaviour_cloning': {'shards': str(shards_dir), 'training_shards': len(training),
                                      'validation_shards': len(validation),
                                      'validation_games': None if held is None else sorted(held),
                                      'epochs': epochs, 'saved_epoch': saved_epoch, 'batch': batch,
                                      'lr': lr, 'width': width, 'seed': seed, 'value_weight': value_weight,
                                      'history': history}}
    # Metadata is the completion marker, as in gaia_rl.training.save_run.
    (out/'metadata.json').write_text(json.dumps(metadata, indent=2))
    return history


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('shards')
    parser.add_argument('--out', required=True)
    parser.add_argument('--epochs', type=int, default=4)
    parser.add_argument('--batch', type=int, default=256)
    parser.add_argument('--lr', type=float, default=0.0003)
    parser.add_argument('--val-shards', type=int, default=1)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--value-weight', type=float, default=0.0)
    parser.add_argument('--width', type=int, help='default 64 for encoding 3 (fixed), 256 for encoding 4')
    parser.add_argument('--val-every', type=int, default=5,
                        help='shards with game ids: hold out every N-th game (0: no validation)')
    parser.add_argument('--val-games', help='comma-separated game ids to hold out instead of --val-every')
    args = parser.parse_args()
    train(args.shards, args.out, args.epochs, args.batch, args.lr, args.val_shards, args.seed,
          args.value_weight, args.width, args.val_every,
          None if args.val_games is None else [int(game) for game in args.val_games.split(',')])


if __name__ == '__main__':
    main()
