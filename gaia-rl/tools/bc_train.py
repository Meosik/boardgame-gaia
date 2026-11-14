"""Behaviour cloning: bc_dataset shards -> a policy checkpoint (inference.pt + metadata.json) that
gaia_rl.evaluation.OfflinePolicy loads (HANDOFF E128 step 2, user 2026-11-12 "모델 업그레이드 진행").

  bc_train.py SHARDS_DIR --out CHECKPOINT_DIR [--epochs 4] [--batch 256] [--lr 0.0003] [--val-shards 1]
              [--seed 0] [--value-weight 0]

SHARDS_DIR holds shard-*.npz from `bc_dataset.py export` (observation, ragged candidate features cand +
cand_offsets, chosen index, value). The network is gaia_rl.module.CandidateModule's (state trunk, candidate
scoring head, value head) written in plain torch with the same parameter names, so training needs torch only and
the saved state_dict loads into CandidateModule (ray) for OfflinePolicy and as the PPO starting point.
Loss: cross-entropy of the chosen candidate over the legal candidates (padded per batch to the largest list, not
to the encoder capacity 2048). --value-weight > 0 adds MSE on value/100 for samples of finished 6-round games
(value is NaN otherwise); 0 leaves the value head at its initial weights.
Defaults: 4 epochs as in the earlier strategy pilot, lr 0.0003 as in gaia_rl.training. The width is fixed at 64: OfflinePolicy and PPO build CandidateModule with width 64, so another width could not be loaded (Codex debate 2026-11-14).
Validation = the last --val-shards shards. Shards are cut by sample count, so a game can straddle the boundary:
validation accuracy is optimistic by that leak until the export carries a game id. 'chance' is the mean of
1/candidates over the validation samples (candidate order is the engine's, not a ranking).
The shard reader and batcher need numpy only; training needs torch (pyproject extra `train`).
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np

PARAMETERS = ('state_encoder.0.weight', 'state_encoder.0.bias', 'action_encoder.0.weight', 'action_encoder.0.bias',
              'policy_head.0.weight', 'policy_head.0.bias', 'policy_head.2.weight', 'policy_head.2.bias',
              'value_head.weight', 'value_head.bias')     # CandidateModule.setup, gaia_rl/module.py:10-17


WIDTH = 64   # fixed: OfflinePolicy (gaia_rl/evaluation.py:29) and PPO (gaia_rl/training.py:42) build CandidateModule with width 64


def shard_paths(directory):
    paths = sorted(Path(directory).glob('shard-*.npz'))
    if not paths:
        raise FileNotFoundError(f'no shard-*.npz in {directory}')
    return paths


def load_shard(path):
    with np.load(path) as data:
        shard = {key: data[key] for key in ('observation', 'cand', 'cand_offsets', 'chosen', 'value')}
    counts = np.diff(shard['cand_offsets'])
    if len(counts) != len(shard['chosen']) or (counts < 1).any() or (shard['chosen'] >= counts).any():
        raise ValueError(f'{path}: chosen index outside its candidate list')
    return shard


def batches(shard, size, rng=None):
    """Padded numpy batches of one shard: observation [B, O], candidates [B, K, F] (K = largest list in the batch,
    zero padded), mask [B, K], chosen [B], value [B]. rng shuffles the sample order."""
    offsets, total = shard['cand_offsets'], len(shard['chosen'])
    order = np.arange(total) if rng is None else rng.permutation(total)
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


def build_model(observation_size, candidate_size, width=WIDTH):
    import torch
    from torch import nn

    class CandidateNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.state_encoder = nn.Sequential(nn.Linear(observation_size, width), nn.Tanh())
            self.action_encoder = nn.Sequential(nn.Linear(candidate_size, width), nn.Tanh())
            self.policy_head = nn.Sequential(nn.Linear(width*2, width), nn.Tanh(), nn.Linear(width, 1))
            self.value_head = nn.Linear(width, 1)

        def forward(self, observation, candidates, mask):
            state = self.state_encoder(observation)
            encoded = self.action_encoder(candidates)
            expanded = state.unsqueeze(-2).expand(*encoded.shape)
            logits = self.policy_head(torch.cat((expanded, encoded), dim=-1)).squeeze(-1)
            return logits.masked_fill(~mask, torch.finfo(logits.dtype).min), self.value_head(state).squeeze(-1)

    return CandidateNet()


def _run(model, shards, size, value_weight, optimizer=None, rng=None):
    """One pass over the shard files. Returns mean policy loss, top-1 accuracy, chance level, samples."""
    import torch
    loss_sum = correct = chance = samples = 0
    for path in shards:
        for batch in batches(load_shard(path), size, rng):
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
            loss_sum += float(policy_loss)
            correct += int((logits.argmax(dim=-1) == tensors['chosen']).sum())
            chance += float((1/batch['mask'].sum(axis=1)).sum())
            samples += len(batch['chosen'])
    return {'loss': loss_sum/samples, 'accuracy': correct/samples, 'chance': chance/samples, 'samples': samples}


def train(shards_dir, out, epochs=4, batch=256, lr=0.0003, val_shards=1, seed=0, value_weight=0.0):
    import torch
    from gaia_rl.encoding import ENCODING_VERSION, FeatureEncoder
    from gaia_rl.versions import runtime_versions
    out = Path(out)
    if (out/'metadata.json').exists():
        raise FileExistsError(f'{out} already holds a checkpoint')
    paths = shard_paths(shards_dir)
    if not 0 <= val_shards < len(paths):
        raise ValueError('--val-shards must leave at least one training shard')
    training, validation = paths[:len(paths)-val_shards], paths[len(paths)-val_shards:]
    encoder = FeatureEncoder()
    spaces = encoder.observation_space.spaces
    first = load_shard(paths[0])
    sizes = (first['observation'].shape[1], first['cand'].shape[1])
    if sizes != (spaces['observation'].shape[0], spaces['candidates'].shape[-1]):
        raise ValueError(f'shards were exported with another encoding: {sizes}')
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = build_model(*sizes)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    history = []
    for epoch in range(1, epochs+1):
        model.train()
        row = {'epoch': epoch, 'train': _run(model, training, batch, value_weight, optimizer, rng)}
        if validation:
            model.eval()
            row['validation'] = _run(model, validation, batch, value_weight)
        history.append(row)
        print(json.dumps(row), flush=True)
    if not all(math.isfinite(row['train']['loss']) for row in history):
        raise RuntimeError('non-finite training loss; no checkpoint written')
    out.mkdir(parents=True, exist_ok=True)
    state = model.state_dict()
    assert tuple(state) == PARAMETERS, tuple(state)
    torch.save(state, out/'inference.pt')
    metadata = {'versions': runtime_versions(), 'encoding_version': ENCODING_VERSION,
                'settings': {'capacity': encoder.candidate_capacity}, 'iteration': 0,
                'behaviour_cloning': {'shards': str(shards_dir), 'training_shards': len(training),
                                      'validation_shards': len(validation), 'epochs': epochs, 'batch': batch,
                                      'lr': lr, 'width': WIDTH, 'seed': seed, 'value_weight': value_weight,
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
    args = parser.parse_args()
    train(args.shards, args.out, args.epochs, args.batch, args.lr, args.val_shards, args.seed,
          args.value_weight)


if __name__ == '__main__':
    main()
