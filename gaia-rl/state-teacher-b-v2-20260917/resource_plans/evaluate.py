"""Xenos matched resource-plan comparison; no fixed opening or PPO training."""
from pathlib import Path

from research_plans.evaluate import main as compare
from resource_plans.teacher import ResourcePlanTeacher


def main():
    compare(faction='Xenos', candidate_factory=ResourcePlanTeacher,
            teacher_variant='xenos-native-resource-plans',
            fixture_dirs=(Path(__file__).parent/'fixtures',), description=__doc__)


if __name__ == '__main__':
    main()
