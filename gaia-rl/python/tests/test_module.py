import unittest
import numpy as np
import torch
from gymnasium import spaces
from ray.rllib.core.columns import Columns
from gaia_rl import network
from gaia_rl.encoding import BOARD_CAPACITY, FIELD_VOCABULARY
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

    def test_encoding_4_scores_only_legal_candidates(self):
        torch.manual_seed(7)
        size=network.V4_CANDIDATE_SIZE
        fields=network.FIELDS
        obs_space=spaces.Dict({'observation':spaces.Box(-1,1,(8,),np.float32),
                              'candidates':spaces.Box(-1e6,1e6,(4,size),np.float32),
                              'action_mask':spaces.MultiBinary(4)})
        module=CandidateModule(observation_space=obs_space,action_space=spaces.Discrete(4),
                               model_config={'width':8,'encoding':4})
        self.assertEqual(tuple(module.state_dict()),
                         ('state_encoder.0.weight','state_encoder.0.bias','field_embedding.weight',
                          'board_encoder.weight','board_encoder.bias','outcome_encoder.weight','outcome_encoder.bias',
                          'policy_head.0.weight','policy_head.0.bias','policy_head.2.weight','policy_head.2.bias',
                          'value_head.weight','value_head.bias'))
        candidates=torch.randn(2,4,size)
        candidates[:,:,:fields]=torch.randint(0,FIELD_VOCABULARY,(2,4,fields)).float()
        cells=torch.tensor([0,1,2,32,64,96],dtype=torch.float32)
        candidates[:,:,fields:fields+BOARD_CAPACITY]=cells[torch.randint(0,len(cells),(2,4,BOARD_CAPACITY))]
        mask=torch.tensor([[1,1,1,0],[1,1,0,0]])
        observation={'observation':torch.randn(2,8),'candidates':candidates,'action_mask':mask}
        batch={Columns.OBS:observation}
        logits=module.forward_train(batch)[Columns.ACTION_DIST_INPUTS]
        self.assertEqual(tuple(logits.shape),(2,4))
        low=torch.finfo(logits.dtype).min
        self.assertTrue(torch.all(logits[~mask.bool()]==low))
        self.assertTrue(torch.all(torch.softmax(logits,-1)[~mask.bool()]==0))
        loss=-torch.log_softmax(logits,-1)[:,0].mean()+module.compute_values(batch).square().mean()
        loss.backward()
        self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in module.parameters()))

        def run(rows):
            with torch.no_grad():
                return module.forward_inference({Columns.OBS:{**observation,'candidates':rows}})[Columns.ACTION_DIST_INPUTS]
        logits=run(candidates)
        torch.testing.assert_close(run(candidates[:,[1,0,2,3]]),logits[:,[1,0,2,3]])
        garbage=candidates.clone()
        garbage[0,3]=torch.randn(size)*1e3
        garbage[1,2:]=torch.randn(2,size)*1e3
        garbage[0,3,0]=1e6
        garbage[1,2,0]=1e6
        torch.testing.assert_close(run(garbage),logits)
        cell=fields+0
        planes=candidates.clone()
        planes[0,0,cell]=1
        a=run(planes)[0,0]
        planes[0,0,cell]=2
        torch.testing.assert_close(run(planes)[0,0],a)
        planes[0,0,cell]=32
        self.assertNotEqual(run(planes)[0,0].item(),a.item())

        with self.assertRaises(ValueError):
            CandidateModule(observation_space=spaces.Dict({'observation':spaces.Box(-1,1,(8,),np.float32),
                                                           'candidates':spaces.Box(-1e6,1e6,(4,10),np.float32),
                                                           'action_mask':spaces.MultiBinary(4)}),
                            action_space=spaces.Discrete(4),model_config={'width':8,'encoding':4})


if __name__=='__main__':
    unittest.main()
