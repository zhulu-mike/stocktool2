# coding=utf-8
from __future__ import print_function, absolute_import
import os
import json

import pandas as pd
from gm.api import *
import requests
import json
import os
from bs4 import BeautifulSoup
import fund_data_processor
import stock_announce_info
import stock_base_info
import stock_announce_processor
import stock_price_processor
from openpyxl import load_workbook
import datetime
from openpyxl.workbook.defined_name import DefinedName
import matplotlib.pyplot as plt
import mplcursors
import numpy as np
import sys
import getopt
from kzz_processor import fetch_all_convert_bonds


#获取新三板股票列表
all_stocks_url = "https://push2.eastmoney.com/api/qt/clist/get?ut=c964af255f56da290419b605978b89db&fltt=1&invt=2&np=1&pn=$PAGE_NUM$&pz=$PAGE_SIZE$&fid=f12&po=1&fs=m%3A0%2Bt%3A81%2Bs%3A!2048&fields=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6%2Cf9%2Cf12%2Cf13%2Cf14%2Cf15%2Cf16%2Cf17%2Cf18%2Cf20%2Cf111%2Cf152%2Cf324&cb=&_=1757771181814"
all_file = "all.json"
root_dir = "stocks/"
base_dir = "base/"
announce_dir = "announce/"
all_a_file = "all_a.json"
all_stocks = {}
all_a_stocks = []
#获取股票的基本信息
stock_info_url = "https://xinsanban.eastmoney.com/F10/CompanyInfo/Introduction/$CODE$.html"
#获取股票的财务数据
stock_finance_url = "https://datacenter.eastmoney.com/securities/api/data/get?type=RPT_F10_FINANCE_MAINFINADATA&sty=APP_F10_MAINFINADATA&quoteColumns=&filter=(SECUCODE%3D%22$STOCK_CODE$%22)&p=1&ps=200&sr=-1&st=REPORT_DATE&source=HSF10&client=PC&v=022747256953180262"
#获取股票的公告
stock_announce_url = "https://np-anotice-stock.eastmoney.com/api/security/ann?cb=&sr=-1&page_size=100&page_index=$PAGE_INDEX$&ann_type=A&client_source=web&stock_list=000951&f_node=0&s_node=0"
#获取股票某个公告的具体内容
stock_announce_detail_url = "https://pdf.dfcfw.com/pdf/H2_$ART_CODE$_1.pdf"
#获取某个基金的历史净值
fund_net_value_url = "https://api.fund.eastmoney.com/f10/lsjz?callback=&fundCode=$FUND$&pageIndex=$PAGE$&pageSize=20&startDate=$START$&endDate=&_=1760357946011"
#存储股票公告信息
all_stocks_announce = {}

if sys.argv[1:] and sys.argv[1:][0].find("--")<0:
    arg_flag = int(sys.argv[1:][0]) if len(sys.argv) > 1 else -1
else:
    arg_flag = -1

# 策略中必须有init方法
def init(context):
    update_flag = False
    load_local_all()
    #update_flag = load_remote_all()
    if update_flag:
        updateAll()
    #UpdateBaseInfo()
    #fund_p = fund_data_processor.FundDataProcessor(fund_net_value_url)
    #fund_p.process()
    loadAllA()
    #load_all_announcements()
    update_ann=0
    if update_ann == 1:
        UpdateAllStockAnnounce(True)
        return
    #searchHaveChangeMainFolder()
    #searchChongZheng("2024-01-01", "2024-12-31")
    #return
    context.stock_price_processor = stock_price_processor.StockPirceProcessor()
    flag = 9 if arg_flag == -1 else arg_flag
    print("flag=", flag)
    need_cz = True
    need_daily = False
    need_tuishi = False
    next_year = 1
    count = 6
    start_year = 2025
    if flag ==0:
        timer(timer_func=ontimer_3, period=5000, start_delay=10000)
    elif flag==1:
        for i in range(count):
            searcReallyTuiShiProxy(start_year+i, need_cz=need_cz, 
                                   need_daily=need_daily,
                                   need_tuishi=need_tuishi,
                                   price_end=str(start_year+i+next_year)+"-04-30",
                                   price_start=str(start_year+i+next_year)+"-01-01")
    elif flag==2:
        for i in range(count):
            searcReallyTuiShiProxy(start_year+i, need_cz=need_cz, 
                                   need_daily=need_daily,
                                   need_tuishi=need_tuishi,
                                   price_end=str(start_year+i+next_year)+"-12-31",
                                   price_start=None)
    elif flag==3:
        searcTuiShiProxy(2024)
    elif flag==4:
        for i in range(count):
            searcCZProxy(start_year+i, need_daily=need_daily)
    elif flag==5:
        for i in range(count):
            searcOther2Proxy(start_year+i)
    elif flag==6:
        searchWPG()
    elif flag==7:
        kzzzg()
    elif flag==8:
        calculate_price_profit("2024-09-20", "2026-03-20")
    elif flag==9:
        etfFill()
    elif flag==10:
        time_orders = [
            [
                ["2021-01-21", "2021-02-08", "牛中杀跌"],
                ["2021-02-08", "2021-02-22", "牛中反弹"],
            ],
            [
                ["2021-09-15", "2021-10-12", "牛尾杀跌"],
                ["2021-10-12", "2021-11-30", "牛尾反弹"],
            ],
            [
                ["2021-12-10", "2022-01-28", "牛转熊首次杀跌"],
                ["2022-01-28", "2022-02-18", "首杀反弹"],
            ],
            [
                ["2022-03-02", "2022-03-15", "牛转熊二次杀跌"],
                ["2022-03-15", "2022-03-22", "二杀反弹"],
            ],
            [
                ["2022-03-22", "2022-04-26", "牛转熊三次杀跌"],
                ["2022-04-26", "2022-06-27", "三杀反弹"],
            ],
            [
                ["2022-06-27", "2022-10-11", "牛转熊四次杀跌"],
                ["2022-10-11", "2022-10-17", "四杀反弹"],
            ],
            [
                ["2022-10-17", "2022-10-31", "牛转熊五次杀跌"],
                ["2022-10-31", "2022-12-05", "五杀反弹"],
            ],
            [
                ["2024-01-03", "2024-01-22", "熊尾一杀"],
                ["2024-01-22", "2024-01-25", "熊尾一杀反弹"],
            ],
            [
                ["2024-01-25", "2024-02-05", "熊尾二杀"],
                ["2024-02-05", "2024-02-22", "熊尾二杀反弹"],
            ],
            [
                ["2024-12-30", "2025-01-13", "牛中调整"],
                ["2025-01-13", "2025-02-27", "反弹"],
            ],
            [
                ["2026-03-11", "2026-03-23", "牛中调整"],
                ["2026-03-23", "2026-04-22", "反弹"],
            ],
        ]
        group_range = [-50, -40, -30, -20, 0, 20, 50, 100, 200, 100000]
        calculate_market_profit(time_orders, group_range, flag)
    elif flag==11:
        time_orders = [
            [
                ["2025-12-16", "2025-12-17", "反弹首日"],
                ["2025-12-17", "2025-12-31", "反弹后续"],
            ],
            [
                ["2025-12-16", "2025-12-31", "反弹区间"],
            ],
            [
                ["2026-03-23", "2026-03-24", "反弹首日"],
                ["2026-03-24", "2026-04-22", "反弹后续"],
                ["2026-03-23", "2026-04-22", "带止损反弹", True],
            ],
            [
                ["2026-04-01", "2026-04-30", "反弹区间"],
            ],
        ]
        group_range = [-10,-5,0,1.7,3,5,8,10,40]
        calculate_market_profit(time_orders, group_range, flag)
    elif flag==12:
        time_orders = [
            [
                ["2019-01-04", "2022-01-28", "牛转熊首次杀跌"],
                ["2022-01-28", "2022-02-18", "首杀反弹"],
            ],
            [
                ["2019-01-04", "2022-03-15", "牛转熊二次杀跌"],
                ["2022-03-15", "2022-03-22", "二杀反弹"],
            ],
            [
                ["2019-01-04", "2022-04-26", "牛转熊三次杀跌"],
                ["2022-04-26", "2022-06-27", "三杀反弹"],
            ],
            [
                ["2019-01-04", "2022-10-11", "牛转熊四次杀跌"],
                ["2022-10-11", "2022-10-17", "四杀反弹"],
            ],
            [
                ["2019-01-04", "2022-10-31", "牛转熊五次杀跌"],
                ["2022-10-31", "2022-12-05", "五杀反弹"],
            ],
            [
                ["2019-01-04", "2024-01-22", "熊尾一杀"],
                ["2024-01-22", "2024-01-25", "熊尾一杀反弹"],
            ],
            [
                ["2019-01-04", "2024-02-05", "熊尾二杀"],
                ["2024-02-05", "2024-02-22", "熊尾二杀反弹"],
            ],
            [
                ["2024-09-24", "2025-01-13", "牛中调整"],
                ["2025-01-13", "2025-02-27", "反弹"],
            ],
            [
                ["2024-09-24", "2026-03-23", "牛中调整"],
                ["2026-03-23", "2026-04-22", "反弹"],
            ],
        ]
        group_range = [-80, -70,-60,-50, -40, -30, -20, 0, 20, 50, 100, 200, 100000]
        calculate_market_profit(time_orders, group_range, flag)
    elif flag==13:
        time_orders = [
            [
                ["2022-01-28", "2022-02-18", "首杀反弹","2021-12-10", "2022-01-28"],
            ],
            [
                ["2022-03-15", "2022-03-22", "二杀反弹","2022-03-02", "2022-03-15"],
            ],
            [
                ["2022-04-26", "2022-06-27", "三杀反弹","2022-03-22", "2022-04-26"],
            ],
            [
                ["2022-10-11", "2022-10-17", "四杀反弹","2022-06-27", "2022-10-11"],
            ],
            [
                ["2022-10-31", "2022-12-05", "五杀反弹","2022-10-17", "2022-10-31"],
            ],
            [
                ["2024-01-22", "2024-01-25", "熊尾一杀反弹","2024-01-03", "2024-01-22"],
            ],
            [
                ["2024-02-05", "2024-02-22", "熊尾二杀反弹","2024-01-25", "2024-02-05"],
            ],
            [
                ["2025-01-13", "2025-02-27", "反弹","2024-12-30", "2025-01-13"],
            ],
            [
                ["2026-03-23", "2026-04-22", "反弹","2026-03-11", "2026-03-23"],
            ],
        ]
        group_range = [-50, -40, -30, -20, 0, 5, 10, 15, 20, 25, 30, 50, 100, 200, 100000]
        calculate_market_profit(time_orders, group_range, flag)
    elif flag==20:
        time_orders = [
            ["2024-09-23", "2024-10-08", "第一波"],
            ["2024-10-08", "2025-04-07", "第一波横盘"],
            ["2025-04-07", "2025-08-25", "第二波"],
            ["2025-08-25", "2025-12-16", "第二波横盘"],
            ["2025-12-16", "2026-01-12", "第三波"],
            ["2026-01-12", "2026-03-12", "第三波横盘"],
            ["2026-03-12", "2026-03-23", "第三波下跌"],
            ["2026-03-23", "2026-04-30", "第四波"],

        ]
        calculate_etf_profit(time_orders)
    elif flag==21:
        start_date = "2026-03-31"
        end_date = "2026-04-30"
        plot_etf_cumulative_profit(start_date, end_date)
    elif flag==22:
        start_date = "2026-03-11"
        end_date = "2026-03-23"
        plot_etf_cumulative_profit(start_date, end_date)
    elif flag==23:
        processor = stock_price_processor.StockPirceProcessor()
        processor.update_kzz_with_market_data()
    elif flag==100:
        output = fetch_all_convert_bonds()
        print(output)
    elif flag==2025:
        time_orders = [
            [
                ["2024-09-23", "2025-11-11", "牛市前半段"],
                ["2025-11-11", "2025-12-16", "牛市中期调整"],
                ["2025-12-16", "2026-03-02", "调整后反弹"],
                ["2026-03-02", "2026-03-23", "新高后调整"],
                ["2026-03-23", "2026-04-22", "反弹"],
                ["2025-11-11", "2026-05-19", "牛市后期"],
            ],
            [
                ["2024-09-23", "2025-08-25", "牛市前半段"],
                ["2025-08-25", "2026-04-22", "牛市后期"],
            ],
            [
                ["2024-09-23", "2025-09-01", "牛市前期"],
            ],
            [
                ["2025-09-01", "2026-04-22", "牛市后期"],
            ],
            [
                ["2025-09-01", "2025-12-17", "牛市中期横盘"],
            ],
            [
                ["2025-12-16", "2025-12-31", "年末上升成交量持平"],
            ],
            [
                ["2025-12-31", "2026-01-12", "年末上升2成交量放大"],
            ],
            [
                ["2026-01-12", "2026-02-26", "年末上升后横盘"],
            ],
            [
                ["2022-12-30", "2023-12-29", "2023熊市横盘"],
            ]
        ]
        calculate_market_profit(time_orders, flag=flag)
    elif flag==2021:
        time_orders = [
            [
                ["2019-01-03", "2021-12-10", "牛市前半段"],
                ["2021-12-10", "2022-03-15", "牛转熊杀跌"],
                ["2022-03-15", "2022-04-26", "牛转熊再杀跌"],
                ["2022-04-26", "2022-07-04", "反弹"],
                ["2022-07-04", "2022-10-31", "反弹后的下杀"],
                ["2022-10-31", "2022-12-30", "再次反弹"],
                ["2022-12-30", "2023-12-29", "熊市横盘"],
                ["2023-12-29", "2024-02-05", "熊市后期加速杀跌"],
                ["2024-02-05", "2024-03-19", "熊市反弹"],
                ["2021-12-10", "2024-02-02", "牛市结束后全"],
                ["2024-02-02", "2026-04-22", "下轮牛市"],
            ]
        ]
        calculate_market_profit(time_orders, flag=flag)
    elif flag==2020:
        time_orders = [
            [
                ["2019-01-03", "2020-07-13", "牛市前半段"],
                ["2020-07-13", "2020-12-29", "牛市中间调整"],
                ["2020-12-29", "2021-02-18", "牛市中途新高"],
                ["2021-02-18", "2021-03-09", "牛市新高后杀跌"],
                ["2021-03-09", "2021-12-10", "牛市后半段横盘"],
                ["2021-12-10", "2022-03-15", "牛转熊杀跌"],
                ["2022-03-15", "2022-04-26", "牛转熊再杀跌"],
                ["2022-04-26", "2022-07-04", "反弹"],
                ["2022-07-04", "2022-10-31", "反弹后的下杀"],
                ["2022-10-31", "2022-12-30", "再次反弹"],
                ["2022-12-30", "2023-12-29", "熊市横盘"],
                ["2023-12-29", "2024-02-05", "熊市后期加速杀跌"],
                ["2024-02-05", "2024-03-19", "熊市反弹"],
                ["2021-12-10", "2024-02-02", "牛市结束后全"],
                ["2024-02-02", "2026-04-22", "下轮牛市"],
            ]
        ]
        calculate_market_profit(time_orders, flag=flag)
    elif flag==2016:
        time_orders = [
            [
                ["2012-12-03", "2015-02-09", "牛市前半段"],
                ["2015-02-09", "2015-05-30", "最后主升浪"],
            ],
            [
                ["2012-12-03", "2015-05-30", "牛市前半段"],
                ["2015-05-30", "2015-08-26", "熊市阴跌"],
            ],
            [
                ["2012-12-03", "2014-11-27", "牛市前半段"],
            ],
            [
                ["2014-11-27", "2015-05-30", "牛市前半段"],
            ],
            [
                ["2014-06-25", "2015-05-30", "牛市前半段"],
            ],
            [
                ["2016-01-06", "2018-01-25", "牛市前半段"],
                ["2018-01-25", "2019-01-02", "熊市阴跌"],
            ]
        ]
        group_range = [-50, -20, 0, 20, 50, 100, 200, 300, 500, 100000]
        calculate_market_profit(time_orders, group_range, flag=flag)


def ontimer_3(context):
    #超过15点10分后后不再更新
    if datetime.datetime.now().hour >= 15 and datetime.datetime.now().minute >= 10:
        return
    processor = context.stock_price_processor
    processor.update_kzz_with_market_data()
def kzzzg():
    bonds = [118049,123251,123176,118063,127042,113045,123256,113575,111023,127080,127038,118062,113687,118057,118048,111012,123263,123182,118052,127071,110074,118054,123255,118055,113644,118058,113677,127070,123241,123262,113651,113646,118039,123118,118045,123245,123210,118021,111010,127055,123224,113615,113033,113052,128127,113698,113623,118006,123207,113601,110089,123254,123159,123131,113697,123252,113588,123211,118050,113695,118029,123247,123195,113042,113039,110094,118027,118013,127037,118031,118030,118009,123199,123180,123197,123158,113639,123209,127028,113593,118061,123088,118012,128136,118056,118053,123124,113056,123257,118000,113673,111016,123213,110081,118060,127089,123172,118051,110073,127039,123076,111021,123239,118043,110075,118024,113589,110095,123104,113667,127109,127084,127104,118004,123160,113672,113659,118040,113696,110092,113069,118034,110085,123235,123128,113691,110067,123236,113053,127092,123065,113699,118059,123260,113616,123064,127108,123107,113655,123246,118038,113654,118025,127067,127045,123109,113058,127066,123187,118042,127022,128137,113046,127103,118016,123061,113062,111000,123261,127061,127079,113048,113043,113051,127049,118011,123259,123215,113652,123222,111015,110090,127064,110093,127026,127040,127053,123188,113692,128142,123264,118003,111018,127056,127018,118007,123216,123119,123221,123150,127082,128101,118033,123242,113574,110086,113059,127076,123085,123146,118008,113640,118022,123108,110087,128129,113676,123173,110099,127047,123225,123157,127016,113678,123178,118041,123155,123114,113584,127025,111013,127110,123183,113605,111004,123243,128125,113049,123091,113653,118036,113656,113686,113666,113643,123054,123258,128141,123149,110098,127027,123189,127031,113649,113632,123196,123071,127085,111002,127030,113661,127090,113037,111019,127105,110070,127093,110077,127072,127054,127102,127041,113681,123059,118018,123133,128108,113054,127088,113067,123237,123194,118035,127024,113625,113671,113647,113636,123198,113633,127094,123220,113627,113693]
    symbols = []
    for bond in bonds:
        bsymbol = ""
        if bond > 120000:
            bsymbol = f'SZSE.{bond}'
        else:
            bsymbol = f'SHSE.{bond}'
        ret = get_symbol_infos(sec_type1=1030, sec_type2=103001, symbols=bsymbol)
        symbols.append(ret[0]["underlying_symbol"].split(".")[1])
    print("可转债对应的正股数量=", len(symbols), symbols)

def searchWPG():
    processor = stock_price_processor.StockPirceProcessor()
    avg1 = processor.calculate_wpg("2016-01-04")
    avg2 = processor.calculate_wpg("2016-12-30")
    print("=======2016年微盘股β收益=", f"{avg2/avg1*100-100:.2f}%")
    avg1 = processor.calculate_wpg("2017-01-03")
    avg2 = processor.calculate_wpg("2017-12-29")
    print("=======2017年微盘股β收益=", f"{avg2/avg1*100-100:.2f}%")
    avg1 = processor.calculate_wpg("2018-01-02")
    avg2 = processor.calculate_wpg("2018-12-28")
    print("=======2018年微盘股β收益=", f"{avg2/avg1*100-100:.2f}%")
    avg1 = processor.calculate_wpg("2019-01-02")
    avg2 = processor.calculate_wpg("2019-12-31")
    print("=======2019年微盘股β收益=", f"{avg2/avg1*100-100:.2f}%")
    avg1 = processor.calculate_wpg("2020-01-02")
    avg2 = processor.calculate_wpg("2020-12-31")
    print("=======2020年微盘股β收益=", f"{avg2/avg1*100-100:.2f}%")
    avg1 = processor.calculate_wpg("2021-01-04")
    avg2 = processor.calculate_wpg("2021-12-31")
    print("=======2021年微盘股β收益=", f"{avg2/avg1*100-100:.2f}%")
    avg1 = processor.calculate_wpg("2022-01-04")
    avg2 = processor.calculate_wpg("2022-12-30")
    print("=======2022年微盘股β收益=", f"{avg2/avg1*100-100:.2f}%")
    avg1 = processor.calculate_wpg("2023-01-03")
    avg2 = processor.calculate_wpg("2023-12-29")
    print("=======2023年微盘股β收益=", f"{avg2/avg1*100-100:.2f}%")
    avg1 = processor.calculate_wpg("2024-01-02")
    avg2 = processor.calculate_wpg("2024-12-31")
    print("=======2024年微盘股β收益=", f"{avg2/avg1*100-100:.2f}%")
    avg1 = processor.calculate_wpg("2025-01-02")
    avg2 = processor.calculate_wpg("2025-12-31")
    print("=======2025年微盘股β收益=", f"{avg2/avg1*100-100:.2f}%")
    avg1 = processor.calculate_wpg("2025-12-31")
    avg2 = processor.calculate_wpg("2026-03-20")
    print("=======2026年微盘股β收益=", f"{avg2/avg1*100-100:.2f}%")

def etfFill():
    # 打开 Excel 文件
    file_path = r'D:\\my\\投资\\仓位结构.xlsx'
    wb = load_workbook(file_path)
    
    # ========== 原有的 ETF 涨幅写入逻辑 ==========
    with open('etf.json', 'r', encoding='utf-8') as f:
        etfs = json.load(f)
    processor = stock_price_processor.StockPirceProcessor()
    ret = processor.get_stocks_today_delta(etfs)
    
    # 获取当前日期
    today = datetime.date.today().strftime('%Y%m%d')
    
    # 写入 ETF 涨幅（原逻辑）
    sheet = wb['etf']
    for name in wb.defined_names:
        print(name, wb.defined_names[name].attr_text)
    
    # 找到当前日期对应的行（假设第一列是日期）
    row_num = None
    for row in sheet.iter_rows(min_row=1, max_col=1):
        print(row[0].value)
        if str(row[0].value) == today:
            row_num = row[0].row
            break
    
    if row_num is not None:
        # 从第二列开始依次写入涨幅
        for i, code in enumerate(etfs):
            symbol = processor.get_stock_symbol(code)
            delta = ret.get(symbol, 0)*0.01
            print(f"写入 {symbol} 的涨幅 {delta:.2%} 到 Excel {i+2}列")
            sheet.cell(row=row_num, column=i+2, value=delta)
        #attr = f"'D:\my\投资\可转债\[{today}.xls]{today}'!$C:$L"
        #name = DefinedName(
        #    name="dd",
        #    attr_text=attr  # 引用地址
        #)
        #wb.defined_names.add(name)
        print("ETF 涨幅已写入 Excel")
    else:
        print(f"未找到日期 {today} 对应的行")
    bonds = fetch_all_convert_bonds()
    # ========== 新增的可转债数据写入逻辑 ==========
    sheet_name = '全部可转债'
    # 如果sheet已存在，先删除
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    
    # 重新创建sheet
    sheet = wb.create_sheet(sheet_name)
    
    # 写入表头
    headers = ['债券名称','债券代码', '股票代码', '股票名称', '转股价', '强赎价', '到期价', '下修价', 
               '转股溢价率', '剩余年限', '强赎状态', '最后交易日', '最后转股日', '剩余规模(亿)', '到期日',
               '转债最新价', '转债涨跌幅', '正股最新价', '正股涨跌幅']
    sheet.append(headers)
    
    # 辅助函数：处理价格和涨跌幅的格式化
    def format_value(value, divisor=1):
        """格式化值，返回数字类型"""
        if value is None or value == '':
            return ''
        try:
            # 如果是带百分号的字符串，先去掉百分号
            if isinstance(value, str):
                value = value.replace('%', '')
            num = float(value)
            if divisor != 1:
                num = num / divisor
            return num
        except (ValueError, TypeError):
            return value
    
    # 写入数据
    for bond in bonds:
        row_data = [
            bond.get('bond_name', ''),
            bond.get('bond_id', ''),
            bond.get('stock_id', ''),
            bond.get('stock_name', ''),
            format_value(bond.get('convert_price'), 1),
            format_value(bond.get('force_redeem_price'), 1),
            format_value(bond.get('maturity_price'), 1),
            format_value(bond.get('lowering_trigger_price'), 1),
            format_value(bond.get('premium_rate'), 1),
            format_value(bond.get('year_left'), 1),
            bond.get('force_redeem_status', ''),
            bond.get('last_trade_date', ''),
            bond.get('last_convert_date', ''),
            format_value(bond.get('left_market_value', ''), 1),
            format_value(bond.get('maturity_dt', '').replace('-', ''), 1),
            format_value(bond.get('bond_price'), 1),
            format_value(bond.get('bond_change'), 1),
            format_value(bond.get('stock_price'), 1),
            format_value(bond.get('stock_change'), 1),
        ]
        sheet.append(row_data)
    
    # 保存并关闭
    wb.save(file_path)
    wb.close()
    print(f"可转债数据已写入 Excel，共 {len(bonds)} 条记录")


#统计全市场股票在牛市之后的表现
def calculate_market_profit(time_orders, group_range=None, flag=None):
    processor = stock_price_processor.StockPirceProcessor()
    for to, time_order in enumerate(time_orders):
        outs = {}
        rets = []
        zhishu = {"SHSE.000905": "中证500", "SHSE.000852": "中证1000"}
        zhishu_rets = []
        for i in range(len(time_order)):
            #顺便获取一些指数的同期涨幅，作为对比，中证500和中证1000
            ret = processor.get_stocks_during_delta(list(zhishu.keys()), time_order[i][0], time_order[i][1])
            zhishu_rets.append(ret)

            ret = processor.get_stocks_during_delta(all_a_stocks, time_order[i][0], time_order[i][1])
            rets.append(ret)
        #先对第一个阶段的涨幅进行排序，分成10组，统计每组在后续阶段的表现
        group_range = [-50, -20, 0, 20, 50, 100, 200, 100000] if group_range is None else group_range
        groups = [[] for _ in range(len(group_range))]
        for code in all_a_stocks:
            if code not in rets[0]:
                continue
            delta = rets[0].get(code, 0)
            group = len(group_range)-1
            for i in range(len(group_range)):
                if delta < group_range[i]:
                    group = i
                    break
            groups[group].append(code)
        group_by_str = time_order[0][0]+"-"+time_order[0][1]
        out_path = "out/"
        log_dir = os.path.join(out_path, f"flag{flag}") if flag is not None else out_path
        os.makedirs(log_dir, exist_ok=True)
        #把涨幅最小的股票列表写到文件里方便后面分析
        with open(os.path.join(log_dir, f'final_stocks_min{to}.txt'), 'w', encoding='utf-8') as f:
            f.write(f"涨幅小于{group_range[0]}%的股票列表:\n")
            for code in groups[0]:
                f.write(f"{code}\n")
        with open(os.path.join(log_dir, f'final_stocks_max{to}.txt'), 'w', encoding='utf-8') as f:
            f.write(f"涨幅小于{group_range[-1]}%的股票列表:\n")
            for code in groups[-1]:
                f.write(f"{code}\n")
        final_rets = []
        for i in range(0, len(rets)):

            zhishu_str = "同期中证500涨幅{:.2f}%, 中证1000涨幅{:.2f}%".format(zhishu_rets[i]["SHSE.000905"], zhishu_rets[i]["SHSE.000852"])
            time_str = time_order[i][0]+"~"+time_order[i][1]+"=="+time_order[i][2]
            print("\n\n")
            if i == 0:
                 print(f"首先按{time_order[i][0]}~{time_order[i][1]}======{time_order[i][2]}阶段的涨幅表现进行分组, {zhishu_str}")
            else:
                print(f"对分组股票统计{time_order[i][0]}~{time_order[i][1]}======{time_order[i][2]}阶段的表现, {zhishu_str}")
            print("▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼")
            outs[time_str] = []
            for group in range(len(groups)):
                total_profit = 0
                count = 0
                win_count = 0
                group_stock_data = []
                group_range_str = f"{group_range[group-1]}%~{group_range[group]}%" if group > 0 else f"<{group_range[group]}%"
                for code in groups[group]:
                    if code in rets[i]:
                        total_profit = total_profit + rets[i][code]
                        group_stock_data.append(rets[i][code])
                        count = count + 1
                        if rets[i][code] > 0:
                            win_count = win_count + 1
                        outs[time_str].append(f"{time_str}, 组【{group_range_str}】, {code}, {rets[i][code]:.2f}%")
                avg_profit = total_profit / count if count > 0 else 0
                win_rate = win_count / count if count > 0 else 0
                #再反向求一遍跌幅超过平均值的有多少
                beyond_count = 0
                for zdf in group_stock_data:
                    if zdf > avg_profit:
                        beyond_count = beyond_count + 1
                beyond_count_rate = beyond_count / count if count > 0 else 0
                if count > 0:
                    df = np.array(group_stock_data)
                    fenbu_str = f"10%分位={np.percentile(df, 10):.2f}, 25%分位={np.percentile(df, 25):.2f}, 40%分位={np.percentile(df, 40):.2f}, 50%分位={np.percentile(df, 50):.2f}, 60%分位={np.percentile(df, 60):.2f}, 75%分位={np.percentile(df, 75):.2f}, 90%分位={np.percentile(df, 90):.2f}"
                else:
                    fenbu_str = ""
                #反向求该组股票在前面下跌阶段的涨幅
                backward_str = ""
                if len(time_order[i]) > 4:
                    backward_ret = processor.get_stocks_during_delta(groups[group], time_order[i][3], time_order[i][4])
                    total_backward_profit = sum(backward_ret.values())
                    avg_backward_profit = total_backward_profit / len(backward_ret) if len(backward_ret.items()) > 0 else 0
                    backward_str = f"前期下跌阶段涨幅={avg_backward_profit:.2f}%"
                print(f"{time_order[i][0]}~{time_order[i][1]}阶段，分组涨跌幅【{group_range_str}】的{count}只股票平均涨幅{avg_profit:.2f}%，胜率={win_rate:.2%}, 超过平均涨幅的股票占比={beyond_count_rate:.2%}, {fenbu_str}, {backward_str}")
                print("==============================================")
            if time_order[i][3] if len(time_order[i])>3 else False:
                processor.backtrace_fantan(groups[-1], time_order[i][0], time_order[i][1])
        #保存outs.json
        with open(os.path.join(log_dir, f'outs{to}.json'), 'w', encoding='utf-8') as f:
            json.dump(outs, f, ensure_ascii=False, indent=4)

#计算ETF在指定时间区间的平均涨幅
def calculate_etf_profit(time_orders):
    stock_list = ['159985','562700','159770','159870','560280','512690','159698','159928','159766','515210','512400','510880','516970','512880','159996','515220','512800','512200','159867','159326','159566','159625','512170','560080','512010','159859','159992','159611','516110','515790','159852','159869','512980','512660','512480','515050']
    stock_names = [' 豆粕 ',' 汽车零部件 ',' 机器人 ',' 化工 ',' 工程机械 ',' 酒 ',' 粮食 ',' 消费 ',' 旅游 ',' 钢铁 ',' 有色金属 ',' 红利 ',' 基建 ',' 证券 ',' 家电 ',' 煤炭 ',' 银行 ',' 房地产 ',' 畜牧 ',' 电网设备 ',' 储能电池 ',' 绿色电力 ',' 医疗 ',' 中药 ',' 医药 ',' 生物医药 ',' 创新药 ',' 电力 ',' 汽车 ',' 光伏 ',' 软件 ',' 游戏 ',' 传媒 ',' 军工 ',' 半导体 ',' 通信']
    
    stock_dict = dict(zip(stock_list, stock_names))

    processor = stock_price_processor.StockPirceProcessor()
    
    # 准备输出数据结构
    results = {}
    
    # 2. 对每个时间区间依次计算平均涨幅
    for idx, time_order in enumerate(time_orders):
        start_date = time_order[0]
        end_date = time_order[1]
        label = time_order[2] if len(time_order) > 2 else f"{start_date}~{end_date}"
        
        print(f"\n处理区间 {idx+1}/{len(time_orders)}: {label} ({start_date} 至 {end_date})")
        
        # 获取该区间内所有ETF的涨幅
        rets = processor.get_stocks_during_delta(stock_list, start_date, end_date)
        
        # 获取同期指数涨幅
        zhishu = {"SHSE.000905": "中证500", "SHSE.000852": "中证1000"}
        zhishu_rets = processor.get_stocks_during_delta(list(zhishu.keys()), start_date, end_date)
        
        if not rets:
            print(f"  警告: 区间 {label} 无数据返回")
            count = 0
            valid_etfs = {}
        else:
            count = len(rets)
            valid_etfs = rets
            
        # 打印每个证券的具体涨幅，按从大到小排序
        zhishu_str = "同期中证500涨幅{:.2f}%, 中证1000涨幅{:.2f}%".format(zhishu_rets["SHSE.000905"], zhishu_rets["SHSE.000852"])
        if valid_etfs:
            sorted_etfs = sorted(valid_etfs.items(), key=lambda x: x[1], reverse=True)
            print(f"  有效ETF数量: {count}, {zhishu_str}")
            for code, profit in sorted_etfs:
                name = stock_dict.get(code, "")
                print(f"    {code} {name}: {profit:.2f}%")
        else:
            print(f"  有效ETF数量: {count}, {zhishu_str}")
        
        results[label] = {
            "start_date": start_date,
            "end_date": end_date,
            "count": count,
            "zhishu_500": round(zhishu_rets["SHSE.000905"], 2),
            "zhishu_1000": round(zhishu_rets["SHSE.000852"], 2),
            "details": [f"{k} {stock_dict.get(k, '')}: {round(v, 2)}%" for k, v in sorted(valid_etfs.items(), key=lambda x: x[1], reverse=True)]
        }

    # 3. 把涨幅结果保存到out/etf/out.json
    output_dir = "out/etf"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "out.json")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"\n结果已保存至: {output_path}")
    except Exception as e:
        print(f"保存结果时出错: {e}")

#绘制ETF累计涨幅折线图
def plot_etf_cumulative_profit(start_date, end_date):
    import matplotlib.pyplot as plt

    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    stock_list = ['159985','562700','159770','159870','560280','512690','159698','159928','159766','515210','512400','510880','516970','512880','159996','515220','512800','512200','159867','159326','159566','159625','512170','560080','512010','159859','159992','159611','516110','515790','159852','159869','512980','512660','512480','515050','SHSE.000905','SHSE.000852','511380','BK.007520']
    stock_names = [' 豆粕 ',' 汽车零部件 ',' 机器人 ',' 化工 ',' 工程机械 ',' 酒 ',' 粮食 ',' 消费 ',' 旅游 ',' 钢铁 ',' 有色金属 ',' 红利 ',' 基建 ',' 证券 ',' 家电 ',' 煤炭 ',' 银行 ',' 房地产 ',' 畜牧 ',' 电网设备 ',' 储能电池 ',' 绿色电力 ',' 医疗 ',' 中药 ',' 医药 ',' 生物医药 ',' 创新药 ',' 电力 ',' 汽车 ',' 光伏 ',' 软件 ',' 游戏 ',' 传媒 ',' 军工 ',' 半导体 ',' 通信','中证500','中证1000','可转债','微盘股']
    
    stock_dict = dict(zip(stock_list, stock_names))

    processor = stock_price_processor.StockPirceProcessor()
    
    # 获取每日涨幅数据
    daily_profits = processor.get_daily_profits(stock_list, start_date, end_date)
    
    if not daily_profits:
        print("无每日涨幅数据")
        return
    
    # 获取所有日期
    all_dates = set()
    for profits in daily_profits.values():
        all_dates.update(profits.keys())
    dates = sorted(all_dates)
    
    # 计算每个ETF的累计涨幅
    cumulative_profits = {}
    for code in stock_list:
        if code not in daily_profits:
            continue
        cumulative = [0.0]
        for date in dates:
            profit = daily_profits[code].get(date, 0.0)
            cumulative.append(cumulative[-1] + profit)
        cumulative_profits[code] = cumulative[1:]  # 去掉初始0
    
    # 按最后累计涨幅从大到小排序
    sorted_codes = sorted(
        cumulative_profits.keys(),
        key=lambda c: cumulative_profits[c][-1] if cumulative_profits[c] else float('-inf'),
        reverse=True
    )

    # 绘制折线图
    plt.figure(figsize=(14, 8))
    lines = []
    for code in sorted_codes:
        name = stock_dict.get(code, "")
        final_profit = cumulative_profits[code][-1]
        line, = plt.plot(
            dates,
            cumulative_profits[code],
            label=f"{code} {name} {final_profit:.2f}%"
        )
        line.set_picker(5)
        lines.append(line)
    
    # 启用 hover 提示
    try:
        cursor = mplcursors.cursor(lines, hover=True)
        @cursor.connect("add")
        def on_add(sel):
            label = sel.artist.get_label()
            date_label = ''
            if hasattr(sel, 'index') and sel.index is not None:
                try:
                    idx = int(sel.index)
                    date_label = dates[idx]
                    if isinstance(date_label, str) and len(date_label) >= 10:
                        date_label = date_label[5:]
                except Exception:
                    date_label = ''
            value = sel.target[1] if hasattr(sel, 'target') else None
            if value is not None:
                sel.annotation.set(text=f"{label}\n{date_label}: {value:.2f}%")
            else:
                sel.annotation.set(text=f"{label}\n{date_label}")
            sel.annotation.get_bbox_patch().set(alpha=0.8)
    except Exception as e:
        print(f"无法启用 hover 提示: {e}")

    plt.xlabel('日期')
    plt.ylabel('累计涨幅 (%)')
    plt.title(f'ETF累计涨幅折线图 ({start_date} 至 {end_date})')
    legend = plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    if legend is not None:
        legend_lines = legend.get_lines()
        legend_texts = legend.get_texts()
        lined = {}
        text_map = {}
        annotations = []
        for legline, origline in zip(legend_lines, lines):
            legline.set_picker(5)
            lined[legline] = origline
        for text, origline in zip(legend_texts, lines):
            text.set_picker(5)
            lined[text] = origline
            text_map[origline] = text
        def clear_annotations():
            nonlocal annotations
            for ann in annotations:
                ann.remove()
            annotations = []
        def highlight_line(picked_line):
            clear_annotations()
            xdata = picked_line.get_xdata()
            ydata = picked_line.get_ydata()
            for line in lines:
                if line is picked_line:
                    line.set_linewidth(3.5)
                    line.set_alpha(1.0)
                else:
                    line.set_linewidth(1.0)
                    line.set_alpha(0.15)
            for text in legend_texts:
                if text_map.get(picked_line) is text:
                    text.set_fontweight('bold')
                    text.set_color('red')
                else:
                    text.set_fontweight('normal')
                    text.set_color('black')
            for x, y in zip(xdata, ydata):
                x_label = x[5:] if isinstance(x, str) and len(x) >= 10 else x
                annotations.append(plt.text(x, y, f"{x_label}\n{y:.2f}%", fontsize=12, rotation=45, va='bottom', ha='left', color='black'))
        def on_pick(event):
            artist = event.artist
            if artist in lined:
                highlight_line(lined[artist])
            elif artist in lines:
                highlight_line(artist)
            else:
                return
            event.canvas.draw()
        plt.gcf().canvas.mpl_connect('pick_event', on_pick)

    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

#计算指定股票列表在某时间段的平均涨幅
def calculate_price_profit(start_date, end_date):
    stock_list = ['159985','562700','159770','159870','560280','512690','159698','159928','159766','515210','512400','510880','516970','512880','159996','515220','512800','512200','159867','159326','159566','159625','512170','560080','512010','159859','159992','159611','516110','515790','159852','159869','512980','512660','512480','515050']
    stock_names = [' 豆粕 ',' 汽车零部件 ',' 机器人 ',' 化工 ',' 工程机械 ',' 酒 ',' 粮食 ',' 消费 ',' 旅游 ',' 钢铁 ',' 有色金属 ',' 红利 ',' 基建 ',' 证券 ',' 家电 ',' 煤炭 ',' 银行 ',' 房地产 ',' 畜牧 ',' 电网设备 ',' 储能电池 ',' 绿色电力 ',' 医疗 ',' 中药 ',' 医药 ',' 生物医药 ',' 创新药 ',' 电力 ',' 汽车 ',' 光伏 ',' 软件 ',' 游戏 ',' 传媒 ',' 军工 ',' 半导体 ',' 通信']
    processor = stock_price_processor.StockPirceProcessor()
    start_date_list = {}
    end_date_list = {}
    for code in stock_list:
        start_date_list[code] = start_date
        end_date_list[code] = end_date
    avg_profit = processor.calculate_price_profit(stock_list, start_date_list, end_date_list, stock_names=stock_names)

def searchAnnounce():
    processor = stock_announce_processor.StockAnnounceProcessor(all_stocks_announce)
    processor.process()
    processor.print_intervals_over(700)
    processor.find_max_interval_and_print()

def searchChongZheng(start_date, end_date, need_daily=False):
    processor = stock_announce_processor.StockAnnounceProcessor(all_stocks_announce)
    processor.searchChongZheng(start_date, end_date)
    processor2 = stock_price_processor.StockPirceProcessor()
    end_dates = {}
    start_dates = {}
    print("chongzheng=", processor.chongzheng)
    next_year = str(int(end_date.split("-")[0]) + 1)
    for code in processor.chongzheng:
        end_dates[code] = end_date
        start_dates[code] = start_date.split("-")[0]+"-05-01"
    processor2.calculate_price_profit(set(processor.chongzheng), start_dates, end_dates, need_daily=need_daily)
def searcOther2Proxy(year):
    year2 =  year + 2
    year1 = year + 1
    year = str(year)
    year2 = str(year2)
    year1 = str(year1)
    searcOtherByTitle(year+"-01-01", year+"-12-31",
                    year+"-01-01", year1+"-12-31")
def searcCZProxy(year, need_daily=False):
    year = str(year)
    searchChongZheng(year+"-01-01", year+"-12-31", need_daily=need_daily)
def searcTuiShiProxy(year):
    year2 =  year + 2
    year3 = year + 1
    year = str(year)
    year2 = str(year2)
    year3 = str(year3)
    searchTuiShi(year+"-01-01", year+"-12-20",
                    year+"-12-31", year+"-11-19")
def searchTuiShi(start, end,  price_end, price_start=None):
    processor = stock_announce_processor.StockAnnounceProcessor(all_stocks_announce)
    processor2 = stock_price_processor.StockPirceProcessor()
    processor.searchTuiShi(start, end)
    s1 = set(processor.tuishi)
    processor2.calculate_stock_mv2(s1, price_end)
    end_date = {}
    for code in s1:
        end_date[code] = price_end
        if price_start:
            processor.tuishi_date[code] = price_start
    
    processor2.calculate_price_profit(s1, processor.tuishi_date, end_date)

def searchHaveTuiShi():
    processor = stock_announce_processor.StockAnnounceProcessor(all_stocks_announce)
    processor.searchHaveTuiShi()
def searchHaveChangeMainFolder():
    processor = stock_announce_processor.StockAnnounceProcessor(all_stocks_announce)
    processor.searchHaveChangeMainFolder()

def searcReallyTuiShiProxy(year, need_cz=False, need_daily=False,
                           need_tuishi=False, price_end=None, 
                            price_start=None, ):
    year2 =  year + 2
    year3 = year + 1
    year = str(year)
    year2 = str(year2)
    searcReallyTuiShi(year+"-01-01", year+"-12-20",
                    year+"-01-01", year2+"-01-01",
                    price_end, need_cz=need_cz, 
                    price_start=price_start, need_daily=need_daily,
                    need_tuishi=need_tuishi)

def searcReallyTuiShi(start, end, start_have, end_have, price_end, 
                      price_start=None, need_cz=False, need_daily=False,
                      need_tuishi=False):
    processor2 = stock_price_processor.StockPirceProcessor()
    processor = stock_announce_processor.StockAnnounceProcessor(all_stocks_announce)
    if not need_tuishi:
        processor.searchHaveTuiShi(start_have, end_have)
    processor.searchTuiShi(start, end)
    if not need_cz:
        processor.searchPreChongZheng(start, end)
    s1 = set(processor.tuishi)
    s2 = set(processor.have_tuishi)
    spre = set(processor.pre_chongzheng)
    s5 = s1-s2
    s5 = s5 - spre
    print("有风险警示但没有退市的股票=", len(s5), s5)
    s4 = s2-s1
    print("实际退市但没有风险警示的股票列表=",len(s4), s4)
    s3 = s1.intersection(s2)
    print("可能退市的股票数=", len(s1),"真的退市股票数=", len(s3), s3)
    processor2.calculate_stock_mv2(s5, price_end)
    end_date = {}
    for code in s5:
        end_date[code] = price_end
        if price_start:
            processor.tuishi_date[code] = price_start
    
    processor2.calculate_price_profit(s5, processor.tuishi_date, end_date, need_daily=need_daily)
    

def searcOther(start, end, start_have, end_have, price_end):
    processor = stock_announce_processor.StockAnnounceProcessor(all_stocks_announce)
    processor.searchHaveTuiShi(start_have, end_have)
    processor.searchOther(start, end)
    s1 = set(processor.other)
    s2 = set(processor.have_tuishi)
    s5 = s1-s2
    print("有风险警示但没有退市的股票=", len(s5), s5)
    end_date = {}
    for code in s5:
        end_date[code] = price_end
    processor2 = stock_price_processor.StockPirceProcessor()
    processor2.calculate_price_profit(s5, processor.other_date, end_date)
def searcOtherByTitle(start, end, start_have, end_have):
    processor = stock_announce_processor.StockAnnounceProcessor(all_stocks_announce)
    processor.searchHaveTuiShi(start_have, end_have)
    processor.searchOtherByTitle(start, end)
    s1 = set(processor.other2)
    s2 = set(processor.have_tuishi)
    s5 = s1-s2
    print("有风险警示但没有退市的股票=", len(s5), s5)
    processor2 = stock_price_processor.StockPirceProcessor()
    processor2.calculate_price_profit(s5, processor.other2_start_date, processor.other2_end_date)
# 从本地文件加载所有A股代码
def loadAllA():
    f = root_dir + all_a_file
    with open(f, 'r', encoding='utf-8') as file:
        datas = json.load(file)
        stock_num = len(datas)
        for i in range(stock_num):
            all_a_stocks.append(datas[i])
        print("local_a_stock_num=", stock_num)

def load_all_announcements():
    """
    加载本地所有股票公告数据。
    """
    directory = root_dir + announce_dir
    dir_path = os.path.abspath(directory)
    for filename in os.listdir(dir_path):
        if filename.endswith(".json"):
            file_path = os.path.join(dir_path, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    all_stocks_announce[filename[:-5]] = data  # 去掉 .json 后缀作为股票代码
                except Exception as e:
                    print(f"读取 {filename} 时出错: {e}")
    
# 更新所有股票的公告
def UpdateAllStockAnnounce(f=False):
    for i in range(len(all_a_stocks)):
        code = all_a_stocks[i]
        print("process ", i, " code=", code)
        getStockAnnounceInfo(code,f)
        

def load_local_all():
    f = root_dir + all_file
    with open(f, 'r', encoding='utf-8') as file:
        datas = json.load(file)
        stock_num = len(datas)
        for i in range(stock_num):
            all_stocks[datas[i]] = 1
        print("local_stock_num=", stock_num)
    
def load_remote_all():
    page_size = "200"
    page_num = 1
    url2 = all_stocks_url.replace("$PAGE_SIZE$", page_size)
    need_update = False
    while True:
        url3 = url2.replace("$PAGE_NUM$", str(page_num))
        print(url3)
        ret = get_message(page_num, url3)
        #print(ret)
        ret = json.loads(ret)
        if ret["data"] != None and ret["rc"] == 0:
            diff = ret["data"]["diff"]
            diff_len = len(diff)
            for i in range(diff_len):
                detail = diff[i]
                code = detail["f12"]
                if code in all_stocks:
                    pass
                else:
                    all_stocks[code] = 1
                    need_update = True
        else:
            break
        page_num = page_num + 1
        
        #print(ret)
        pass
    return need_update

def UpdateBaseInfo():
    base_file = root_dir+base_dir
    for key in all_stocks:
        f = base_file + key + ".json"
        if os.path.exists(f):
            pass
        else:
            getStockInfo(key)
        
def getStockFinance(code):
 
 pass

def getStockAnnounceInfo(code, f=False):
    stock_announce = all_stocks_announce.get(code, [])
    stock_announce_len = len(stock_announce)
    if stock_announce_len == 0:
        all_stocks_announce[code] = stock_announce
    elif not f:
        return
    print(" code=", code)
    url2 = stock_announce_url.replace("000951", code)
    need_update = False
    is_end = False
    i = 1
    temp_arr = []
    while True:
        url3 = url2.replace("$PAGE_INDEX$", str(i))
        ret = get_message(code, url3)
        ret = json.loads(ret)
        if ret["data"] != None and ret["success"] == 1:
            anns = ret["data"]["list"]
            anns_len = len(anns)
            if anns_len == 0:
                break
            for j in range(anns_len):
                detail = anns[j]
                if stock_announce_len==0 or detail["art_code"] != stock_announce[0]["art_code"]:
                    notice_date = detail["notice_date"]
                    title = detail["title"]
                    art_code = detail["art_code"]
                    info = stock_announce_info.StockAnnounceInfo(notice_date, title, art_code)
                    temp_arr.append(info.__dict__)
                    need_update = True
                else:
                    is_end = True
                    break
            if is_end:
                break
        else:
            break
        i = i + 1
    if need_update:
        print("  update announce num=", len(temp_arr))
        stock_announce = temp_arr + stock_announce
        all_stocks_announce[code] = stock_announce
        f = root_dir + announce_dir + code + ".json"
        with open(f, 'w', encoding='utf-8') as file:
            json.dump(stock_announce, file, indent=4, ensure_ascii=False)

def getStockInfo(code):
    url2 = stock_info_url.replace("$CODE$", code)
    ret = get_message(code, url2)
    base_info = stock_base_info.StocKBaseInfo()
    soup = BeautifulSoup(ret, 'html.parser')
    security_info = soup.find(id="security_info")
    for elem in security_info.find_all("li"):
        span = elem.find_all("span")
        if len(span) == 2:
            key = span[0].get_text().strip()
            value = span[1].get_text().strip()
            if key == "市场分层":
                base_info.level = value
            elif key == "挂牌日期":
                base_info.birth_date = value
            elif key == "持续督导券商":
                base_info.quanshang = value
            elif key == "证券简称":
                base_info.stock_name = value
            elif key == "证券代码":
                base_info.stock_code = value
    if base_info.stock_code == "-":
        return
    company_info = soup.find(id="company_info")
    for elem in company_info.find_all("li"):
        span = elem.find_all("span")
        if len(span) == 2:
            key = span[0].get_text().strip()
            value = span[1].get_text().strip()
            if key == "公司全称":
                base_info.long_name = value
            elif key == "实际控制人":
                base_info.boss_name = value
            elif key == "主营业务":
                base_info.main_business = value
            elif key == "公司简介":
                base_info.introduce = value 
    f = root_dir + base_dir + code + ".json"
    with open(f, 'w', encoding='utf-8') as file:
        json.dump(base_info.__dict__, file, indent=4, ensure_ascii=False)
    


def updateAll():
    js = []
    for key in all_stocks:
        js.append(key)
    f = root_dir + all_file
    with open(f, 'w', encoding='utf-8') as file:
        json.dump(js, file, indent=4, ensure_ascii=False)

def get_message(code, webhook_url, headers=None):
    
    
    response = requests.get(webhook_url, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        print("消息发送失败", code)
        return ""
    

if __name__ == '__main__':
    run(strategy_id='d01f07c0-a3d0-11ee-b878-14755b767e75',
        filename='main.py',
        mode=MODE_BACKTEST,
        token='09aef9a2c661a1d621024f2c95eaa76d27fdb3ea',
        backtest_start_time='2020-11-01 08:00:00',
        backtest_end_time='2026-11-10 16:00:00',
        backtest_adjust=ADJUST_PREV,
        backtest_initial_cash=10000000,
        backtest_commission_ratio=0.0001,
        backtest_slippage_ratio=0.0001)