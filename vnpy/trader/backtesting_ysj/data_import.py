import os
from datetime import datetime

from vnpy.trader.common_util import getAllTradeDate, getExchange, startWithDigit, printInfo, getLastTradeDate2
from vnpy.trader.constant import INTERVAL_DELTA_MAP, Exchange, Interval
from vnpy.trader.database import get_database, BaseDatabase
from vnpy.trader.object import BarData
from vnpy.trader.utility import round_to


def importHistoryDataFromTxt(directory, interval, encoding='utf-8', specified_symbols: list = None):
    '''指定目錄下文件編碼類型。specified_symbols：目录下指定的标的，只导入这些标的K线数据'''
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
            if specified_symbols is not None:
                if symbol not in specified_symbols:
                    print(f'###{symbol}不是指定的标的范围，跳过')
                    continue
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


if __name__ == "__main__":
    """
    #################################################################################################################
    注意：
    1.文件必须是通达信导出的txt文件（行情界面输入“34”——高级导出——日线、5分钟线各导一次，而且导出前需要先在“盘后数据下载”下载扩展市场行情）
    2.执行此程序前，要先将object.py的BarData类的close_datetime属性注释掉（定制的属性），否则会报错；事后要恢复，否则策略回测等逻辑会报错
    3.先导入日线数据，再导入5分钟数据，否则没有夜盘数据（因为导入5分钟数据时需要读取日线数据来获取交易日日期）
    #################################################################################################################
    """
    t0 = datetime.now()

    # 导数据
    importHistoryDataFromTxt(r'D:\Weo\通达信导出K线数据\期货\5分钟K线\txt格式_更新至20251219', Interval.MINUTE5, encoding='gb2312')
    # importHistoryDataFromTxt(r'D:\Weo\通达信导出K线数据\期货\5分钟K线\txt格式', Interval.MINUTE5, encoding='gb2312')
    # importHistoryDataFromTxt(r'D:\Weo\通达信导出K线数据\期货\日K线\txt格式_更新至20251219', Interval.DAILY, encoding='gb2312')

    t1 = datetime.now()
    print(f'\n>>>>>>总耗时{t1 - t0}s')
