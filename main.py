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
from fetch_stock_base_info import FetchStockBaseInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
from fetch_all_a_stocks import FetchAllAStocks
from domain import doinit



if sys.argv[1:] and sys.argv[1:][0].find("--")<0:
    arg_flag = int(sys.argv[1:][0]) if len(sys.argv) > 1 else -1
else:
    arg_flag = -1

# 策略中必须有init方法
def init(context):
    flag = 0 if arg_flag == -1 else arg_flag
    context.flag = flag
    doinit(context)
    if flag ==0:
        timer(timer_func=ontimer_3, period=5000, start_delay=10000)
    

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