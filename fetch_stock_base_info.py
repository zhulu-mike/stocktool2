import json
import requests
import os
from gm.api import *

class FetchStockBaseInfo:
    def __init__(self):
        self.api_url = 'https://datacenter-web.eastmoney.com/api/data/v1/get'
        self.stocks_dir = 'stocks'
        
        # 确保stocks目录存在
        if not os.path.exists(self.stocks_dir):
            os.makedirs(self.stocks_dir)
    
    def get_stock_base_info(self, stock_code):
        """获取单个股票的基本信息"""
        # 确保股票代码是6位字符串
        stock_code = str(stock_code).zfill(6)
        
        params = {
            'reportName': 'RPT_F10_BASIC_ORGINFO',
            'columns': 'SECURITY_CODE,SECURITY_NAME_ABBR,BOARD_NAME_LEVEL,LISTING_DATE',
            'quoteColumns': '',
            'filter': f'(SECURITY_CODE="{stock_code}")'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        try:
            response = requests.get(self.api_url, params=params, headers=headers, timeout=10)
            data = response.json()
            
            if data.get('success') and data.get('result') and data['result'].get('data'):
                item = data['result']['data'][0]
                
                # 格式化上市日期
                listing_date = item.get('LISTING_DATE', '')
                if listing_date:
                    listing_date = listing_date.split(' ')[0]  # 只取日期部分
                
                # 拆分行业信息
                industry = item.get('BOARD_NAME_LEVEL', '')
                industry_parts = industry.split('-') if industry else []
                
                return {
                    'stock_code': item.get('SECURITY_CODE', ''),
                    'stock_name': item.get('SECURITY_NAME_ABBR', ''),
                    'listed_date': listing_date,
                    'industry_level1': industry_parts[0] if len(industry_parts) > 0 else '',
                    'industry_level2': industry_parts[1] if len(industry_parts) > 1 else '',
                    'industry_level3': industry_parts[2] if len(industry_parts) > 2 else '',
                    'industry_level4': industry_parts[3] if len(industry_parts) > 3 else ''
                }
            else:
                # 打印原始响应用于调试
                print(f"  未找到股票 {stock_code} 的数据")
                print(f"  原始响应: {data}")
                return None
        
        except Exception as e:
            print(f"  获取股票 {stock_code} 信息失败: {e}")
            return None
    
    def process_all_stocks(self, force_update=False):
        """处理所有股票"""
        # 检查all_a.json文件是否存在
        input_file = os.path.join(self.stocks_dir, 'all_a.json')
        if not os.path.exists(input_file):
            print(f"错误：未找到文件 {input_file}")
            return None
        
        # 读取股票列表
        with open(input_file, 'r', encoding='utf-8') as f:
            stock_list = json.load(f)
        
        # 读取本地已有的base信息（当force_update为False时使用）
        existing_base_info = {}
        output_file = os.path.join(self.stocks_dir, 'all_base.json')
        if not force_update and os.path.exists(output_file):
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    for item in existing_data:
                        code = item.get('stock_code')
                        if code:
                            existing_base_info[code] = item
                print(f"已读取本地 {len(existing_base_info)} 条股票基本信息")
            except Exception as e:
                print(f"读取本地base信息失败: {e}")
        
        # 获取每个股票的基本信息
        result = []
        total = len(stock_list)
        for i, stock in enumerate(stock_list, 1):
            # 支持多种格式：{'code': 'xxx'} 或 {'stock_code': 'xxx'} 或 直接是股票代码字符串
            if isinstance(stock, dict):
                stock_code = stock.get('code') or stock.get('stock_code')
            else:
                stock_code = str(stock)
            
            if not stock_code:
                continue
            
            stock_code = str(stock_code).zfill(6)
            
            # 检查是否需要从东方财富获取
            if not force_update and stock_code in existing_base_info:
                print(f"正在处理 {i}/{total}: {stock_code} - 使用本地缓存")
                result.append(existing_base_info[stock_code])
            else:
                print(f"正在处理 {i}/{total}: {stock_code}")
                info = self.get_stock_base_info(stock_code)
                if info:
                    result.append(info)
        
        # 批量获取退市日期
        print("\n正在批量获取退市日期...")
        if result:
            from stock_price_processor import StockPirceProcessor
            processor = StockPirceProcessor()
            
            stock_codes = [processor.get_stock_symbol(item['stock_code']) for item in result]
            try:
                # 获取A股股票的基本信息，包含退市日期
                symbol_info = get_symbol_infos(sec_type1=1010, sec_type2=101001, symbols=stock_codes, df=False)
                
                # 建立股票代码到退市日期的映射
                delisted_date_map = {}
                for item in symbol_info:
                    code = item.get('symbol')
                    if code:
                        # 去掉市场前缀，只保留6位代码
                        code = str(code)[-6:] if len(str(code)) > 6 else str(code)
                        delisted_date = item.get('delisted_date')
                        if delisted_date:
                            # 如果是datetime对象，转换为字符串
                            if hasattr(delisted_date, 'strftime'):
                                delisted_date = delisted_date.strftime('%Y-%m-%d')
                            else:
                                delisted_date = str(delisted_date).split(' ')[0]
                        print(f"  {code}: {delisted_date}")
                        delisted_date_map[code] = delisted_date
                
                # 将退市日期拼接到基本信息中
                for item in result:
                    stock_code = item['stock_code']
                    item['delisted_date'] = delisted_date_map.get(stock_code, '')
                
                print(f"已获取 {len(delisted_date_map)} 只股票的退市日期")
            except Exception as e:
                print(f"获取退市日期失败: {e}")
        
        # 保存到文件
        output_file = os.path.join(self.stocks_dir, 'all_base.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n完成！共获取 {len(result)} 只股票的基本信息")
        print(f"结果已保存到 {output_file}")
        return result

if __name__ == '__main__':
    processor = FetchStockBaseInfo()
    processor.process_all_stocks()