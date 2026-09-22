"""Explicit local commands; never train or select a latest model implicitly."""
import argparse
import json
from pathlib import Path

from . import FACTIONS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init', help='18 independent models; optional explicit PPO import')
    init.add_argument('--output', type=Path, required=True)
    init.add_argument('--source', type=Path)
    init.add_argument('--seed', type=int, default=19)
    status = commands.add_parser('status', help='Validate versions/checksums and show training state')
    status.add_argument('catalog', type=Path)
    bc = commands.add_parser('bc', help='Branch one faction from native-replayed human or teacher games')
    bc.add_argument('--labels', choices=('human', 'teacher'), default='human')
    bc.add_argument('--source', type=Path, required=True)
    bc.add_argument('--output', type=Path, required=True)
    bc.add_argument('--faction', choices=FACTIONS, required=True)
    bc.add_argument('--training-game', type=Path, action='append', required=True)
    bc.add_argument('--validation-game', type=Path, action='append', required=True)
    bc.add_argument('--epochs', type=int, required=True)
    bc.add_argument('--seed', type=int, default=19)
    audit = commands.add_parser('audit', help='Independently replay one complete local recording')
    audit.add_argument('game', type=Path)
    audit.add_argument('--faction', choices=FACTIONS, required=True)
    audit.add_argument('--labels', choices=('human', 'teacher'), default='human')
    args = parser.parse_args()
    if args.command == 'status':
        from .models import read_catalog
        data = read_catalog(args.catalog)
        result = {f: e['status'] for f, e in data['models'].items()}
    else:
        import torch
        torch.set_num_threads(2)
        if args.command == 'init':
            from .models import initialize
            result = initialize(args.output, source=args.source, seed=args.seed)
            result = {f: e['status'] for f, e in result['models'].items()}
        elif args.command == 'bc':
            from .behavior import train
            result = train(args.source, args.output, args.faction, args.training_game,
                           args.validation_game, epochs=args.epochs, seed=args.seed, label_source=args.labels)
        else:
            from gaia_rl.encoding import FeatureEncoder
            from .records import audited_samples
            _, result = audited_samples(args.game, args.faction, FeatureEncoder(4096), controller=args.labels)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
