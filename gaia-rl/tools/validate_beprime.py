"""Compare current (e) to delayed, discounted (e-prime), with (f) fixed ON."""
from dataclasses import dataclass
from pathlib import Path

import validate_bef as validator
import state_evaluation_bef as variant


@dataclass(frozen=True)
class Configured:
    delayed: bool = False

    def evaluate_state(self, state, actor, **kwargs):
        return variant.evaluate_state(state, actor, token_shortfall=True,
            remaining_income=True, distributed_research=True,
            round_resource_prices=True, expansion_rescale=True,
            discounted_expansion=self.delayed, **kwargs)


MODELS = {'B⁗+e+f': Configured(), 'B⁗+e′+f': Configured(delayed=True)}


def run(output: Path) -> bool:
    validator.MODELS = MODELS
    return validator.run(output, round_five_invariants=True)


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(int(run(parser.parse_args().output)))
