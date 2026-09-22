import unittest

from state_teacher_ab import fixed_schedule, win_rates


class StateABTests(unittest.TestCase):
    def test_extension_preserves_the_first_twenty_games(self):
        seeds = [f'fixed-{i}' for i in range(20)]
        self.assertEqual(fixed_schedule(seeds[:10],20),fixed_schedule(seeds,40)[:10])

    def test_tied_wins_are_fractional_and_failures_are_not_losses(self):
        game = {'complete':True,'scores':{'0':100,'1':100,'2':50,'3':40},
                'a_seats':[0,2],'factions':['Xenos','Terrans','Taklons','HadschHallas']}
        self.assertEqual(win_rates([game,{'complete':False}]),{'A':0.25,'B':0.25})
        self.assertEqual(win_rates([game],'Xenos'),{'A':0.5,'B':None})

    def test_short_or_repeated_seed_lists_rejected(self):
        for seeds in (['a'],['a','a']):
            with self.assertRaises(ValueError):
                fixed_schedule(seeds,4)


if __name__ == '__main__':
    unittest.main()
