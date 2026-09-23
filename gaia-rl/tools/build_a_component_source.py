"""Build a disposable frozen-A derivative with independent default-off component flags."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / 'gaia-rl/baseline-teacher-20260917'


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f'exact patch anchor count != 1 in {path}: {old[:80]!r}')
    path.chmod(path.stat().st_mode | 0o200)
    path.write_text(text.replace(old, new))


def digest(root: Path) -> str:
    value = hashlib.sha256()
    for path in sorted(root.rglob('*.py')):
        value.update(path.relative_to(root).as_posix().encode())
        value.update(hashlib.sha256(path.read_bytes()).digest())
    return value.hexdigest()


def build(output: Path) -> dict:
    if output.exists():
        raise FileExistsError(output)
    shutil.copytree(BASELINE, output)

    # The frozen source lives one directory shallower than disposable run
    # derivatives, so keep its project-root lookups pointing at the same tree.
    for path in output.rglob('*.py'):
        text = path.read_text()
        relocated = text.replace('.parents[3]', '.parents[4]').replace(
            '.parents[2]', '.parents[3]')
        if relocated != text:
            path.chmod(path.stat().st_mode | 0o200)
            path.write_text(relocated)

    quick = output / 'four_factions/quick.py'
    replace(quick, 'import math\nimport time\n', 'import math\nimport os\nimport time\n')
    replace(quick, "    actor = snapshot['player']\n", "    actor = snapshot['player']\n    conservation_off = os.environ.get('GAIA_A_RESOURCE_PRICES') == '1'\n")
    replace(quick,
            "        if action['type'] == 'FreeAction' and action['kind'] in FORBIDDEN:\n",
            "        if (not conservation_off and action['type'] == 'FreeAction'\n                and action['kind'] in FORBIDDEN):\n")
    replace(quick,
            "        elif action['type'] == 'FreeAction' and action['kind'] == 'QicToOre':\n",
            "        elif (not conservation_off and action['type'] == 'FreeAction'\n              and action['kind'] == 'QicToOre'):\n")
    replace(quick,
            "    ordered = interleave_families(eligible, lambda i: candidates[i]['action']['type'])\n",
            "    ordered = interleave_families(eligible, lambda i: candidates[i]['action']['type'])\n    if os.environ.get('GAIA_A_P_FIX') == '1':\n        ordered.sort(key=lambda i: candidates[i]['action']['type'] != 'FormFederation')\n")
    replace(quick, '        if brainstone_committed(snapshot, after, actor):\n',
            '        if not conservation_off and brainstone_committed(snapshot, after, actor):\n')

    value = output / 'four_factions/value.py'
    replace(value, 'import json\nimport copy\n', 'import json\nimport copy\nimport os\n')
    replace(value,
            'def materials(resources):\n    # A monotone concave potential, not root-dependent prices that could reward\n',
            "def materials(resources):\n    if os.environ.get('GAIA_A_RESOURCE_PRICES') == '1':\n        prices = {'credits': 0.8, 'ore': 2.67, 'knowledge': 2.67, 'qic': 4.67}\n        return sum(resources.get(key, 0) * price for key, price in prices.items())\n    # A monotone concave potential, not root-dependent prices that could reward\n")

    features = output / 'integrated/features.py'
    replace(features, 'from collections import Counter\n', 'from collections import Counter\nimport os\n')
    replace(features,
            'def resource_value(player, resources):\n    stock = player[\'resources\']\n',
            "def resource_value(player, resources):\n    if os.environ.get('GAIA_A_RESOURCE_PRICES') == '1':\n        prices = {'credits': 0.8, 'ore': 2.67, 'knowledge': 2.67, 'qic': 4.67}\n        return sum(prices[key] * value for key, value in resources.items())\n    stock = player['resources']\n")

    conservation = output / 'current_actions/conservation.py'
    replace(conservation, 'import json\n', 'import json\nimport os\n')
    replace(conservation,
            "FORBIDDEN = {'OreToCredit', 'KnowledgeToCredit'}\n",
            "FORBIDDEN = (set() if os.environ.get('GAIA_A_RESOURCE_PRICES') == '1'\n             else {'OreToCredit', 'KnowledgeToCredit'})\n")
    replace(conservation,
            "    def protect(self, env, snapshot, scores):\n        phase = snapshot['state']['phase']\n",
            "    def protect(self, env, snapshot, scores):\n        if os.environ.get('GAIA_A_RESOURCE_PRICES') == '1':\n            return scores\n        phase = snapshot['state']['phase']\n")

    teacher = output / 'four_factions/teacher.py'
    replace(teacher, 'import json\nimport math\n', 'import json\nimport math\nimport os\n')
    replace(teacher,
            'def brainstone_committed(before, after, actor):\n    return (',
            "def brainstone_committed(before, after, actor):\n    if os.environ.get('GAIA_A_RESOURCE_PRICES') == '1':\n        return False\n    return (")
    replace(teacher,
            "            forbidden = action['type'] == 'FreeAction' and action['kind'] in FORBIDDEN\n",
            "            forbidden = (os.environ.get('GAIA_A_RESOURCE_PRICES') != '1'\n                         and action['type'] == 'FreeAction' and action['kind'] in FORBIDDEN)\n")
    replace(teacher,
            "            qic_conversion = action['type'] == 'FreeAction' and action['kind'] == 'QicToOre'\n",
            "            qic_conversion = (os.environ.get('GAIA_A_RESOURCE_PRICES') != '1'\n                              and action['type'] == 'FreeAction' and action['kind'] == 'QicToOre')\n")

    record = {
        'baseline': str(BASELINE.relative_to(ROOT)),
        'baseline_python_sha256': digest(BASELINE),
        'derived_python_sha256': digest(output),
        'flags': {
            'GAIA_A_P_FIX': {'default': '0', 'scope': 'stable federation-first fallback partition'},
            'GAIA_A_RESOURCE_PRICES': {
                'default': '0',
                'scope': 'fixed source ratios and teacher conservation OFF',
                'prices': {'credits': 0.8, 'ore': 2.67, 'knowledge': 2.67, 'qic': 4.67},
            },
        },
    }
    output.chmod(output.stat().st_mode | 0o200)
    (output / 'DERIVATION.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    result = build(parser.parse_args().output)
    print(json.dumps(result, ensure_ascii=False))
