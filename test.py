import numpy as np
import time
import talib
from numba import jit # type: ignore
import random

@jit
def test_numba(arr: np.ndarray):
    initial = 0
    for i in range(0, len(arr)):
        initial += arr[i]
    return initial

@jit
def get_rand_arr(size: int):
    return np.array([1 + random.randint(0, 9) for _ in range(size)])

def test():
    add = lambda a, b: a + b
    initial_0 = test_numba(np.array([]))
    print(f"initial_0: {initial_0}")
    # random_arr = np.array([1 + random.randint(0, 9) for _ in range(100000000)])
    random_arr = get_rand_arr(100000000)
    start = time.perf_counter()
    initial = test_numba(random_arr)
    end = time.perf_counter()
    print(f"Hello, world! init + 1 = {add(initial, 1)}")
    print(f"Time elapsed: {(end - start) * 1000}ms")

def main():
    vec_1 = np.arange(0, 100000, 1)
    vec_2 = np.arange(0, 100000, 1)

    start = time.perf_counter()

    vec_sum = vec_1 + vec_2

    end = time.perf_counter()
    print(f"Time elapsed: {(end - start) * 1000}ms")

    print(vec_sum)

def np_ma():
    list_len = 100000
    ma_len = 20

    vec_1 = np.arange(0, list_len, 1)

    start = time.perf_counter()

    window = np.ones(ma_len) / ma_len
    # Compute moving average using convolution
    vec_1_ma = np.convolve(vec_1, window, mode='valid')

    end = time.perf_counter()
    print(f"Time elapsed: {(end - start) * 1000}ms")

    print(vec_1_ma) 

def ta_lib_ma():
    list_len = 100000
    ma_len = 20

    vec_1 = np.arange(0, list_len, 1, dtype=np.float64)

    start = time.perf_counter()

    vec_1_ma = talib.MA(vec_1, timeperiod=ma_len)

    end = time.perf_counter()
    print(f"Time elapsed: {(end - start) * 1000}ms")

    print(vec_1_ma)


def main2():
    vec_1 = range(0, 100000, 1)
    vec_2 = range(0, 100000, 1)

    start = time.perf_counter()

    vec_sum = []

    for i in range(0, 100000):
        vec_sum.append(vec_1[i] + vec_2[i])

    end = time.perf_counter()
    print(f"Time elapsed: {(end - start) * 1000}ms")

    print(vec_sum)

@jit
def test_2(k):
    nb_arr = k[0]
    nb_arr_2 = k[1]

    nb_arr_3 = nb_arr + nb_arr_2[0]

    return nb_arr_3

print(test_2((np.array([1, 2, 3]), np.array([[4, 5, 6], [7, 8, 9]]))))