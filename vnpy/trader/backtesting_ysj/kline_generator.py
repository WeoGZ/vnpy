from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine
from urllib import parse

from vnpy.trader.common_util import getAllTradeDate, getExchange, startWithDigit, printInfo, getLastTradeDate2
from vnpy.trader.constant import *
from vnpy.trader.database import get_database, BaseDatabase
from vnpy.trader.object import BarData
from vnpy.trader.utility import round_to


# 15分钟K线结束时间
TRADE_TIME_15M: list[tuple] = [(9, 15), (9, 30), (9, 45), (10, 0), (10, 15), (10, 45), (11, 0), (11, 15), (11, 30),
                               (13, 45), (14, 0), (14, 15), (14, 30), (14, 45), (15, 0), (21, 15), (21, 30), (21, 45),
                               (22, 0), (22, 15), (22, 30), (22, 45), (23, 0)]
# 30分钟K线结束时间
TRADE_TIME_30M: list[tuple] = [(9, 30), (10, 0), (10, 45), (11, 15), (13, 45), (14, 15), (14, 45), (15, 0), (21, 30),
                               (22, 0), (22, 30), (23, 0)]
# 60分钟K线结束时间
TRADE_TIME_60M: list[tuple] = [(10, 0), (11, 15), (14, 15), (15, 0), (22, 0), (23, 0)]
# 120分钟K线结束时间
TRADE_TIME_120M: list[tuple] = [(11, 15), (15, 0), (23, 0)]

def generate(start_date: datetime, end_date: datetime, new_interval: int, symbols: list = None):
    """用5分钟K线合成新周期K线（新周期仅限分钟级别）"""
    if new_interval not in [15, 30, 60, 120]:
        print(f'*****interval should be in [15, 30, 60, 120]')
        return

    # 商品期货K线周期每根K线的结束时间
    tradeTimeList = TRADE_TIME_15M
    if new_interval == 30:
        tradeTimeList = TRADE_TIME_30M
    elif new_interval == 60:
        tradeTimeList = TRADE_TIME_60M
    elif new_interval == 120:
        tradeTimeList = TRADE_TIME_120M

    db_engine = create_engine('mysql+pymysql://root:%s@localhost:3306/vnpy' % parse.quote_plus('admin'))
    df_symbols = symbols
    if df_symbols is None:
        query_symbols_sql = "SELECT DISTINCT symbol FROM `dbbardata` ORDER BY symbol;"
        df_symbols = pd.read_sql_query(query_symbols_sql, db_engine)['symbol'].tolist()
    if df_symbols is not None and len(df_symbols) > 0:
        print(f'>>待合成K线的标的数量={len(df_symbols)}')
        for symbol in df_symbols:
            query_kline_sql = "SELECT * FROM `dbbardata` WHERE symbol='%s' and `interval`='5m' and datetime>='%s' \
                and datetime<='%s' ORDER BY datetime;" % (symbol, start_date.strftime('%Y-%m-%d %H:%M:%S'),
                                                          end_date.strftime('%Y-%m-%d %H:%M:%S'))
            df_klines_5m = pd.read_sql_query(query_kline_sql, db_engine)
            if not df_klines_5m.empty:
                print(f'>>symbol={symbol}, df_klines_5m.len={len(df_klines_5m)}')
                table_columns = ['symbol', 'exchange', 'datetime', 'interval', 'volume', 'turnover', 'open_interest',
                                 'open_price', 'high_price', 'low_price', 'close_price']
                new_klines: list[dict] = []
                bar: dict = None
                kline_5m_count = 0

                for i in df_klines_5m.index:
                    kl = df_klines_5m.loc[i]
                    dt = kl['datetime']
                    if bar is None:
                        values = [kl[table_columns[0]], kl[table_columns[1]], kl[table_columns[2]], f'{new_interval}m',
                                  kl[table_columns[4]], kl[table_columns[5]], kl[table_columns[6]],
                                  kl[table_columns[7]],
                                  kl[table_columns[8]], kl[table_columns[9]], kl[table_columns[10]]]
                        bar = dict(zip(table_columns, values))
                    else:
                        bar['high_price'] = max(bar['high_price'], kl[table_columns[8]])
                        bar['low_price'] = min(bar['low_price'], kl[table_columns[9]])
                        bar['close_price'] = kl[table_columns[10]]
                        bar['volume'] += kl[table_columns[4]]
                        bar['turnover'] += kl[table_columns[5]]
                        bar['open_interest'] = kl[table_columns[6]]

                    kline_5m_count += 1
                    nextBarTime = dt + INTERVAL_DELTA_MAP[Interval.MINUTE5]
                    for tradetimeTuple in tradeTimeList:
                        if nextBarTime.hour == tradetimeTuple[0] and nextBarTime.minute == tradetimeTuple[1]:
                            new_klines.append(bar)

                            bar = None
                            kline_5m_count = 0

                # 转换
                new_klines_df = pd.DataFrame(new_klines)
                new_klines_df.to_sql('dbbardata', db_engine, if_exists='append', index=False)


if __name__ == "__main__":
    """"""
    t0 = datetime.now()

    startDate = datetime(2016, 1, 1, 9, 0, 0)
    endDate = datetime(2025, 5, 14, 15, 0, 0)
    generate(startDate, endDate, 30)

    t1 = datetime.now()
    print(f'\n>>>>>>总耗时{t1 - t0}s')
