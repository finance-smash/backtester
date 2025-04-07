import unittest
import numpy as np
from .generate_optimize_and_test_indices import generate_optimize_and_test_indices
from backtester.commons import TOhlcv


class TestOptimizeTestIndices(unittest.TestCase):
    
    def setUp(self):
        self.data_len = 5000
        optimize_indices, test_indices = generate_optimize_and_test_indices(
            data_len=self.data_len,
            nb_of_items_to_optimize_on=30,
            nb_of_items_to_test_on=10,
            nb_of_items_for_step=5
        )
        self.optimize_indices = optimize_indices
        self.test_indices = test_indices
    
    def test_basic_functionality(self):
        """Test basic functionality and result integrity"""
        self.assertEqual(len(self.optimize_indices), 994)
        self.assertEqual(self.optimize_indices.shape, (994, 2))
        self.assertEqual(len(self.test_indices), 994)
        self.assertEqual(self.test_indices.shape, (994, 2))
    
    def test_size_of_optimize_intervals_are_correct(self):
        """Test that the size of the optimize intervals are correct"""
        for optimize_index in self.optimize_indices:
            self.assertEqual(optimize_index[1] - optimize_index[0], 30)

    def test_size_of_test_intervals_are_correct(self):
        """Test that the size of the test intervals are correct"""
        for i in range(len(self.test_indices) - 1):
            test_index = self.test_indices[i]
            self.assertEqual(test_index[1] - test_index[0], 10)
        last_test_index = self.test_indices[-1]
        self.assertEqual(last_test_index[1] - last_test_index[0], 5)
    
    def test_step_size_is_correct(self):
        """Test that the step size is correct"""
        for i in range(len(self.optimize_indices) - 1):
            optimize_index = self.optimize_indices[i]
            optimize_index_next = self.optimize_indices[i + 1]
            self.assertEqual(optimize_index_next[0] - optimize_index[0], 5)


if __name__ == '__main__':
    unittest.main()