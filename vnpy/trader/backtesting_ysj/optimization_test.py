from datetime import datetime

import pandas as pd
from pandas import DataFrame

from vnpy.trader.backtesting_ysj.backtesting_test import executeTestBacktesting
from vnpy.trader.common_util import *
from vnpy.trader.constant import Interval
from vnpy_ctastrategy.backtesting import BacktestingEngine

from vnpy.trader.optimize import OptimizationSetting
from vnpy_ctastrategy.strategies import w_s12_strategy, double_ma_strategy


def doTestBfOptimization(strategy_class, symbol, exchange, startDate: datetime, endDate: datetime, rate, slippage,
                         size, pricetick, capital, minuteWindow, optSetting: OptimizationSetting):
    startDate = startDate.replace(hour=9, minute=0, second=0, microsecond=0)
    endDate = endDate.replace(hour=15, minute=0, second=0, microsecond=0)
    optResults = executeTestBacktesting(strategy_class, {}, symbol + '.' + exchange, Interval.MINUTE5,
                                        startDate, endDate, rate, slippage, size, pricetick, capital, minuteWindow,
                                        onlyOptimized=True, optSetting=optSetting, output=True)
    return optResults


def doTestDynamicOptimization(startDate: datetime, endDate: datetime, trainDayLength: int, testDayLength: int):
    ### 入参校验

    ### 切割日期
    # 获取螺纹钢指数的所有交易日（代表市场交易日）
    allTradeDates = getAllTradeDate('RBL9', Exchange.SHFE, datetime(1900, 1, 1),
                                    datetime(2100, 12, 31))
    if not allTradeDates:
        print(r'***获取全部交易日失败')
        return
    if startDate < allTradeDates[0]:
        print(r'***参数startDate早于所能获取的最早交易日')
        return

    ### 调用回测接口，进行分段训练、测试
    startDate = startDate.replace(hour=0, minute=0, second=0, microsecond=0)
    endDate = endDate.replace(hour=23, minute=59, second=59, microsecond=0)
    _startIndex = findFirstPos(startDate, allTradeDates)
    _endIndex = None
    _startDate = getRealTradeDatetime(allTradeDates, _startIndex)
    _endDate = None
    isTrain = True  # 初次是训练
    daily_pnl: DataFrame = pd.DataFrame()  # 每日盈亏
    selectedParams: dict = {}  # 参数优化后选中的参数
    skip = False
    while not skip and _startDate < endDate:
        if isTrain:  # 训练
            _endIndex = _startIndex + trainDayLength - 1
            if _endIndex >= len(allTradeDates):
                _endIndex = len(allTradeDates) - 1
                skip = True
            _endDate = getRealTradeDatetime(allTradeDates, _endIndex, 1)
            optSetting = OptimizationSetting()
            optSetting.set_target("sharpe_ratio")
            optSetting.add_parameter("fast_window", 5, 20, 5)
            optSetting.add_parameter("slow_window", 30, 60, 5)
            optResults = executeTestBacktesting(double_ma_strategy.DoubleMaStrategy, {}, "RBL9.SHFE",
                                                Interval.MINUTE5, _startDate, _endDate, 0.0002, 1,
                                                10, 1, 15000, 60, True,
                                                False, optSetting=optSetting)
            selectedParams = optResults[0]
            printInfo(f'训练区间[{_startDate}-{_endDate}]，最优参数={selectedParams}')
            # printInfo(f'训练区间[{_startDate}-{_endDate}]')
            isTrain = False
            _startIndex = _endIndex + 1
        else:  # 测试
            _endIndex = _startIndex + testDayLength - 1
            if _endIndex >= len(allTradeDates):
                _endIndex = len(allTradeDates) - 1
                skip = True
            _endDate = getRealTradeDatetime(allTradeDates, _endIndex, 1)
            daily_df, statistic = executeTestBacktesting(double_ma_strategy.DoubleMaStrategy, selectedParams,
                                                         "RBL9.SHFE", Interval.MINUTE5, _startDate, _endDate,
                                                         0.0002, 1, 10, 1, 15000,
                                                         60, False, False)
            daily_pnl = pd.concat([daily_pnl, daily_df], ignore_index=True)  # 拼接每日盈亏
            annual_return = statistic['annual_return']
            max_drawdown = statistic['max_drawdown']
            max_ddpercent = statistic['max_ddpercent']
            sharpe_ratio = statistic['sharpe_ratio']
            printInfo(f'测试区间[{_startDate}-{_endDate}]，参数={selectedParams}；年化收益={annual_return:.2f}，'
                      f'最大回撤={max_drawdown:.2f}，最大回撤率={max_ddpercent:.2f}，夏普比率={sharpe_ratio:.2f}')
            # printInfo(f'测试区间[{_startDate}-{_endDate}]')
            isTrain = True
            _startIndex = _endIndex + 1 - trainDayLength
        _startDate = getRealTradeDatetime(allTradeDates, _startIndex)

    ### 汇总
    engine = BacktestingEngine()
    engine.capital = 15000
    final_statistic = engine.calculate_statistics(daily_pnl)  # 计算汇总的指标
    final_annual_return = final_statistic['annual_return']
    final_max_drawdown = final_statistic['max_drawdown']
    final_max_ddpercent = final_statistic['max_ddpercent']
    final_sharpe_ratio = final_statistic['sharpe_ratio']
    printInfo(f'测试区间[{dateFormat(startDate)}-{dateFormat(endDate)}]；年化收益={final_annual_return:.2f}，'
              f'最大回撤={final_max_drawdown:.2f}，最大回撤率={final_max_ddpercent:.2f}%，夏普比率={final_sharpe_ratio:.2f}')


if __name__ == "__main__":
    """"""
    t0 = datetime.now()

    # 参数优化测试
    startDate = datetime(2024, 1, 1, 9, 0)
    endDate = datetime(2024, 12, 31)
    optSetting = OptimizationSetting()
    optSetting.set_target("sharpe_ratio")
    optSetting.add_parameter("len", 20, 300, 60)
    optSetting.add_parameter("stpr", 15, 50, 5)
    optSetting.add_parameter("n", 20, 90, 30)
    doTestBfOptimization(w_s12_strategy.WS12Strategy, 'RBL9', 'SHFE', startDate, endDate, 0.0002,
                         1, 10, 1, 15000, 60, optSetting)

    # 动态参数优化
    # trainDay = 240
    # testDay = 120
    # doTestDynamicOptimization(datetime(2024, 1, 1, tzinfo=pytz.UTC),
    #                           datetime(2025, 5, 31, tzinfo=pytz.UTC), trainDay, testDay)

    t1 = datetime.now()
    print(f'\n>>>>>>总耗时{t1 - t0}s')
