"""Shared state trunk, candidate scoring head, and scalar PPO value head (layers: gaia_rl.network)."""
from ray.rllib.core.columns import Columns
from ray.rllib.core.rl_module.torch.torch_rl_module import TorchRLModule
from ray.rllib.core.rl_module.apis.value_function_api import ValueFunctionAPI

from . import network


class CandidateModule(TorchRLModule, ValueFunctionAPI):
    """model_config: width (default 64), encoding (default 3; 4 = FeatureEncoderV4 candidate rows)."""
    def setup(self):
        network.build(self, self.observation_space['observation'].shape[0],
                      self.observation_space['candidates'].shape[-1],
                      self.model_config.get('width',64), self.model_config.get('encoding',3))

    def _forward(self,batch,**kwargs):
        obs = batch[Columns.OBS]
        logits, _ = network.score(self, obs['observation'], obs['candidates'], obs['action_mask'])
        return {Columns.ACTION_DIST_INPUTS:logits}

    def _forward_train(self,batch,**kwargs):
        return self._forward(batch,**kwargs)

    def compute_values(self,batch,embeddings=None):
        return self.value_head(self.state_encoder(batch[Columns.OBS]['observation'].float())).squeeze(-1)
