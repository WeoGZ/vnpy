import enum

import pandas as pd

from vnpy.trader.constant import *
from vnpy.trader.constant import Interval
from vnpy.trader.optimize import OptimizationSetting
from vnpy_ctastrategy.backtesting import BacktestingEngine
from vnpy_ctastrategy.strategies import w_s12_strategy


class PeriodType(enum.Enum):
    Year = 0
    HalfYear = 1
    Quarter = 2
    Month = 3
    Week = 4


def doTestBacktesting():
    # startDate = datetime(2023, 1, 5, 9, 0)
    startDate = datetime(2024, 1, 1, 9, 0)
    endDate = datetime(2024, 12, 31)
    daily_pnl, statistic = executeTestBacktesting(w_s12_strategy.WS12Strategy, {"len": 250, "stpr": 20, "n": 70},
                                                  "RBL9.SHFE", Interval.MINUTE5, startDate, endDate,
                                                  0.0002, 1, 10, 1, 15000,
                                                  60, showOrders=True, pre_load_month=1)
    daily_pnl2, statistic2 = executeTestBacktesting(w_s12_strategy.WS12Strategy, {"len": 50, "stpr": 15, "n": 20},
                                                    "SAL9.CZCE", Interval.MINUTE5, startDate, endDate,
                                                    0.0003, 1, 20, 1, 15000,
                                                    60, showOrders=True)  # 纯碱有一点误差，原因是通达信数据与文华数据差异性导致
    daily_pnl3, statistic3 = executeTestBacktesting(w_s12_strategy.WS12Strategy, {"len": 130, "stpr": 40, "n": 20},
                                                    "AOL9.SHFE", Interval.MINUTE5, startDate, endDate,
                                                    0.0002, 1, 20, 1, 20000,
                                                    60, showOrders=True, pre_load_month=2)
    # 合并组合测试
    engine = BacktestingEngine()
    engine.capital = 50000
    sum_daily_pnl = daily_pnl + daily_pnl2 + daily_pnl3
    sum_daily_pnl = sum_daily_pnl.dropna()
    final_statistic = engine.calculate_statistics(sum_daily_pnl)


def executeTestBacktesting(strategy_class, setting: dict, vt_symbol, interval, startDate, endDate, rate, slippage,
                           size, pricetick, capital, minuteWindow=60, onlyOptimized=False, showChart=False,
                           showOrders=False, pre_load_month=2, optSetting: OptimizationSetting = {},
                           output=False) -> list | pd.DataFrame:
    engine = BacktestingEngine()
    engine.set_parameters(
        vt_symbol=vt_symbol,
        interval=interval,
        start=startDate,
        end=endDate,
        rate=rate,
        slippage=slippage,
        size=size,
        pricetick=pricetick,
        capital=capital,
        pre_load_month=pre_load_month
    )
    engine.add_strategy(strategy_class, setting, minuteWindow)
    if onlyOptimized:  # 只做参数优化
        # engine.run_ga_optimization(setting)
        results = engine.run_bf_optimization(optSetting, output=output, max_workers=None)
        return results
    else:  # 普通回测
        engine.load_data()
        engine.run_backtesting()
        daily_pnl = engine.calculate_result()
        statistic = engine.calculate_statistics()
        if showChart:
            engine.show_chart().show()
        if showOrders:
            # print(f'\n>>>>>>>>>>Orders<<<<<<<<<<\n{engine.get_all_orders()}\n')
            order_list = [
                f'{x.datetime.strftime("%Y-%m-%d %H:%M:%S")} {x.direction.value} {x.offset.value} {x.price} {x.volume} {x.status.value}'
                for x in engine.get_all_orders()]
            print(f'\n>>>>>>>>>>Orders<<<<<<<<<<\n{order_list}\n')

            net_pnl_list = [x.net_pnl for x in engine.get_all_daily_results()]
            print(f'每日盈亏={net_pnl_list}')
            print(f'每日盈亏汇总={sum(net_pnl_list)}')
        return daily_pnl, statistic


if __name__ == "__main__":
    """"""
    t0 = datetime.now()

    # 回测测试
    doTestBacktesting()

    t1 = datetime.now()
    print(f'\n>>>>>>总耗时{t1 - t0}s')
