import numpy as np
import time
import talib
from numba import jit # type: ignore
import random
import ctypes
import numba as nb
import psutil
import os


def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # in MB

print(f"Memory usage: {get_memory_usage()} MB")
arr_size = 100000
arr = np.arange(arr_size).astype(np.double)  # create arbitrary numpy array
print(arr)
@nb.extending.intrinsic
def address_as_void_pointer(typingctx, src):
    """ returns a void pointer from a given memory address """
    sig = nb.core.types.voidptr(src)

    def codegen(cgctx, builder, sig, args):
        return builder.inttoptr(args[0], nb.core.cgutils.voidptr_t)
    return sig, codegen

addr = arr.ctypes.data

@nb.njit
def get_arr_from_address(address: int, arr_shape: tuple, arr_dtype: np.dtype):
    return nb.carray(address_as_void_pointer(address), arr_shape, dtype=arr_dtype)

@nb.njit
def modify_data(address: int, addv: float):
    """ a function taking the memory address of an array to modify it """
    # data = nb.carray(address_as_void_pointer(address), arr.shape, dtype=arr.dtype)
    data = get_arr_from_address(address, (arr_size,), np.float64)
    data += addv

global addrg
addrg = 0

# @nb.njit
def modify_data_test():
    global addrg
    arr2 = np.arange(arr_size).astype(np.double)  # create arbitrary numpy array
    print(f"Memory usage: {get_memory_usage()} MB")
    print(arr2)
    addr2 = arr2.ctypes.data
    modify_data(addr2, 10)
    addrg = addr2
    print(f"addrg: {addrg}")
    print(arr2)
    arr2.resize(0, refcheck=False)

print(f"Memory usage: {get_memory_usage()} MB")
modify_data(addr, 2)
print(arr)
print(f"Memory usage: {get_memory_usage()} MB")
modify_data_test()
print(addrg)
re_arr = get_arr_from_address(addrg, (arr_size,), np.float64)
print(re_arr)
print(f"Memory usage: {get_memory_usage()} MB")
modify_data_test()
print(f"Memory usage: {get_memory_usage()} MB")
modify_data_test()
print(f"Memory usage: {get_memory_usage()} MB")
modify_data_test()
print(f"Memory usage: {get_memory_usage()} MB")


# @jit
# def test_numba(arr: np.ndarray):
#     initial = 0
#     for i in range(0, len(arr)):
#         initial += arr[i]
#     return initial

# @jit
# def get_rand_arr(size: int):
#     return np.array([1 + random.randint(0, 9) for _ in range(size)])

# def test():
#     add = lambda a, b: a + b
#     initial_0 = test_numba(np.array([]))
#     print(f"initial_0: {initial_0}")
#     # random_arr = np.array([1 + random.randint(0, 9) for _ in range(100000000)])
#     random_arr = get_rand_arr(100000000)
#     start = time.perf_counter()
#     initial = test_numba(random_arr)
#     end = time.perf_counter()
#     print(f"Hello, world! init + 1 = {add(initial, 1)}")
#     print(f"Time elapsed: {(end - start) * 1000}ms")

# def main():
#     vec_1 = np.arange(0, 100000, 1)
#     vec_2 = np.arange(0, 100000, 1)

#     start = time.perf_counter()

#     vec_sum = vec_1 + vec_2

#     end = time.perf_counter()
#     print(f"Time elapsed: {(end - start) * 1000}ms")

#     print(vec_sum)

# def np_ma():
#     list_len = 100000
#     ma_len = 20

#     vec_1 = np.arange(0, list_len, 1)

#     start = time.perf_counter()

#     window = np.ones(ma_len) / ma_len
#     # Compute moving average using convolution
#     vec_1_ma = np.convolve(vec_1, window, mode='valid')

#     end = time.perf_counter()
#     print(f"Time elapsed: {(end - start) * 1000}ms")

#     print(vec_1_ma) 

# def ta_lib_ma():
#     list_len = 100000
#     ma_len = 20

#     vec_1 = np.arange(0, list_len, 1, dtype=np.float64)

#     start = time.perf_counter()

#     vec_1_ma = talib.MA(vec_1, timeperiod=ma_len)

#     end = time.perf_counter()
#     print(f"Time elapsed: {(end - start) * 1000}ms")

#     print(vec_1_ma)


# def main2():
#     vec_1 = range(0, 100000, 1)
#     vec_2 = range(0, 100000, 1)

#     start = time.perf_counter()

#     vec_sum = []

#     for i in range(0, 100000):
#         vec_sum.append(vec_1[i] + vec_2[i])

#     end = time.perf_counter()
#     print(f"Time elapsed: {(end - start) * 1000}ms")

#     print(vec_sum)

# @jit
# def test_2(k):
#     nb_arr = k[0]
#     nb_arr_2 = k[1]

#     nb_arr_3 = nb_arr + nb_arr_2[0]

#     return nb_arr_3

# print(test_2((np.array([1, 2, 3]), np.array([[4, 5, 6], [7, 8, 9]]))))


nb_of_els = 100

@nb.njit
def testing_append():
    arr = np.empty((0, 10), dtype=np.float64)
    for i in range(0, nb_of_els):
        arr = np.append(arr, np.array([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]], dtype=np.float64), axis=0)
    return arr
testing_append()

@nb.njit
def testing_replace_in_place():
    arr = np.empty((nb_of_els, 10), dtype=np.float64)
    arr.fill(np.nan)
    for i in range(0, nb_of_els):
        next_nan_indice = np.argmax(np.isnan(arr[0]))
        arr[next_nan_indice] = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=np.float64)
        # arr[i] = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=np.float64)
    return arr
testing_replace_in_place()

@nb.njit
def testing_full_replace():
    arr = np.empty((nb_of_els, 10), dtype=np.float64)
    for i in range(0, nb_of_els):
        next_arr = arr.copy()
        next_arr[i] = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=np.float64)
        arr = next_arr
    return arr
testing_full_replace()


@nb.njit
def get_next_nan_indice(arr: np.ndarray):
    nan_indices = np.where(np.isnan(arr[0]))[0]
    return nan_indices[0]

def main():
    start = time.perf_counter()
    testing_append()
    end = time.perf_counter()
    print(f"testing_append Time elapsed: {(end - start) * 1000}ms")

    start = time.perf_counter()
    testing_replace_in_place()
    end = time.perf_counter()
    print(f"testing_replace_in_place Time elapsed: {(end - start) * 1000}ms")

    start = time.perf_counter()
    testing_full_replace()
    end = time.perf_counter()
    print(f"testing_full_replace Time elapsed: {(end - start) * 1000}ms")

main()