from datetime import datetime

import numpy as np
import pandas as pd


def doTestCommon():
    """"""
    # print(f'route={Path.cwd()}')
    # print(f'result={math.ceil(69/6)}')

    # arr = np.array(([2, 3], [5, 6]))
    # print(f'arr: {arr}')
    # result = arr - 1
    # print(result)

    # arr2 = pd.Series(np.array([2, 3, -1, -2]))
    # print(f'arr2: {arr2}')
    # a1 = tafunc.ref(arr2, 1)
    # a2 = tafunc.hhv(arr2, 2)
    # a3 = tafunc.barlast(arr2 > 0)
    # print(f'a1=\n{a1}, \n\na2=\n{a2}, \n\na3=\n{a3}')

    # b1 = np.where(arr2 > 0, arr2, 0)
    # print(f'b1=\n{b1}')

    # print(f'nan > 1: {np.nan < 1}')
    # print(f'nan min: {min(np.nan, 3)}, max: {max(np.nan, 3)}')

    # c1 = arr2.rolling([2, 2, 3, 4]).sum()  # rolling函数参数仅支持固定整数
    # print(f'c1: {c1}')

    arr3 = pd.Series(np.array([1, 1, 2, 3]))
    # d1 = tafunc.hhv(arr2, arr3)
    # print(f'd1: {d1}')
    # d2 = arr2 * arr3
    # print(f'd2: {d2}')

    # print(f'max: {max(arr2, 1)}')
    # print(f'max: {max(arr2, arr3)}')
    # print(f'max: {[max(v, 1) for v in arr2]}')

    # arr4 = pd.Series(np.array([2, 3, -1, np.nan]))
    # print(f'isnan: {np.isnan(arr4)}')

    # list1 = [1, 2, 3, 4]
    # print(f'con: {arr2 > 0 and list1 > 2}')
    # print(f'con: {tafunc.barlast(arr2 > 0 and arr3 < 3)}')
    # print(f'con: {tafunc.barlast(arr2 > 0 and arr2.shift(1) > 2)}')
    # ps1 = pd.Series([arr2.iloc[i] > 0 and arr2.iloc[i - 1] > 0 if i > 0 else False for i in range(0, len(list1))])
    # print(ps1)
    # print(f'con: {tafunc.barlast(ps1)}')

    # brr1 = pd.Series([False, True, False, True])
    # brr2 = pd.Series([True, True, True, False])
    # print(brr1 & brr2)

    # list2 = [1, 2, 3, 2]
    # print(f'list / list: {list1 / list2}')
    # print(f'arr / arr: {arr2 / arr3}')

    # arr4 = pd.Series(np.array([1.023, 1.025, 1.026, 2.119, 3]))
    # list3 = [1.023, 1.025, 1.026, 2.119, 3]
    arr4 = pd.Series(np.array([1.23, 1.25, 1.35, 1.26, 2.119, 3]))
    # list3 = [1.23, 1.25, 1.26, 2.119, 3]
    # print(f'round arr4: {np.around(arr4, 1)}')
    # print(f'round list3: {np.around(list3, 1)}')
    # print(f'np.minimum: {np.minimum(arr2, arr3)}')

    nn1 = 1
    if nn1:
        print(f'nn1 is not None')
    else:
        print(f'nn1 is None')


if __name__ == "__main__":
    """"""
    t0 = datetime.now()

    doTestCommon()  # 调试

    t1 = datetime.now()
    print(f'\n>>>>>>总耗时{t1 - t0}s')