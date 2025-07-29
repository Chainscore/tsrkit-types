# from ctypes import c_uint8
# from time import time

# from tsrkit_types.integers import U8


# def test_compare_cuint_int():
#     start = time()
#     for i in range(1):
#         a = c_uint8(1000000)
#         print(a)
#     mid = time()
#     for i in range(10000):
#         b = U8(10)
#     end = time()
#     print("U8 took", end - mid)
#     print("c_uint8 took", mid - start)
#     print("faster", 100/((end - mid)/(mid - start)))


# from ctypes import c_uint16, c_uint8
# from time import perf_counter
# from tsrkit_types.integers import U16
# from tsrkit_types.c_integers import C_U16, C_U8

# ITERATIONS = 100_000

# def benchmark_creation():
#     start = perf_counter()
#     for _ in range(ITERATIONS):
#         a = C_U16(10000)
#     mid = perf_counter()
    
#     for _ in range(ITERATIONS):
#         b = U16(10000)
#     end = perf_counter()

#     c_time = mid - start
#     u_time = end - mid

#     print(f"C_U16 time: {c_time:.6f} seconds")
#     print(f"U16 time:   {u_time:.6f} seconds")
#     print(f"Ratio U16/C_U16:   {u_time / c_time:.2f}x slower")
#     print(f"Ratio C_U16/U16:   {c_time / u_time:.2f}x faster")

# benchmark_creation()


from ctypes import c_uint16, c_uint8
from time import perf_counter
from tsrkit_types.integers import U16  
from tsrkit_types.c_integers import C_U16  

ITERATIONS = 100_000

def benchmark_creation():
    start = perf_counter()
    for _ in range(ITERATIONS):
        a = C_U16(10000)
    mid = perf_counter()
    
    for _ in range(ITERATIONS):
        b = U16(10000)
    end = perf_counter()

    c_time = mid - start
    u_time = end - mid

    print("====== Benchmark: Int Instantiation ======")
    print(f"C_U16 (ctypes-backed) time: {c_time:.6f} seconds")
    print(f"U16   (Python-style)   time: {u_time:.6f} seconds")

    if c_time == 0 or u_time == 0:
        print("⚠️  Cannot compute ratio — one time is zero")
        return

    if u_time > c_time:
        percent = ((u_time - c_time) / u_time) * 100
        print(f"⚠️")
        print(f"✅ C_U16 is {percent:.2f}% faster than U16")
        print(f"   ")

    elif c_time > u_time:
        percent = ((c_time - u_time) / c_time) * 100
        print(f"⚠️")
        print(f"✅ U16 is {percent:.2f}% faster than C_U16")
        print(f"   ")
    else:
        print("⚠️  Both are equally fast")

    # print(f"Ratio U16 / C_U16: {u_time / c_time:.2f}x")
    # print(f"Ratio C_U16 / U16: {c_time / u_time:.2f}x")

benchmark_creation()
