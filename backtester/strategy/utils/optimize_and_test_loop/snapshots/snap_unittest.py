# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots['TestOptimizeAndTestLoop::test_optimize_and_test_loop_basic_functionality 1'] = '''{
    "0": {
        "optimize_indices": [
            0.0,
            100.0
        ],
        "test_indices": [
            100.0,
            150.0
        ],
        "optimized_params": [
            0.0,
            1000.0,
            100.0
        ],
        "test_result": [
            165100.0
        ]
    },
    "1": {
        "optimize_indices": [
            75.0,
            175.0
        ],
        "test_indices": [
            175.0,
            225.0
        ],
        "optimized_params": [
            750.0,
            1750.0,
            250.0
        ],
        "test_result": [
            618925.0
        ]
    },
    "2": {
        "optimize_indices": [
            150.0,
            250.0
        ],
        "test_indices": [
            250.0,
            300.0
        ],
        "optimized_params": [
            1500.0,
            2500.0,
            400.0
        ],
        "test_result": [
            1320250.0
        ]
    },
    "3": {
        "optimize_indices": [
            225.0,
            325.0
        ],
        "test_indices": [
            325.0,
            375.0
        ],
        "optimized_params": [
            2250.0,
            3250.0,
            550.0
        ],
        "test_result": [
            2269075.0
        ]
    },
    "4": {
        "optimize_indices": [
            300.0,
            400.0
        ],
        "test_indices": [
            400.0,
            450.0
        ],
        "optimized_params": [
            3000.0,
            4000.0,
            700.0
        ],
        "test_result": [
            3465400.0
        ]
    },
    "5": {
        "optimize_indices": [
            375.0,
            475.0
        ],
        "test_indices": [
            475.0,
            525.0
        ],
        "optimized_params": [
            3750.0,
            4750.0,
            850.0
        ],
        "test_result": [
            4909225.0
        ]
    },
    "6": {
        "optimize_indices": [
            450.0,
            550.0
        ],
        "test_indices": [
            550.0,
            600.0
        ],
        "optimized_params": [
            4500.0,
            5500.0,
            1000.0
        ],
        "test_result": [
            6600550.0
        ]
    },
    "7": {
        "optimize_indices": [
            525.0,
            625.0
        ],
        "test_indices": [
            625.0,
            675.0
        ],
        "optimized_params": [
            5250.0,
            6250.0,
            1150.0
        ],
        "test_result": [
            8539375.0
        ]
    },
    "8": {
        "optimize_indices": [
            600.0,
            700.0
        ],
        "test_indices": [
            700.0,
            750.0
        ],
        "optimized_params": [
            6000.0,
            7000.0,
            1300.0
        ],
        "test_result": [
            10725700.0
        ]
    },
    "9": {
        "optimize_indices": [
            675.0,
            775.0
        ],
        "test_indices": [
            775.0,
            825.0
        ],
        "optimized_params": [
            6750.0,
            7750.0,
            1450.0
        ],
        "test_result": [
            13159525.0
        ]
    },
    "10": {
        "optimize_indices": [
            750.0,
            850.0
        ],
        "test_indices": [
            850.0,
            900.0
        ],
        "optimized_params": [
            7500.0,
            8500.0,
            1600.0
        ],
        "test_result": [
            15840850.0
        ]
    },
    "11": {
        "optimize_indices": [
            825.0,
            925.0
        ],
        "test_indices": [
            925.0,
            975.0
        ],
        "optimized_params": [
            8250.0,
            9250.0,
            1750.0
        ],
        "test_result": [
            18769675.0
        ]
    }
}'''
