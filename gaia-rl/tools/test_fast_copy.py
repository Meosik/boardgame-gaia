import copy
import json
import unittest

import fast_copy


class FastCopyTests(unittest.TestCase):
    def test_json_data_copies_equal_and_independent(self):
        value = json.loads('{"a": [1, {"b": [2.5, null, true, "x"]}], "c": {"d": []}}')
        result = fast_copy.fast_deepcopy(value)
        self.assertEqual(result, copy.deepcopy(value))
        result['a'][1]['b'].append(3)
        result['c']['d'].append(1)
        self.assertEqual(value, json.loads('{"a": [1, {"b": [2.5, null, true, "x"]}], "c": {"d": []}}'))

    def test_dict_order_and_tuples_are_preserved(self):
        value = {'z': 1, 'a': (1, [2]), 'm': 3}
        result = fast_copy.fast_deepcopy(value)
        self.assertEqual(list(result), ['z', 'a', 'm'])
        self.assertEqual(result['a'], (1, [2]))
        self.assertIsNot(result['a'][1], value['a'][1])

    def test_other_types_use_the_original_deepcopy(self):
        class Box:
            def __init__(self):
                self.items = [1]
        box = Box()
        result = fast_copy.fast_deepcopy({'box': box, 'set': {1, 2}})
        self.assertIsNot(result['box'], box)
        self.assertEqual(result['box'].items, [1])
        self.assertEqual(result['set'], {1, 2})

    def test_install_replaces_copy_deepcopy(self):
        original = copy.deepcopy
        try:
            fast_copy.install()
            self.assertIs(copy.deepcopy, fast_copy.fast_deepcopy)
        finally:
            copy.deepcopy = original


if __name__ == '__main__':
    unittest.main()
