"""Explicit short end-to-end verification against one pinned native build (not a test discovery run)."""
import json
from pathlib import Path
import random
import resource
import time
import numpy as np
import torch
import ray
from gaia_rl.training import build_algorithm, save_run, restore_run, parameter_vector
from gaia_rl.evaluation import OfflinePolicy, evaluate
from gaia_rl.versions import require_current_sources, runtime_versions


def main():
    root=Path(__file__).resolve().parents[3]
    require_current_sources(root)
    destination=root/'gaia-rl/runs/integrated-pilot-v2'
    if destination.exists():
        raise ValueError('Pilot output exists; choose a fresh destination')
    destination.mkdir(parents=True)
    torch.set_num_threads(2);torch.manual_seed(8);np.random.seed(8);random.seed(8)
    settings={'seed':8,'capacity':2048,'batch_size':32,'device':'cpu'}
    ray.init(num_cpus=2,include_dashboard=False,object_store_memory=128*1024**2,log_to_driver=False)
    algorithm=None
    start=time.monotonic()
    try:
        algorithm=build_algorithm(8)
        before=parameter_vector(algorithm)
        result=algorithm.train()
        after=parameter_vector(algorithm)
        assert torch.isfinite(after).all() and not torch.equal(before,after)
        assert all(np.isfinite(result['learners']['shared'][k]) for k in ('total_loss','policy_loss','vf_loss'))
        save_run(algorithm,destination/'initial',settings,1)
        optimizer_before=algorithm.learner_group.get_state()['learner']['optimizer']
        algorithm.stop();algorithm=None
        algorithm=build_algorithm(8)
        assert restore_run(algorithm,destination/'initial',settings)==1
        torch.testing.assert_close(parameter_vector(algorithm),after,rtol=0,atol=0)
        def equal(a,b):
            if isinstance(a,dict):
                assert a.keys()==b.keys()
                for key in a: equal(a[key],b[key])
            elif isinstance(a,(list,tuple)):
                assert len(a)==len(b)
                for x,y in zip(a,b):equal(x,y)
            elif isinstance(a,(np.ndarray,torch.Tensor)):
                np.testing.assert_array_equal(np.asarray(a),np.asarray(b))
            else: assert a==b
        equal(optimizer_before,algorithm.learner_group.get_state()['learner']['optimizer'])
        resumed=algorithm.train()
        save_run(algorithm,destination/'resumed',settings,2)
        algorithm.stop();algorithm=None
        ray.shutdown()
        policy=OfflinePolicy(destination/'resumed');frozen=OfflinePolicy(destination/'initial')
        random_report=evaluate(policy,None,2,'rl-heldout-integration-random')
        frozen_report=evaluate(policy,frozen,2,'rl-heldout-integration-frozen')
        report={'versions':runtime_versions(),'initial':result,'resumed':resumed,
                'optimizer_restored_exactly':True,'weights_restored_exactly':True,
                'parameter_delta_l2':torch.linalg.vector_norm(after-before).item(),
                'seconds':time.monotonic()-start,
                'peak_driver_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
                'versus_random':random_report,'versus_frozen':frozen_report}
        (destination/'report.json').write_text(json.dumps(report,default=lambda x:x.tolist() if hasattr(x,'tolist') else str(x),indent=2))
        print('Integrated pilot complete',flush=True)
    finally:
        if algorithm is not None:algorithm.stop()
        ray.shutdown()


if __name__=='__main__':main()
