import unittest
from coaching.server import teacher_factory

FIXED = {'target_seconds': 10, 'long_seconds': 10, 'uses_per_seat': 0}
OLD = {'target_seconds': 10, 'long_seconds': 120, 'uses_per_seat': 6}


class ClockTests(unittest.TestCase):
    def test_new_coaching_clock_has_no_extension(self):
        teacher = teacher_factory({'seed': 'test', 'delta_factions': []})([], {})
        self.assertEqual(teacher.target_seconds, 10)
        self.assertEqual(teacher.maximum_seconds, 10)
        self.assertEqual(teacher.adaptive_clock.uses, 0)

    def test_legacy_clock_remains_unchanged_without_amendment(self):
        teacher = teacher_factory({'seed': 'test', 'delta_factions': [], 'clock': OLD})([], {})
        self.assertEqual(teacher.maximum_seconds, 120)
        self.assertEqual(teacher.adaptive_clock.uses, 6)

    def test_boundary_and_old_spent_clock_do_not_enable_extension(self):
        memory = {'_clock': {'spent': [['0', 0], ['1', 1]]}, '_plans': {'2': {'saved': True}}}
        make = teacher_factory({'seed': 'test', 'delta_factions': [], 'clock': OLD},
                               {'effective_from_decision': 7, 'clock': FIXED})
        old = make([0]*6, memory.copy())
        new = make([0]*7, memory.copy())
        self.assertEqual(old.maximum_seconds, 120)
        self.assertEqual(new.maximum_seconds, 10)
        self.assertEqual(new.adaptive_clock.remaining('1'), 0)
        self.assertEqual(new.memory['_plans'], memory['_plans'])
        self.assertEqual(memory['_clock']['spent'], [['0', 0], ['1', 1]])


if __name__ == '__main__':
    unittest.main()
