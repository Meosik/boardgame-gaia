"""The policy network in plain torch: state trunk, candidate scoring head, value head.

gaia_rl.module.CandidateModule (ray) and tools/bc_train.py (torch only) create the same layers under the same
parameter names here, so a state_dict saved by one loads into the other.

encoding 3: a candidate row is one linear input (FeatureEncoder).
encoding 4: a candidate row is FeatureEncoderV4's field ids | board columns | outcome columns, read as measured in
cycles 115-117 (`expand+o`): one embedding per (action field, value) summed over the 34 fields, the board columns
(sum of 2**role per cell) opened into three 0/1 planes (single-coordinate roles, federation hexes, satellites)
through one linear layer, the outcome columns through one linear layer; tanh of the sum of the three.
Differences from the measured network: the state trunk reads the whole state vector (the scratch scripts dropped the
columns that were zero in the training fold, which changes the initial weight scale of that layer), and every field
has the whole vocabulary (the scripts counted the values present in the 114 samples).
"""
import torch
from torch import nn

from .encoding import ACTION_FIELDS, BOARD_CAPACITY, COORD_ROLES, FIELD_VOCABULARY, OUTCOME_SIZE

FIELDS = len(ACTION_FIELDS)
V4_CANDIDATE_SIZE = FIELDS + BOARD_CAPACITY + OUTCOME_SIZE
HEXES = 2 ** COORD_ROLES.index('hexes')                 # roles before it name a single coordinate
SATELLITES = 2 ** COORD_ROLES.index('satellite_hexes')
assert SATELLITES == 2 * HEXES and COORD_ROLES[-1] == 'satellite_hexes'


def build(net, observation_size, candidate_size, width, encoding=3):
    """Creates the layers on `net` (an nn.Module). The creation order is the state_dict order."""
    if encoding not in (3, 4):
        raise ValueError(f'unknown encoding {encoding}')
    if encoding == 4 and candidate_size != V4_CANDIDATE_SIZE:
        raise ValueError(f'encoding 4 candidate rows have {V4_CANDIDATE_SIZE} columns, not {candidate_size}')
    net.candidate_encoding = encoding
    net.state_encoder = nn.Sequential(nn.Linear(observation_size, width), nn.Tanh())
    if encoding == 3:
        net.action_encoder = nn.Sequential(nn.Linear(candidate_size, width), nn.Tanh())
    else:
        net.field_embedding = nn.EmbeddingBag(FIELDS * FIELD_VOCABULARY, width, mode='sum')
        net.board_encoder = nn.Linear(3 * BOARD_CAPACITY, width)
        net.outcome_encoder = nn.Linear(OUTCOME_SIZE, width)
    net.policy_head = nn.Sequential(nn.Linear(width * 2, width), nn.Tanh(), nn.Linear(width, 1))
    net.value_head = nn.Linear(width, 1)


def encode_candidates(net, rows):
    """Encoding 4 candidate rows [N, V4_CANDIDATE_SIZE] -> [N, width]."""
    ids = rows[:, :FIELDS].long() + torch.arange(FIELDS, device=rows.device) * FIELD_VOCABULARY
    cells = rows[:, FIELDS:FIELDS + BOARD_CAPACITY]
    planes = torch.cat((torch.remainder(cells, HEXES) > 0,
                        torch.remainder(torch.div(cells, HEXES, rounding_mode='floor'), 2) > 0,
                        cells >= SATELLITES), dim=-1).to(rows.dtype)
    outcome = rows[:, FIELDS + BOARD_CAPACITY:]
    return torch.tanh(net.field_embedding(ids) + net.board_encoder(planes) + net.outcome_encoder(outcome))


def score(net, observation, candidates, mask):
    """(candidate logits [..., K] with masked candidates at the dtype minimum, state embedding [..., width])."""
    state = net.state_encoder(observation.float())
    mask = mask.bool()
    low = torch.finfo(state.dtype).min
    if net.candidate_encoding == 3:
        encoded = net.action_encoder(candidates.float())
        expanded = state.unsqueeze(-2).expand(*encoded.shape)
        logits = net.policy_head(torch.cat((expanded, encoded), dim=-1)).squeeze(-1)
        return logits.masked_fill(~mask, low), state
    # Only the legal candidates are encoded: a padded list (capacity 2048) would cost 34 lookups per empty slot.
    encoded = encode_candidates(net, candidates[mask].float())
    expanded = state.unsqueeze(-2).expand(*mask.shape, state.shape[-1])[mask]
    scores = net.policy_head(torch.cat((expanded, encoded), dim=-1)).squeeze(-1)
    return torch.full(mask.shape, low, dtype=scores.dtype, device=scores.device).masked_scatter(mask, scores), state
