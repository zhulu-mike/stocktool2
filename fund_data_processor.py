# coding=utf-8

import json
import requests


class FundDataProcessor:
    def compare_close_with_nav(self, fund_code):
        """
        逐行比较fund_data和fund_lsjz_data里指定基金的数据，
        用fund_data的收盘除以fund_lsjz_data里的DWJZ，返回结果列表。
        匹配规则：以日期为key，若两边都存在该日期则计算。
        """
        fund_data = self.fund_data.get(fund_code, [])
        fund_lsjz_data = self.fund_lsjz_data.get(fund_code, [])
        # 构建日期到DWJZ的映射
        nav_map = {}
        for row in fund_lsjz_data:
            date = row.get("FSRQ")
            nav = row.get("DWJZ")
            if date and nav:
                try:
                    nav_map[date] = float(nav)
                except Exception:
                    continue
        result = []
        alpha_value = 0
        yijia_count = 0
        yijia_history = []
        zhejia_count = 0
        zhejia_history = []
        step_count = 1
        for row in fund_data:
            date = row.get("\ufeff时间") or row.get("date")
            #需要把date转成2020-01-01格式，date原来是2020/01/01格式
            date = date.replace("/", "-")
            close = row.get("收盘") or row.get("close")
            if date and close and date in nav_map:
                try:
                    close_val = float(close)
                    nav_val = nav_map[date]
                    ratio = close_val / nav_val * 100 - 100  # 乘以100作为百分比
                    step_count = step_count + 1
                    if ratio > 0.2:
                        #溢价，卖出然后申购，获得超额
                        alpha_value += ratio-0.2
                        yijia_count += 1
                        yijia_history.append((date, ratio-0.2))
                        step_count = 0
                    elif ratio < -0.55 and step_count > 6:
                        #折价，赎回然后买入，获得超额
                        alpha_value += (-0.55 - ratio)
                        zhejia_count += 1
                        zhejia_history.append((date, -0.55 - ratio))
                        step_count = 0
                except Exception:
                    ratio = None
                result.append({"date": date, "close": close_val, "DWJZ": nav_val, "ratio": ratio})
        print(f"基金 {fund_code} 的溢价次数: {yijia_count}, 折价次数: {zhejia_count}, 超额收益率估算: {alpha_value:.2f}%")
        #print("溢价历史记录:", yijia_history)
        #print("折价历史记录:", zhejia_history)
        return result
    def sync_fund_history_with_remote(self, fund_code, headers=None):
        """
        读取stocks/fund/{fund_code}.json（历史净值数据），如不存在或数据落后于csv，则远程抓取补齐。
        """
        import os
        import json
        json_path = os.path.join("stocks", "fund", f"{fund_code}.json")
        csv_data = self.load_fund_csv(fund_code)
        csv_latest_date = None
        if csv_data:
            last_row = csv_data[-1]
            csv_latest_date = last_row.get("\ufeff时间") or last_row.get("date")
            csv_latest_date = csv_latest_date.replace("/", "-")
        # 读取本地json
        local_data = []
        local_latest_date = None
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                try:
                    local_data = json.load(f)
                    if local_data:
                        self.fund_lsjz_data = {fund_code: local_data}
                        last_row = local_data[-1]
                        local_latest_date = last_row.get("FSRQ") or last_row.get("date")
                except Exception:
                    local_data = []
        # 判断是否需要远程抓取
        need_fetch = (not local_data) or (csv_latest_date and (not local_latest_date or csv_latest_date > local_latest_date))
        if need_fetch:
            print(f"本地数据缺失或过期，正在远程抓取 {fund_code} 的历史净值数据...")
            remote_data = self.fetch_fund_history_from_url(fund_code)
            # 合并本地和远程数据，去重，按日期排序
            def get_date(row):
                return row.get("FSRQ") or row.get("date") 
            # 合并并去重（以日期为key）
            merged = {get_date(row): row for row in (local_data + remote_data) if get_date(row)}
            # 按日期升序排列
            merged_list = [merged[k] for k in sorted(merged.keys())]
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(merged_list, f, ensure_ascii=False, indent=2)
            self.fund_lsjz_data = {fund_code: merged_list}
            return merged_list
        else:
            print(f"本地数据已是最新，无需抓取。")
            return local_data

    def get_message(code, webhook_url, headers=None):
        response = requests.get(webhook_url, headers=headers)
        if response.status_code == 200:
            return response.text
        else:
            print("消息发送失败", code)
            return ""
    
    def fetch_fund_history_from_url(self, fund_code, start_date="2023-01-01"):
        """
        从self.url获取指定基金的历史净值数据，支持自定义headers。
        返回请求到的原始数据（如json或text）。
        """
        if not self.url:
            raise ValueError("未设置url")
        url2 = self.url.replace("$FUND$", fund_code)
        default_headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
            "referer": "https://fundf10.eastmoney.com/"  # 根据需要设置
        }
        is_end = False
        i = 1
        lsjz_list = []
        while True:
            url3 = url2.replace("$PAGE$", str(i))
            url3 = url3.replace("$START$", start_date)
            response = self.get_message(url3, default_headers)
            if response == "":
                
                continue
            #print(response, url3)
            i = i + 1
            ret = json.loads(response)
            if ret.get("Data") and ret["Data"].get("LSJZList"):
                LSJZList = ret["Data"]["LSJZList"]
                lsjz_list.extend(LSJZList)
                if LSJZList[-1].get("FSRQ") <= start_date:
                    is_end = True
                    break
            else:
                print(f"未获取到基金 {fund_code} 的历史净值数据 {i}")
                break
        return lsjz_list

    def load_fund_csv(self, fund_code):
        """
        加载stocks/fund目录下指定基金代码的csv文件，返回格式化后的数据列表。
        """
        import os
        import csv
        fund_dir = os.path.join("stocks", "fund")
        file_path = os.path.join(fund_dir, f"{fund_code}.csv")
        data_list = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                data_list.append(dict(row))
        # 可选：保存到成员变量
        self.fund_data = {fund_code: data_list}
        #print(data_list)
        return data_list
    def process(self):
        """
        处理基金数据的主函数，具体逻辑待实现。
        """
        self.sync_fund_history_with_remote("161725")  # 示例调用
        self.compare_close_with_nav("161725")  # 示例调用
        self.sync_fund_history_with_remote("160637")  # 示例调用
        self.compare_close_with_nav("160637")  # 示例调用
        pass
    """
    基金数据处理类：用于加载、分析和处理基金相关数据。
    用法示例：
        processor = FundDataProcessor()
        # processor.load_data(...)
        # processor.analyze(...)
    """
    def __init__(self, url=None):
        """
        初始化基金数据处理器，可传入数据源url。
        """
        self.url = url

    # 你可以在这里添加更多处理基金数据的方法
