import enum
import math
import re
from datetime import datetime, timedelta
from pathlib import Path
import os
import pytz
import pandas as pd
import numpy as np

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.optimize import OptimizationSetting
from vnpy_ctastrategy.backtesting import BacktestingEngine
from vnpy_ctastrategy.strategies import boll_channel_strategy, double_ma_strategy, w_s12_strategy
from vnpy.trader.object import TickData, BarData
from vnpy.trader.database import BaseDatabase, get_database
from vnpy.trader.utility import round_to
from vnpy_ctastrategy.base import INTERVAL_DELTA_MAP
from tqsdk import tafunc


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
                                                         60,  False, False)
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


def doTestBfOptimization(strategy_class, symbol, exchange, startDate: datetime, endDate: datetime, rate, slippage,
                         size, pricetick, capital, minuteWindow, optSetting: OptimizationSetting):
    startDate = startDate.replace(hour=9, minute=0, second=0, microsecond=0)
    endDate = endDate.replace(hour=15, minute=0, second=0, microsecond=0)
    optResults = executeTestBacktesting(strategy_class, {}, symbol + '.' + exchange, Interval.MINUTE5,
                                        startDate, endDate, rate, slippage, size, pricetick, capital, minuteWindow,
                                        onlyOptimized=True, optSetting=optSetting, output=True)


def executeTestBacktesting(strategy_class, setting: dict, vt_symbol, interval, startDate, endDate, rate, slippage,
                           size, pricetick, capital, minuteWindow=60, onlyOptimized=False, showChart=False,
                           showOrders=False, pre_load_month=2, optSetting: OptimizationSetting={}, output=False) -> list | pd.DataFrame:
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
    # engine.add_strategy(boll_channel_strategy.BollChannelStrategy, setting)
    # engine.add_strategy(double_ma_strategy.DoubleMaStrategy, setting)
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


def importHistoryDataFromTxt(directory, interval, encoding='utf-8'):
    '''指定目錄下文件編碼類型'''
    database: BaseDatabase = None
    # 获取螺纹钢指数的所有交易日
    allTradeDates = getAllTradeDate('RBL9', Exchange.SHFE, datetime(2000, 1, 1),
                                    datetime(2050, 12, 31))
    # 列出目录中的所有文件
    files = os.listdir(directory)
    # 遍历文件，只处理TXT文件
    for file in files:
        if file.endswith('.txt'):
            # if file.__eq__('30#RBL9.txt'):
            marketTag = file.split('.')[0].split('#')[0]
            symbol = file.split('.')[0].split('#')[1]
            exchange = getExchange(marketTag)
            print(f'\n[{datetime.now()}] >>[{symbol}] reading...')
            file_path = os.path.join(directory, file)
            with open(file_path, 'r', encoding=encoding) as f:
                barDataList: list[BarData] = []
                for line in f:
                    # for line in f.readlines()[:10]:
                    sline = line.strip()
                    # printInfo(f'line="{sline}"')
                    if startWithDigit(sline):  # 数字开头的行
                        dataArray = sline.split('\t')
                        bar = None
                        if interval == Interval.DAILY:
                            if len(dataArray) < 8:
                                printInfo(f'单个K线数据的信息数量<8，请检查格式是否发生改变。line={sline}>')
                                return
                            dt = datetime.strptime(f'{dataArray[0]} 1800', '%Y/%m/%d %H%M')
                            bar: BarData = BarData(
                                symbol=symbol,
                                exchange=exchange,
                                interval=interval,
                                datetime=dt,
                                open_price=round_to(dataArray[1], 0.000001),
                                high_price=round_to(dataArray[2], 0.000001),
                                low_price=round_to(dataArray[3], 0.000001),
                                close_price=round_to(dataArray[4], 0.000001),
                                volume=dataArray[5],
                                turnover=0,
                                open_interest=dataArray[6],
                                gateway_name="tdx"
                            )
                        else:
                            if len(dataArray) < 9:
                                printInfo(f'单个K线数据的信息数量<9，请检查格式是否发生改变。line={sline}>')
                                return
                            # 通达信导出数据的夜盘日期有错位，提前了一天（如2025.5.14日夜盘数据的日期时间为2025/05/15 2105），需要校正
                            if dataArray[1] > '2100' and dataArray[1] <= '2359':
                                rawDate = datetime.strptime(f'{dataArray[0]} 0000', '%Y/%m/%d %H%M')
                                newDate = getLastTradeDate2(symbol, rawDate, allTradeDates)
                                if not newDate:  # 为null可能是因为数据库没找到比其更早的日线数据，可忽略
                                    continue
                                dataArray[0] = newDate.strftime('%Y/%m/%d')
                            dt = datetime.strptime(f'{dataArray[0]} {dataArray[1]}', '%Y/%m/%d %H%M') - \
                                 INTERVAL_DELTA_MAP[interval]  # 取K线的起始时间（通达信导出的K线时间是结束时间）
                            bar: BarData = BarData(
                                symbol=symbol,
                                exchange=exchange,
                                interval=interval,
                                datetime=dt,
                                open_price=round_to(dataArray[2], 0.000001),
                                high_price=round_to(dataArray[3], 0.000001),
                                low_price=round_to(dataArray[4], 0.000001),
                                close_price=round_to(dataArray[5], 0.000001),
                                volume=dataArray[6],
                                turnover=0,
                                open_interest=dataArray[7],
                                gateway_name="tdx"
                            )
                        barDataList.append(bar)
            printInfo(f'>>[{symbol}] done')

            if not database:
                database = get_database()
            if database.save_bar_data(barDataList):
                printInfo(f'>>[{symbol}] save to DB successfully')
            else:
                printInfo(f'>>[{symbol}] save to DB failed')


def startWithDigit(str):
    if re.match(r'^\d', str):
        return True
    else:
        return False


def getExchange(marketTag: str):
    """通达信导出的K线文件名开头是其定义的市场号码，需要转换为vnpy的格式"""
    if marketTag == '28':
        return Exchange.CZCE
    elif marketTag == '29':
        return Exchange.DCE
    elif marketTag == '30':
        return Exchange.SHFE
    elif marketTag == '66':
        return Exchange.GFEX


def getLastTradeDate(symbol, exchange, dateOrDatetime: datetime):
    """获取上一个交易日（返回类型是datetime.datetime）。读取本地数据库。dateOrDatetime要求时分秒为00:00:00"""
    database = get_database()
    bars: list[BarData] = database.load_bar_data(symbol, exchange, Interval.DAILY,
                                                 dateOrDatetime - 30 * INTERVAL_DELTA_MAP[Interval.DAILY],
                                                 dateOrDatetime)
    if bars:
        return bars[-1].datetime


def getLastTradeDate2(symbol, date: datetime, allTradeDates: list[datetime]):
    """获取上一个交易日（返回类型是datetime.datetime）。date要求时分秒为00:00:00"""
    if date and allTradeDates:
        date = date.replace(tzinfo=pytz.UTC)
        matchedTradeDates = [td for td in allTradeDates if td < date]
        if matchedTradeDates:
            return matchedTradeDates[-1]


def getAllTradeDate(symbol, exchange, startDate, endDate) -> list[datetime]:
    """获取所有交易日。读取本地数据库。"""
    database = get_database()
    bars: list[BarData] = database.load_bar_data(symbol, exchange, Interval.DAILY, startDate, endDate)
    if bars:
        return [bar.datetime for bar in bars]


def printInfo(msg: str):
    print(f'[{datetime.now()}] {msg}')


def findFirstPos(date: datetime, allDates: list[datetime]) -> int:
    """查找列表allDates中首个大于等于date的位置"""
    if date and allDates:
        for i in range(len(allDates)):
            if allDates[i] >= date:
                return i
    else:
        print(r'***请检查参数')


def dateFormat(date: datetime) -> str:
    return date.strftime('%Y-%m-%d')


def getRealTradeDatetime(allTradeDates: list[datetime], index: int, openOrClose: int = 0) -> datetime:
    """获取真实交易日期时间。因为一个交易日是从前一个交易日晚上的夜盘开始，如遇到节假日的情况，交易日的开始是当天的日盘。
    参数说明：openOrClose取值0、1，0表示开盘，1表示收盘"""
    if allTradeDates and index >= 0 and index < len(allTradeDates):
        if openOrClose == 0:
            return allTradeDates[index - 1].replace(hour=21, minute=0, second=0, microsecond=0) if index > 0 \
                else allTradeDates[index].replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            return allTradeDates[index].replace(hour=15, minute=0, second=0, microsecond=0)


if __name__ == "__main__":
    """"""
    t0 = datetime.now()

    # 回测测试
    # doTestBacktesting()

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
    trainDay = 240
    testDay = 120
    # doTestDynamicOptimization(datetime(2024, 1, 1, tzinfo=pytz.UTC),
    #                           datetime(2025, 5, 31, tzinfo=pytz.UTC), trainDay, testDay)

    # 导数据
    # importHistoryDataFromTxt(r'D:\Weo\通达信导出K线数据\期货\5分钟K线\txt格式', Interval.MINUTE5, encoding='gb2312')
    # importHistoryDataFromTxt(r'D:\Weo\通达信导出K线数据\期货\日K线\txt格式', Interval.DAILY, encoding='gb2312')

    t1 = datetime.now()
    print(f'\n>>>>>>总耗时{t1 - t0}s')