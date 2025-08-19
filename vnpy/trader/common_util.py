import re

import pytz
from datetime import datetime, timedelta

from vnpy.trader.database import BaseDatabase, get_database
from vnpy.trader.object import TickData, BarData
from vnpy.trader.constant import Exchange, Interval, INTERVAL_DELTA_MAP


def getAllTradeDate(symbol, exchange, startDate, endDate) -> list[datetime]:
    """获取所有交易日。读取本地数据库。"""
    database = get_database()
    bars: list[BarData] = database.load_bar_data(symbol, exchange, Interval.DAILY, startDate, endDate)
    if bars:
        return [bar.datetime for bar in bars]


def getNextTradeDate(date: datetime, allTradeDates: list[datetime]):
    """获取上一个交易日（返回类型是datetime.datetime）。date要求时分秒为00:00:00"""
    if date and allTradeDates:
        date = date.replace(tzinfo=pytz.UTC)
        matchedTradeDates = [td for td in allTradeDates if td > date]
        if matchedTradeDates:
            return matchedTradeDates[0]


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
