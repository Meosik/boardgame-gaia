"""Minimal legal-action bot, not a trained or competitive policy."""
import argparse
import json
import random

from gaia_rl import ENGINE_BUILD_ID, ENV_SCHEMA_VERSION, Environment


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", default="engine-kit-example")
    parser.add_argument("--max-steps", type=int, default=10000)
    args = parser.parse_args()
    env = Environment(args.seed, args.max_steps)
    rng = random.Random(args.seed)
    steps = 0
    while not env.is_terminal():
        snapshot = json.loads(env.snapshot_json())
        # Replace only this choice with your policy. The engine owns turn order,
        # including setup, charging decisions and other players' reactions.
        index = rng.randrange(len(snapshot["candidates"]))
        env.step(snapshot["decision_id"], index)
        steps += 1
    print(json.dumps({"complete": True, "seed": args.seed, "steps": steps,
                      "engine_build_id": ENGINE_BUILD_ID,
                      "environment_schema": ENV_SCHEMA_VERSION,
                      "scores": env.final_scores()}, indent=2))


if __name__ == "__main__":
    main()
