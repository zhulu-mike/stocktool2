# coding=utf-8
from datetime import datetime, timedelta
from gm.api import *
import json

class StockPirceProcessor:
   
    def __init__(self):
        pass
    def get_stock_symbol(self, stock):
        if isinstance(stock, str):
            if stock.startswith("SHSE.") or stock.startswith("SZSE.") or stock.startswith("BK.")or stock.startswith("BJSE."):
                return stock
        
        if isinstance(stock, str):
            stock = int(stock)
        stock = f'{stock:06d}'
        if stock.startswith("6"):
            ssymbol = f'SHSE.{stock}'
        elif stock.startswith("9"):
            ssymbol = f'SHSE.{stock}'
        elif stock.startswith("12"):
            ssymbol = f'SZSE.{stock}'
        elif stock.startswith("11"):
            ssymbol = f'SHSE.{stock}'
        elif stock.startswith("15"):
            ssymbol = f'SZSE.{stock}'
        elif stock.startswith("5"):
            ssymbol = f'SHSE.{stock}'
        elif stock.startswith("2"):
            ssymbol = f'SHSE.{stock}'
        else:
            ssymbol = f'SZSE.{stock}'
        return ssymbol
    
    def get_stocks_by_listed_year(self, stock_list):
        """
        获取给定股票列表的上市日期，按年份分组统计。
        stock_list: list of stock codes
        返回一个字典，键为上市年份，值为该年份上市的股票数量。
        """
        symbols = []
        for stock_code in stock_list:
            symbol = self.get_stock_symbol(stock_code)
            symbols.append(symbol)
        
        # 获取股票基本信息（包括上市日期）
        stock_info = get_symbol_infos(sec_type1=1010, sec_type2=101001, symbols=symbols, df=False)
        
        # 按年份分组统计
        year_count = {}
        for info in stock_info:
            listed_date = info.get('listed_date')
            if listed_date:
                # listed_date 可能是 datetime 对象或字符串
                if hasattr(listed_date, 'strftime'):
                    year = listed_date.strftime('%Y')
                else:
                    year = str(listed_date)[:4]
                if year not in year_count:
                    year_count[year] = 0
                year_count[year] += 1
        
        # 按年份排序输出
        sorted_years = sorted(year_count.items(), key=lambda x: x[0])
        print(f"总数={len(stock_list)}只股票，各年份上市股票数量：")
        for year, count in sorted_years:
            print(f"  {year}年: {count}只")
        
        return year_count
    #取莫一日涨幅最好的一批股票，回测它后面一段时间的表现
    def backtrace_fantan(self, stock_list, start_date, end_date):
        """
        获取指定股票列表在某一时间段内的涨跌幅。
        stock_list: list of stock codes
        start_date: str, "YYYY-MM-DD"，第一天应该是调整的最后一天，如果后面价格低于这个价格就卖掉
        end_date: str, "YYYY-MM-DD"
        返回一个字典，键为股票代码，值为涨跌幅百分比。
        """
        result = {}
        symbols = []
        for stock_code in stock_list:
            symbol = self.get_stock_symbol(stock_code)
            symbols.append(symbol)
        datas = history(symbol=symbols, frequency='1d', start_time=start_date,  end_time=end_date, fields='symbol,low ,close', adjust=ADJUST_POST, df= False)
        stock_datas = {}
        first_day_price = {}
        stock_profit = {}
        #先按每个股票归类
        for data in datas:
            if data['symbol'] not in stock_datas:
                first_day_price[data['symbol']] = [data['low'], data['close']]
                stock_datas[data['symbol']] = []
            else:
                stock_datas[data['symbol']].append(data)
            if len(stock_datas[data['symbol']]) == 1:
                #以第二天的收盘价当买入价
                first_day_price[data['symbol']][1] = data['close']
    
        for symbol, stock_data in stock_datas.items():
            min_price = first_day_price[symbol][0]
            for ii in range(1, len(stock_data)):
                if stock_data[ii]['low'] < min_price:
                    stock_profit[symbol] = (min_price - first_day_price[symbol][1]) / first_day_price[symbol][1] * 100
                    #print(f"股票代码: {symbol}, 买入价格: {first_day_price[symbol][1]}, 止损最低价格: {min_price}, 涨跌幅: {stock_profit[symbol]:.2f}%")
                    break
            #如果没有跌破止损价，最后以最后一天的收盘价卖出
            if symbol not in stock_profit and len(stock_data)>0:
                delta = (stock_data[-1]['close'] - first_day_price[symbol][1]) / first_day_price[symbol][1] * 100
                stock_profit[symbol] = delta
        #计算result里的平均涨幅
        total_profit = sum(stock_profit.values()) / len(stock_profit) if stock_profit else 0
        print(f"{len(stock_profit)}只股票, {start_date}~{end_date}, 平均涨幅: {total_profit:.2f}%")
        return result

    def get_stocks_during_delta(self, stock_list, start_date, end_date):
        """
        获取指定股票列表在某一时间段内的涨跌幅。
        stock_list: list of stock codes
        start_date: str, "YYYY-MM-DD"
        end_date: str, "YYYY-MM-DD"
        返回一个字典，键为股票代码，值为涨跌幅百分比。
        """
        result = {}
        symbols = []
        for stock_code in stock_list:
            symbol = self.get_stock_symbol(stock_code)
            symbols.append(symbol)
        datas = history(symbol=symbols, frequency='1d', start_time=start_date,  end_time=start_date, fields='symbol, open, close', adjust=ADJUST_POST, df= False)
        start_price = {}
        for data in datas:
            start_price[data['symbol']] = data['close']
        datas = history(symbol=symbols, frequency='1d', start_time=end_date,  end_time=end_date, fields='symbol, open, close', adjust=ADJUST_POST, df= False)
        end_price = {}
        nodata_count = 0
        no_start_price_count = 0
        no_end_price_count = 0
        for data in datas:
            end_price[data['symbol']] = data['close']
        for stock_code in stock_list:
            symbol = self.get_stock_symbol(stock_code)
            if symbol not in start_price and symbol not in end_price:
                #print(f"股票代码: {stock_code} 在 {start_date} 和 {end_date} 都没有数据，跳过计算涨跌幅。")
                #再跨区间找一次
                data = history(symbol=symbol, frequency='1d', start_time=start_date,  end_time=end_date, fields='symbol, close', adjust=ADJUST_POST, df= False)
                if len(data) > 2:
                    start_price[symbol] = data[0]['close']
                    end_price[symbol] = data[-1]['close']
                else:
                    nodata_count += 1
                    continue
            if symbol not in start_price:
                #没有开始数据有结束数据，说明是新上市的股票，可以从开始日期往后继续寻找数据，用第一个可寻的数据替代
                data = history(symbol=symbol, frequency='1d', start_time=start_date,  end_time=end_date, fields='symbol, close', adjust=ADJUST_POST, df= False)
                if len(data) > 0:
                    start_price[symbol] = data[0]['close']
                else:
                    no_start_price_count += 1
                    continue
            if symbol not in end_price:
                #可能是退市或者停牌了，往后延长1个月的数据寻找试试
                data = history(symbol=symbol, frequency='1d', start_time=end_date,  end_time=(datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=30)).strftime("%Y-%m-%d"), fields='symbol, close', adjust=ADJUST_POST, df= False)
                if len(data) > 0:
                    end_price[symbol] = data[0]['close']
                else:
                    no_end_price_count += 1
                    continue
            delta = (end_price[symbol] - start_price[symbol]) / start_price[symbol] * 100
            result[stock_code] = delta
        #print(f"共有 {nodata_count} 只股票在 {start_date}~{end_date} 时间段内没有数据。")
        #print(f"共有 {no_start_price_count} 只股票在 {start_date} 没有数据。")
        #print(f"共有 {no_end_price_count} 只股票在 {end_date} 没有数据。")
        return result

    def get_daily_profits(self, stock_list, start_date, end_date):
        """
        获取指定股票列表在某一时间段内的每日涨跌幅。
        stock_list: list of stock codes
        start_date: str, "YYYY-MM-DD"
        end_date: str, "YYYY-MM-DD"
        返回一个字典，键为股票代码，值为 {date: profit_percent}
        """
        result = {}
        symbols = []
        for stock_code in stock_list:
            symbol = self.get_stock_symbol(stock_code)
            symbols.append(symbol)
        
        # 获取整个区间的数据
        datas = history(symbol=symbols, frequency='1d', start_time=start_date, end_time=end_date, fields='symbol, close, eob', adjust=ADJUST_POST, df=False)
        
        # 按股票分组数据
        stock_data = {}
        for data in datas:
            symbol = data['symbol']
            if symbol not in stock_data:
                stock_data[symbol] = []
            stock_data[symbol].append(data)
        
        # 对每个股票计算每日涨幅
        for stock_code in stock_list:
            symbol = self.get_stock_symbol(stock_code)
            if symbol not in stock_data:
                continue
            data_list = sorted(stock_data[symbol], key=lambda x: x['eob'])
            daily_profits = {}
            prev_close = None
            for data in data_list:
                close = data['close']
                date_str = data['eob'].strftime('%Y-%m-%d')
                if prev_close is not None:
                    profit = (close - prev_close) / prev_close * 100
                    daily_profits[date_str] = profit
                prev_close = close
            result[stock_code] = daily_profits
        
        return result

    def get_stocks_today_delta(self, stock_list):
        """
        获取指定股票列表在当天的涨跌幅。
        stock_list: list of stock codes
        返回一个字典，键为股票代码，值为涨跌幅百分比。
        """
        #先往前取一段，看看最近的交易日是哪一天就用哪一天
        d1 = (datetime.now() - timedelta(days=20)).strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        history_data = history(symbol="SHSE.512800", frequency='1d', start_time=d1,  end_time=yesterday, fields='symbol, close, eob', adjust=ADJUST_PREV, df= False)
        print(f"最近的交易日是{history_data[-1]['eob'].strftime('%Y-%m-%d')}")
        yesterday = history_data[-1]["eob"].strftime('%Y-%m-%d')
        result = {}
        symbols = []
        for stock_code in stock_list:
            symbol = self.get_stock_symbol(stock_code)
            symbols.append(symbol)
        history_data = history(symbol=symbols, frequency='1d', start_time=yesterday,  end_time=yesterday, fields='symbol, close, eob', adjust=ADJUST_PREV, df= False)
        yesterday_close = {}
        for data in history_data:
            yesterday_close[data['symbol']] = data['close']
        #现在取今天的数据
        td = datetime.now().strftime('%Y-%m-%d')
        datas = datas = current(symbols=symbols,  fields='symbol, open, price')# history(symbol=symbols, frequency='1d', start_time=td,  end_time=td, fields='symbol, close, eob', adjust=ADJUST_PREV, df= False)
        for data in datas:
            symbol = data['symbol']
            price = data['price']
            if symbol in yesterday_close:
                yesterday_price = yesterday_close[symbol]
                delta = (price - yesterday_price) / yesterday_price * 100
                result[symbol] = delta
                print(f"股票代码: {symbol}, 昨收价格: {yesterday_price}, 当前价格: {price}, 涨跌幅: {delta:.2f}%")

        return result
        
    #计算指定股票列表在某一时间段内的涨跌幅
    def calculate_price_profit(self, stock_list, start_date, end_date, need_daily=False, stock_names=None):
        """
        计算指定股票列表在某一时间段内的涨跌幅。
        stock_list: list of stock codes
        start_date: str, "YYYY-MM-DD"
        end_date: str, "YYYY-MM-DD"
        返回平均涨幅
        """
        total_profit = 0
        win_count = 0
        stock_count = 0
        groupby_month_profit = {}
        groupby_month_profit2 = {}
        groupby_daily_profit = {}
        cc = -1
        for stock_code in stock_list:
            cc = cc + 1
            if start_date[stock_code]>= end_date[stock_code]:
                continue
            if stock_code.startswith("6") or stock_code.startswith("5"):
                stock = "SHSE." + stock_code
            else:
                stock = "SZSE." + stock_code
            data = history(symbol=stock, frequency='1d', start_time=start_date[stock_code],  end_time=end_date[stock_code], fields='symbol, open, close, eob', adjust=ADJUST_PREV, df= False)
            if len(data) < 1:
                print(f"股票代码: {stock_code}-{start_date[stock_code]} 到 {end_date[stock_code]} 无数据")
                continue
            start_price = data[0]['open']
            end_price = data[-1]['close']
            profit = (end_price - start_price) / start_price * 100
            stock_name = "none"
            if stock_names:
                stock_name=stock_names[cc]
            print(f"股票代码: {stock_code}{stock_name}=={start_date[stock_code]}-{end_date[stock_code]}, 起始价格: {start_price}, 结束价格: {end_price}, 涨跌幅: {profit:.2f}%")
            total_profit += profit
            stock_count = stock_count + 1
            if profit > 0:
                win_count += 1
            if need_daily:
                #统计按日涨跌幅
                start_price = data[0]['open']
                for i in range(0, len(data)):
                    date_str = data[i]['eob'].strftime("%Y-%m-%d")
                    end_price = data[i]['close']
                    day_profit = (end_price - start_price) / end_price * 100
                    if date_str not in groupby_daily_profit:
                        groupby_daily_profit[date_str] = [day_profit, 1]
                    else:
                        groupby_daily_profit[date_str][0] += day_profit
                        groupby_daily_profit[date_str][1] += 1
                    start_price = end_price

            #继续统计按月涨跌幅
            start_price = data[0]['open']
            start_date_str = data[0]['eob'].strftime("%Y-%m")
            start_date_str2 = data[0]['eob'].strftime("%Y-%m-%d")
            for i in range(1, len(data)+1):
                if i < len(data):
                    date_str = data[i]['eob'].strftime("%Y-%m")
                    if date_str == start_date_str:
                        continue
                end_price = data[i-1]['close']
                month_profit = (end_price - start_price) / start_price * 100
                
                if start_date_str not in groupby_month_profit:
                    groupby_month_profit[start_date_str] = [month_profit, 1, 0]
                    groupby_month_profit2[start_date_str] = {stock_code: month_profit}
                else:
                    groupby_month_profit[start_date_str][0] += month_profit
                    groupby_month_profit[start_date_str][1] += 1
                    groupby_month_profit2[start_date_str][stock_code] = month_profit
                if month_profit < 0:
                    groupby_month_profit[start_date_str][2] += 1
                start_price = end_price
                if i < len(data):
                    date_str = data[i]['eob'].strftime("%Y-%m")
                    start_date_str = date_str
        #打印按日统计的涨跌幅
        if need_daily:
            ds = ""
            daily_arr = sorted(groupby_daily_profit.items())
            for day, profit in daily_arr:
                ds = ds + f"{day}: {profit[0]/profit[1]:.2f}%, "
            print("按日统计涨跌幅: ", ds)
        #打印按月统计的涨跌幅
        month_arr = sorted(groupby_month_profit.items())
        ms = ""
        for month, profit in month_arr:
            ms = ms + f"{month}: {profit[0]/profit[1]:.2f}%=失败率{profit[2]*100/profit[1]:.2f}%, "
        print("按月统计涨跌幅: ", ms)
        avg_profit = total_profit / stock_count
        print(f"平均涨跌幅: {avg_profit:.2f}%, 赢的次数: {win_count}, {stock_count}")
        #统计本月涨跌幅最差的股票在下个月的表现
        month_arr2 = sorted(groupby_month_profit2.items())
        last_loser = []
        ms = ""
        for month, profit_map in month_arr2:
            if len(last_loser)>0:
                dic = []
                total_profit2 = 0
                total_count = 0
                for stock_code in last_loser:
                    if stock_code in profit_map:
                        profit2 = profit_map[stock_code]
                        total_profit2 += profit2
                        total_count += 1
                if total_count>0:
                    avg_profit2 = total_profit2 / total_count
                    ms = ms + f"{month} : {avg_profit2:.2f}%, "
            last_loser.clear()
            for stock_code, profit in profit_map.items():
                if profit < 0:
                    last_loser.append((stock_code))
        print(f"下月表现: ", ms)
        return avg_profit
    
    #计算指定股票列表在某一时间的平均市值
    def calculate_stock_mv(self, stock_list, start_date):
        """
        计算指定股票列表在某一时间的平均市值。
        stock_list: list of stock codes
        start_date: str, "YYYY-MM-DD"
        返回一个字典，键为股票代码，值为涨跌幅百分比。
        """
        total_mv = 0
        for stock_code in stock_list:
            if stock_code.startswith("6"):
                stock = "SHSE." + stock_code
            else:
                stock = "SZSE." + stock_code
            data = stk_get_daily_mktvalue_pt(symbols=stock, trade_date=start_date[stock_code],  fields='tot_mv', df= False)
            mv = data[0]['tot_mv']
            mv = mv / 100000000  #转换为亿元
            print(f"股票代码: {stock_code}-{start_date[stock_code]}, 市值: {mv}")
            total_mv += mv
        avg_mv = total_mv / len(stock_list)
        print(f"平均市值: {avg_mv:.2f} 亿元")
        return avg_mv

    #计算指定股票列表在某一时间的平均市值
    def calculate_stock_mv2(self, stock_list, end_date):
        """
        计算指定股票列表在某一时间的平均市值。
        stock_list: list of stock codes
        start_date: str, "YYYY-MM-DD"
        返回一个字典，键为股票代码，值为涨跌幅百分比。
        """
        total_mv = 0
        symbols = []
        for stock_code in stock_list:
            if stock_code.startswith("6"):
                stock = "SHSE." + stock_code
            else:
                stock = "SZSE." + stock_code
            symbols.append(stock)
        datas = stk_get_daily_mktvalue_pt(symbols=symbols, trade_date=end_date,  fields='tot_mv', df= False)
        for i in range(len(datas)):
            data = datas[i]
            mv = data['tot_mv']
            mv = mv / 100000000  #转换为亿元
            print(f"股票代码: {data['symbol']}-{end_date}, 市值: {mv:.2f} 亿元")
            total_mv += mv
        avg_mv = total_mv / len(stock_list)
        print(f"平均市值: {avg_mv:.2f} 亿元")
        return avg_mv
    
    def calculate_wpg(self, date):
        ret = stk_get_index_constituents(index="SHSE.000001", trade_date=date)
        ret = ret["symbol"].tolist()
        ret2 = stk_get_index_constituents(index="SZSE.399106", trade_date=date)
        ret2 = ret2["symbol"].tolist()
        ret.extend(ret2)
        #print("沪深市值股票总数=", len(ret), date)
        ret3 = get_symbols(1010, sec_type2=101001, symbols=ret, skip_st=True, trade_date=date, df=True)
        ret3 = ret3["symbol"].tolist()
        print("剔除ST后的股票数量=", len(ret3), date)
        datas = stk_get_daily_mktvalue_pt(symbols=ret3, trade_date=date,  fields='tot_mv', df= False)
        mvs = {}
        for i in range(len(datas)):
            data = datas[i]
            mv = data['tot_mv']
            mvs[data['symbol']] = mv
        #按市值排序，保留key-value形式
        mvs = sorted(mvs.items(), key=lambda x: x[1], reverse=True)
        #print("市值排序后前10名：", mvs[-10:], date)
        #计算排行后400的总市值
        total_mv = 0
        n = 400
        for k,v in mvs[-n:]:
            total_mv += v
        avg_mv = total_mv / n / 100000000  #转换为亿元
        print(f"WPG后{n}平均市值: {avg_mv:.2f} 亿元", date)
        #print(f"第{n}名{mvs[-n+1][0]}市值=", mvs[-n+1][1]/100000000, "亿元", date)  
        return avg_mv

    def update_kzz_with_market_data(self):
        # 1. 读取kzz/all.json文件
        with open('kzz/all.json', 'r', encoding='utf-8') as f:
            kzz_list = json.load(f)
        
        # 2. 获取所有可转债代码
        kzz_symbols = []
        for kzz in kzz_list:
            bond_id = kzz['bond_id']
            symbol = self.get_stock_symbol(bond_id)
            kzz_symbols.append(symbol)
        
        # 获取可转债对应的正股代码
        kzz_info = get_symbol_infos(sec_type1=1030, sec_type2=103001, symbols=kzz_symbols, df=False)
        kzz_to_stock = {}
        stock_symbols = []
        for info in kzz_info:
            kzz_symbol = info['symbol']
            underlying_symbol = info.get('underlying_symbol', '')
            kzz_to_stock[kzz_symbol] = underlying_symbol
            if underlying_symbol:
                stock_symbols.append(underlying_symbol)
        
        # 3. 调取current接口，一次性批量获取所有可转债和对应正股的当日行情
        all_symbols = list(set(kzz_symbols + stock_symbols))
        current_data = current(symbols=all_symbols, fields='symbol, price')
        
        current_price = {}
        for data in current_data:
            current_price[data['symbol']] = data['price']
        
        # 4. 调取history接口，一次性批量获取所有可转债和正股的前20日行情
        end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=20)).strftime('%Y-%m-%d')
        history_data = history(symbol=all_symbols, frequency='1d', start_time=start_date, 
                              end_time=end_date, fields='symbol, close, eob', 
                              adjust=ADJUST_PREV, df=False)
        
        # 为每个股票取最后一天可用的收盘价
        last_close = {}
        symbol_history = {}
        for data in history_data:
            symbol = data['symbol']
            if symbol not in symbol_history:
                symbol_history[symbol] = []
            symbol_history[symbol].append(data)
        
        for symbol, data_list in symbol_history.items():
            if data_list:
                # 按日期排序，取最后一个
                data_list.sort(key=lambda x: x['eob'])
                last_close[symbol] = data_list[-1]['close']
        
        # 5. 计算转股溢价率、涨幅，并更新数据
        for kzz in kzz_list:
            bond_id = kzz['bond_id']
            kzz_symbol = self.get_stock_symbol(bond_id)
            stock_symbol = kzz_to_stock.get(kzz_symbol, '')
            
            # 获取可转债最新价
            kzz_price = current_price.get(kzz_symbol, 0)
            kzz['bond_price'] = round(kzz_price, 2) if kzz_price else None
            
            # 获取正股最新价
            stock_price = current_price.get(stock_symbol, 0)
            kzz['stock_price'] = round(stock_price, 2) if stock_price else None
            
            # 计算可转债涨幅
            kzz_last_close = last_close.get(kzz_symbol, 0)
            if kzz_last_close > 0 and kzz_price > 0:
                kzz['bond_change'] = round((kzz_price - kzz_last_close) / kzz_last_close * 100, 2)
            else:
                kzz['bond_change'] = None
            
            # 计算正股涨幅
            stock_last_close = last_close.get(stock_symbol, 0)
            if stock_last_close > 0 and stock_price > 0:
                kzz['stock_change'] = round((stock_price - stock_last_close) / stock_last_close * 100, 2)
            else:
                kzz['stock_change'] = None
            
            # 计算转股溢价率
            convert_price = float(kzz.get('convert_price', '0'))
            if convert_price > 0 and kzz_price > 0 and stock_price > 0:
                conversion_value = 100 / convert_price * stock_price
                premium_rate = (kzz_price - conversion_value) / conversion_value * 100
                kzz['premium_rate'] = round(premium_rate, 2)
            else:
                kzz['premium_rate'] = None
        
        # 6. 重新写回all.json
        with open('kzz/all.json', 'w', encoding='utf-8') as f:
            json.dump(kzz_list, f, ensure_ascii=False, indent=2)
        
        print(f"{datetime.now()} 已更新 {len(kzz_list)} 只可转债数据")
        return kzz_list