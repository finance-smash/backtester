import unittest
import json
from json import JSONEncoder
import numpy as np
from snapshottest import TestCase

class NumpyArrayEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return JSONEncoder.default(self, obj)

from backtester.strategy.utils.optimize_and_test_loop.optimize_and_test_loop import optimize_and_test_loop


def test_optimize_fn(optimize_indices: np.ndarray) -> np.ndarray:
    i0 = optimize_indices[0]
    i1 = optimize_indices[1]
    return np.array([i0 * 10, i1 * 10, i0 + i1])

def test_test_fn(test_indices: np.ndarray, params: np.ndarray) -> np.ndarray:
    i0 = test_indices[0]
    i1 = test_indices[1]
    p0 = params[0]
    p1 = params[1]
    p2 = params[2]
    return np.array([i0 + i1 * (p0 + p1 + p2)])

class TestOptimizeAndTestLoop(TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.data_len = 1000
        self.nb_of_items_to_optimize_on = 100
        self.nb_of_items_to_test_on = 50
        self.nb_of_items_for_step = 75

    def test_optimize_and_test_loop_basic_functionality(self):
        """Test basic functionality with mock functions."""        
        results = optimize_and_test_loop(
            optimize_fn=test_optimize_fn,
            test_fn=test_test_fn,
            data_len=self.data_len,
            nb_of_items_to_optimize_on=self.nb_of_items_to_optimize_on,
            nb_of_items_to_test_on=self.nb_of_items_to_test_on,
            nb_of_items_for_step=self.nb_of_items_for_step,
        )

        json_results = json.dumps(results, indent=4, cls=NumpyArrayEncoder)

        self.assertMatchSnapshot(json_results)  


if __name__ == '__main__':
    unittest.main()
