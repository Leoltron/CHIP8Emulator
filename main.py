# !/usr/bin/env python3
from multiprocessing import Process, Value, Array


def f(n, a, val=3.1415927):
    n.value = val
    for i in range(len(a)):
        a[i] = i * val


def main():
    num = Value('d', 0.0)
    arr = Array('i', range(10))

    ps = []

    for i in range(5):
        p = Process(target=f, args=(num, arr, i))
        p.start()
        ps.append(p)

    print(num.value)
    print(arr[:])

    for p in ps:
        p.join()

    print(num.value)
    print(arr[:])


if __name__ == '__main__':
    main()
