import unittest
import numpy as np
import torch
from gymnasium import spaces
from ray.rllib.core.columns import Columns
from gaia_rl.module import CandidateModule


class ModuleTests(unittest.TestCase):
    def test_shared_scoring_mask_and_finite_gradient(self):
        torch.manual_seed(5)
        obs_space=spaces.Dict({'observation':spaces.Box(-1,1,(8,),np.float32),
                              'candidates':spaces.Box(-1,1,(3,4),np.float32),
                              'action_mask':spaces.MultiBinary(3)})
        module=CandidateModule(observation_space=obs_space,action_space=spaces.Discrete(3),
                               model_config={'width':8})
        observation={'observation':torch.randn(2,8),'candidates':torch.randn(2,3,4),
                     'action_mask':torch.tensor([[1,1,0],[1,1,0]])}
        batch={Columns.OBS:observation}
        logits=module.forward_train(batch)[Columns.ACTION_DIST_INPUTS]
        self.assertTrue(torch.all(torch.softmax(logits,-1)[:,2]==0))
        loss=-torch.log_softmax(logits,-1)[:,0].mean()+module.compute_values(batch).square().mean()
        loss.backward()
        self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in module.parameters()))
        swapped={**observation,'candidates':observation['candidates'][:,[1,0,2]]}
        other=module.forward_inference({Columns.OBS:swapped})[Columns.ACTION_DIST_INPUTS]
        torch.testing.assert_close(logits[:,[1,0,2]],other)


if __name__=='__main__':
    unittest.main()
