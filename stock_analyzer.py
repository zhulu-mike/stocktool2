import json
import os
from datetime import datetime
from collections import defaultdict

class StockAnalyzer:
    def __init__(self, base_info_file='stocks/all_base.json'):
        self.base_info_file = base_info_file
        self.base_info = self._load_base_info()

    def _load_base_info(self):
        if not os.path.exists(self.base_info_file):
            print(f"文件不存在: {self.base_info_file}")
            return {}

        with open(self.base_info_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        info_dict = {}
        for item in data:
            stock_code = item.get('stock_code', '')
            info_dict[stock_code] = item
        print(f"加载 {len(info_dict)} 条基础信息")
        return info_dict

    def _parse_date(self, date_str):
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return None

    def _is_date_in_range(self, date_str, start_date, end_date):
        date = self._parse_date(date_str)
        if date is None:
            return False

        start = self._parse_date(start_date) if start_date else None
        end = self._parse_date(end_date) if end_date else None

        if start and date < start:
            return False
        if end and date > end:
            return False
        return True

    def find_stocks_by_listed_date(self, listed_start, listed_end, output_file=None):
        print(f"\n=== 按上市日期筛选股票 ===")
        print(f"条件: 上市日期 >= {listed_start}, 上市日期 <= {listed_end}")

        matched_stocks = []
        for code, info in self.base_info.items():
            if self._is_date_in_range(info.get('listed_date', ''), listed_start, listed_end):
                matched_stocks.append(code)

        matched_stocks.sort()
        print(f"共找到 {len(matched_stocks)} 只股票")

        print("\n股票列表:")
        codes_str = ','.join([f'"{code}"' for code in matched_stocks])
        print(codes_str)

        if output_file:
            out_dir = 'out'
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
            out_path = os.path.join(out_dir, output_file)
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(codes_str)
            print(f"股票列表已保存到: {out_path}")

        return matched_stocks

    def _load_stock_list_from_file(self, file_path):
        stock_codes = []
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            return stock_codes

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                code = line.strip()
                if code:
                    code = code.replace(',', '').replace('"', '').strip()
                    code = code.zfill(6)
                    stock_codes.append(code)
        return stock_codes

    def analyze_stocks(self, input_file, output_file=None, listed_start=None, listed_end=None,
                       delisted_start=None, delisted_end=None):
        result = {
            'total_in_file': 0,
            'found_in_base': 0,
            'listed_filter_count': 0,
            'listed_filter_result': 0,
            'listed_filter_stocks': [],
            'delisted_filter_count': 0,
            'delisted_filter_result': 0,
            'industry_classification': {}
        }

        stock_codes = self._load_stock_list_from_file(input_file)
        result['total_in_file'] = len(stock_codes)
        print(f"\n=== 股票分析: {input_file} ===")
        print(f"文件中的股票数量: {result['total_in_file']}")

        base_info_stocks = []
        for code in stock_codes:
            if code in self.base_info:
                base_info_stocks.append(code)

        result['found_in_base'] = len(base_info_stocks)
        print(f"在基本信息中找到的股票数量: {result['found_in_base']}")

        if listed_start or listed_end:
            listed_filtered = []
            not_listed_filtered = []
            for code in base_info_stocks:
                info = self.base_info[code]
                if self._is_date_in_range(info.get('listed_date', ''), listed_start, listed_end):
                    listed_filtered.append(code)
                else:
                    not_listed_filtered.append(code)

            result['listed_filter_count'] = len(base_info_stocks) - len(listed_filtered)
            result['listed_filter_result'] = len(listed_filtered)
            result['listed_filter_stocks'] = listed_filtered
            print(f"\n--- 上市日期筛选 ---")
            print(f"条件: {'上市日期 >= ' + listed_start if listed_start else ''} "
                  f"{'上市日期 <= ' + listed_end if listed_end else ''}")
            print(f"不符合条件的股票数量: {result['listed_filter_count']}")
            print(f"符合条件的股票数量: {result['listed_filter_result']}")

            base_info_stocks = not_listed_filtered
        else:
            result['listed_filter_result'] = len(base_info_stocks)

        if delisted_start or delisted_end:
            delisted_excluded = []
            for code in base_info_stocks:
                info = self.base_info[code]
                delisted_date = info.get('delisted_date', '')

                is_delisted_in_range = False
                if delisted_date and delisted_date != '2038-01-01':
                    if self._is_date_in_range(delisted_date, delisted_start, delisted_end):
                        is_delisted_in_range = True

                if not is_delisted_in_range:
                    delisted_excluded.append(code)

            result['delisted_filter_count'] = len(base_info_stocks) - len(delisted_excluded)
            result['delisted_filter_result'] = len(delisted_excluded)
            print(f"\n--- 退市日期筛选 ---")
            print(f"条件: {'退市日期 >= ' + delisted_start if delisted_start else ''} "
                  f"{'退市日期 <= ' + delisted_end if delisted_end else ''}")
            print(f"不符合条件的股票数量（已退市）: {result['delisted_filter_count']}")
            print(f"符合条件的股票数量（未退市）: {result['delisted_filter_result']}")

            base_info_stocks = delisted_excluded
        else:
            result['delisted_filter_result'] = len(base_info_stocks)

        if base_info_stocks:
            industry_groups = defaultdict(list)
            for code in base_info_stocks:
                info = self.base_info[code]
                industry = info.get('industry_level2', '未知')
                industry_groups[industry].append({
                    'code': code,
                    'name': info.get('stock_name', ''),
                    'industry': industry
                })

            result['industry_classification'] = dict(industry_groups)
            print(f"\n--- 二级行业分类结果 ---")
            print(f"共有 {len(industry_groups)} 个二级行业:")
            for industry, stocks in sorted(industry_groups.items(), key=lambda x: len(x[1]), reverse=True):
                print(f"  {industry}: {len(stocks)} 只")

        if output_file:
            out_dir = 'out'
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
            out_path = os.path.join(out_dir, output_file)
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n分析结果已保存到: {out_path}")

        return result

if __name__ == '__main__':
    analyzer = StockAnalyzer()
    listed_get = 1
    analyze_stocks = 0
    if listed_get:  
        analyzer.find_stocks_by_listed_date(
            listed_start='2019-01-01',
            listed_end='2019-12-31',
            output_file='2019listed.txt'
        )
    if analyze_stocks:
        result = analyzer.analyze_stocks(
            input_file='2021-2023xiadie.txt',
            output_file='2021-2023xiadie_analysis.json',
            listed_start='2019-01-01',
            listed_end='2020-12-31',
            delisted_start='2019-01-01',
            delisted_end='2023-12-31'
        )
