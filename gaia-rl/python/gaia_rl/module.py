"""Shared state trunk, candidate scoring head, and scalar PPO value head."""
import torch
from torch import nn
from ray.rllib.core.columns import Columns
from ray.rllib.core.rl_module.torch.torch_rl_module import TorchRLModule
from ray.rllib.core.rl_module.apis.value_function_api import ValueFunctionAPI


class CandidateModule(TorchRLModule, ValueFunctionAPI):
    def setup(self):
        width = self.model_config.get('width',64)
        self.state_encoder = nn.Sequential(
            nn.Linear(self.observation_space['observation'].shape[0],width), nn.Tanh())
        self.action_encoder = nn.Sequential(
            nn.Linear(self.observation_space['candidates'].shape[-1],width), nn.Tanh())
        self.policy_head = nn.Sequential(nn.Linear(width*2,width), nn.Tanh(), nn.Linear(width,1))
        self.value_head = nn.Linear(width,1)

    def _forward(self,batch,**kwargs):
        obs = batch[Columns.OBS]
        state = self.state_encoder(obs['observation'].float())
        candidates = self.action_encoder(obs['candidates'].float())
        expanded = state.unsqueeze(-2).expand(*candidates.shape)
        logits = self.policy_head(torch.cat((expanded,candidates),dim=-1)).squeeze(-1)
        logits = logits.masked_fill(~obs['action_mask'].bool(), torch.finfo(logits.dtype).min)
        return {Columns.ACTION_DIST_INPUTS:logits}

    def _forward_train(self,batch,**kwargs):
        return self._forward(batch,**kwargs)

    def compute_values(self,batch,embeddings=None):
        return self.value_head(self.state_encoder(batch[Columns.OBS]['observation'].float())).squeeze(-1)
