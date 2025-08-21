import calendar
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import create_engine
from urllib import parse

from vnpy.trader.backtesting_ysj.optimization_test import doTestBfOptimization
from vnpy.trader.optimize import OptimizationSetting
from vnpy_ctastrategy.strategies import w_s12_strategy
from vnpy.trader.backtesting_ysj.backtesting_test import PeriodType
from vnpy.trader.constant import Interval, IntervalUnit
from vnpy.trader.common_util import *


def prepare_data_1(period: PeriodType, start_date: datetime, end_date: datetime, strategy_class, symbol, exchange, rate,
                   slippage, size, pricetick, capital, interval: int, interval_unit: IntervalUnit,
                   optSetting: OptimizationSetting):
    end_date = end_date.replace(hour=15, minute=0, second=0, microsecond=0)
    _end_date = start_date
    if period == PeriodType.Quarter:
        _end_date = get_quarter_end_date(start_date)

    while _end_date <= end_date:
        _startDate = _end_date.replace(year=_end_date.year - 1, hour=9, minute=0, second=0, microsecond=0) + timedelta(
            days=1)
        printInfo(f'【{_startDate.strftime("%Y-%m-%d")}~{_end_date.strftime("%Y-%m-%d")}】')
        opt_results = doTestBfOptimization(strategy_class, symbol, exchange, _startDate, _end_date, rate, slippage,
                                           size, pricetick, capital, interval, optSetting)
        save_to_db(opt_results[:20], strategy_class, f'{symbol}.{exchange}', f'{interval}{interval_unit.value}',
                   _startDate, _end_date, optSetting.target_name, '', datetime.now())
        _end_date = get_quarter_end_date(_end_date + timedelta(days=1))


def get_quarter_end_date(d: datetime):
    """获取季度末的日期"""
    month = d.month
    quarter_end_month = 3
    if 3 < month <= 6:
        quarter_end_month = 6
    elif 6 < month <= 9:
        quarter_end_month = 9
    elif 9 < month <= 12:
        quarter_end_month = 12

    _, num_of_month = calendar.monthrange(d.year, quarter_end_month)

    return datetime(d.year, quarter_end_month, num_of_month, 15, 0, 0, 0)


def save_to_db(results: list, strategy_class, vt_symbol, interval: str, start_date: datetime, end_date: datetime,
               target: str, remark: str, generate_datetime: datetime):
    """写入数据库"""
    # db_engine = create_engine('mysql+pymysql://ucnotkline:%s@192.168.2.205:3306/fitlab_data' % parse.unquote_plus('ucnotkline@205'))
    db_engine = create_engine('mysql+pymysql://root:%s@localhost:3306/vnpy' % parse.unquote_plus('admin'))

    table_columns = ['strategy', 'vt_symbol', 'period', 'start_date', 'end_date', 'target', 'target_value', 'params',
                     'remark', 'generate_datetime']
    data_dict = {key: [] for key in table_columns}
    data_dict[table_columns[0]] = [strategy_class.__name__] * len(results)
    data_dict[table_columns[1]] = [vt_symbol] * len(results)
    data_dict[table_columns[2]] = [interval] * len(results)
    data_dict[table_columns[3]] = [start_date] * len(results)
    data_dict[table_columns[4]] = [end_date] * len(results)
    data_dict[table_columns[5]] = [target] * len(results)
    data_dict[table_columns[8]] = [remark] * len(results)
    data_dict[table_columns[9]] = [generate_datetime] * len(results)
    for result in results:
        params: dict = result[0]
        target_value = result[1]
        data_dict[table_columns[6]].append(target_value)
        data_dict[table_columns[7]].append(str(params))
    df = pd.DataFrame.from_dict(data_dict)
    df.to_sql('optimization_data', db_engine, if_exists='append', index=False)


if __name__ == "__main__":
    """"""
    t0 = datetime.now()

    startDate = datetime(2024, 1, 1)
    endDate = datetime(2024, 12, 31)
    optSetting = OptimizationSetting()
    optSetting.set_target("sharpe_ratio")
    optSetting.add_parameter("len", 20, 40, 10)
    optSetting.add_parameter("stpr", 15, 25, 5)
    optSetting.add_parameter("n", 20, 40, 10)
    prepare_data_1(PeriodType.Quarter, startDate, endDate, w_s12_strategy.WS12Strategy, 'RBL9', 'SHFE',
                   0.0002, 1, 10, 1, 15000, 60, IntervalUnit.MINUTE, optSetting)

    t1 = datetime.now()
    print(f'\n>>>>>>总耗时{t1 - t0}s')
