import json
import re
import os
import time
import random
import requests


class FetchAllAStocks:
    def __init__(self):
        self.api_url = 'https://datacenter-web.eastmoney.com/api/data/v1/get'
        self.stocks_dir = 'stocks'
        if not os.path.exists(self.stocks_dir):
            os.makedirs(self.stocks_dir)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://data.eastmoney.com/',
        })

    def fetch_page(self, page_no, page_size=500):
        """获取单页A股列表，返回code列表和总页数"""
        params = {
            'sortColumns': 'HOLD_NOTICE_DATE,SECURITY_CODE',
            'sortTypes': '-1,-1',
            'pageSize': page_size,
            'pageNumber': page_no,
            'reportName': 'RPT_HOLDERNUMLATEST',
            'columns': 'SECURITY_CODE',
            'quoteColumns': 'f2,f3',
            'quoteType': 0,
            'source': 'WEB',
            'client': 'WEB',
        }
        resp = self.session.get(self.api_url, params=params, timeout=15)
        text = resp.text
        # 去除JSONP外层
        match = re.search(r'\((\{.*\})\)\s*;?\s*$', text)
        if not match:
            try:
                data = json.loads(text)
            except Exception as e:
                print(f"第{page_no}页解析失败: {e}")
                return [], 0
        else:
            data = json.loads(match.group(1))
        if not data.get('success'):
            print(f"第{page_no}页返回失败: {data.get('message')}")
            return [], 0
        result = data.get('result', {}) or {}
        pages = result.get('pages', 0)
        rows = result.get('data', []) or []
        codes = [item.get('SECURITY_CODE') for item in rows if item.get('SECURITY_CODE')]
        return codes, pages

    def fetch_all(self):
        """获取全部A股代码"""
        all_codes = []
        page_no = 1
        page_size = 500
        total_pages = None
        while True:
            codes, fetched_pages = self.fetch_page(page_no, page_size)
            if total_pages is None:
                total_pages = fetched_pages
                print(f"总页数: {total_pages}")
            print(f"第{page_no}页: 获取{len(codes)}条, 累计{len(all_codes) + len(codes)}")
            all_codes.extend(codes)
            if not codes or len(codes) < page_size:
                break
            if total_pages and page_no >= total_pages:
                break
            if page_no % 5 == 0:
                print(f"已抓取{page_no}页，额外暂停5秒")
                time.sleep(5)
            page_no += 1
            time.sleep(random.uniform(1.7, 2.5))
        # 去重保序
        seen = set()
        unique_codes = []
        for c in all_codes:
            if c not in seen:
                seen.add(c)
                unique_codes.append(c)
        print(f"\n完成！共{len(unique_codes)}只A股")
        return unique_codes


if __name__ == '__main__':
    FetchAllAStocks().fetch_all()
