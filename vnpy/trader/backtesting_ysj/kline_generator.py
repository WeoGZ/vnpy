from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine
from urllib import parse

from vnpy.trader.common_util import getAllTradeDate, getExchange, startWithDigit, printInfo, getLastTradeDate2
from vnpy.trader.constant import *
from vnpy.trader.database import get_database, BaseDatabase
from vnpy.trader.object import BarData
from vnpy.trader.utility import round_to


def generate(start_date: datetime, end_date: datetime, new_interval: int, symbols: list = None):
    """用5分钟K线合成新周期K线"""
    if new_interval not in [15, 30, 60, 120]:
        print(f'*****interval should be in [15, 30, 60, 120]')
        return

    # 新周期K线所包含5分钟K线的数量
    num_per_new_kline = new_interval / 5

    # 商品期货K线周期每根K线的结束时间
    tradeTimeList = TRADE_TIME_DAYTIME_15M
    if new_interval == 300:
        tradeTimeList = TRADE_TIME_DAYTIME_30M
    elif new_interval == 60:
        tradeTimeList = TRADE_TIME_DAYTIME_1H
    elif new_interval == 120:
        tradeTimeList = TRADE_TIME_DAYTIME_2H

    db_engine = create_engine('mysql+pymysql://root:%s@localhost:3306/vnpy' % parse.quote_plus('admin'))
    query_symbols_sql = "SELECT DISTINCT symbol FROM `dbbardata` ORDER BY symbol;"
    df_symbols = symbols
    if df_symbols is None:
        df_symbols = pd.read_sql_query(query_symbols_sql, db_engine)
    if df_symbols is not None and not df_symbols.empty:
        for symbol in df_symbols['symbol']:
            query_kline_sql = "SELECT * FROM `dbbardata` WHERE symbol='%s' and `interval`='5m' and datetime>='%s' \
                and datetime<='%s' ORDER BY datetime;" % (symbol, start_date.strftime('%Y-%m-%d %H:%M:%S'),
                                                          end_date.strftime('%Y-%m-%d %H:%M:%S'))
            df_klines_5m = pd.read_sql_query(query_kline_sql, db_engine)
            if not df_klines_5m.empty:
                table_columns = ['symbol', 'exchange', 'datetime', 'interval', 'volume', 'turnover', 'open_interest',
                                 'open_price', 'high_price', 'low_price', 'close_price']
                # new_klines: dict[str, list] = {key: [] for key in table_columns}
                new_klines: list[BarData] = []
                bar: BarData = None
                kline_5m_count = 0

                for i in df_klines_5m.index:
                    kl = df_klines_5m.loc[i]
                    dt = kl['datetime']
                    if bar is None:
                        bar = BarData(symbol=kl[table_columns[0]],
                                      exchange=kl[table_columns[1]],
                                      interval=None,
                                      datetime=dt,
                                      open_price=round_to(kl[table_columns[7]], 0.000001),
                                      high_price=round_to(kl[table_columns[8]], 0.000001),
                                      low_price=round_to(kl[table_columns[9]], 0.000001),
                                      close_price=round_to(kl[table_columns[10]], 0.000001),
                                      volume=kl[table_columns[4]],
                                      turnover=kl[table_columns[5]],
                                      open_interest=kl[table_columns[6]],  # 持仓量
                                      gateway_name="tdx"
                                      )
                    else:
                        bar.high_price = max(bar.high_price, round_to(kl[table_columns[8]], 0.000001))
                        bar.low_price = min(bar.low_price, round_to(kl[table_columns[9]], 0.000001))
                        bar.close_price = round_to(kl[table_columns[10]], 0.000001)
                        bar.volume += kl[table_columns[4]]
                        bar.turnover += kl[table_columns[5]]
                        bar.open_interest = kl[table_columns[6]]

                    kline_5m_count += 1
                    nextBarTime = bar.datetime + INTERVAL_DELTA_MAP[Interval.MINUTE5]
                    if nextBarTime.hour == tradetimeTuple[0] and nextBarTime.minute == tradetimeTuple[1]:
                        if kline_5m_count == num_per_new_kline:  # 子K线数量满足条件的才记录
                            new_klines.append(bar)

                        bar = None
                        kline_5m_count = 0

                # 转换
                new_klines_dict = [{} for nk in new_klines]
                new_klines_df = pd.DataFrame()

def bardata_to_dict(bar: BarData):
    table_columns = ['symbol', 'exchange', 'datetime', 'interval', 'volume', 'turnover', 'open_interest',
                     'open_price', 'high_price', 'low_price', 'close_price']
    if bar is not None:
        return {table_columns[0]: bar.symbol, table_columns[1]: bar.exchange, table_columns[7]: bar.datetime,}



if __name__ == "__main__":
    """"""
    t0 = datetime.now()

    startDate = datetime(2023, 1, 1)
    endDate = datetime(2023, 12, 31)
    generate(startDate, endDate, 60)

    t1 = datetime.now()
    print(f'\n>>>>>>总耗时{t1 - t0}s')
