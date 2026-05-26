# coding=utf-8
from datetime import datetime, timedelta
import json
import os

import requests

import stock_announce_info

class StockAnnounceProcessor:
    #获取股票的公告
    stock_announce_url = "https://np-anotice-stock.eastmoney.com/api/security/ann?cb=&sr=-1&page_size=100&page_index=$PAGE_INDEX$&ann_type=A&client_source=web&stock_list=000951&f_node=0&s_node=0"
    #获取股票某个公告的具体内容
    stock_announce_detail_url = "https://pdf.dfcfw.com/pdf/H2_$ART_CODE$_1.pdf"
    #存储股票公告信息
    all_stocks_announce = {}

    def print_intervals_over(self, days_threshold):
        """
        打印结果中间隔时间超过 days_threshold 的数据。
        """
        found = False
        for code, entry in self.result.items():
            days = entry.get("days_interval")
            if days is not None and days > days_threshold:
                print(f"股票代码: {code}")
                print(f"数据: {entry}")
                found = True
        if not found:
            print(f"没有间隔时间超过 {days_threshold} 天的数据")
    def find_max_interval_and_print(self):
        """
        从结果中找出间隔时间最长的数据并打印出来。
        """
        max_code = None
        max_entry = None
        max_days = -1
        for code, entry in self.result.items():
            days = entry.get("days_interval")
            if days is not None and days > max_days:
                max_days = days
                max_code = code
                max_entry = entry
        if max_code:
            print(f"间隔时间最长的股票代码: {max_code}")
            print(f"数据: {max_entry}")
        else:
            print("没有找到有效的间隔数据")
    """
    公告处理类：遍历所有股票公告，筛选并计算日期间隔。
    用法：
        processor = StockAnnounceProcessor(root_dir, announce_dir)
        processor.process()
        result = processor.result
    """
    def __init__(self, root_dir, announce_dir):
        """
        all_announcements: dict, {stock_code: [公告列表]}
        """
        self.all_announcements = {}
        self.result = {}  # {stock_code: {li_an_date, xing_zheng_date, days_interval}}
        self.tuishi = []
        self.tuishi_date = {}
        self.other = []
        self.other_date = {}
        self.other2 = []
        self.other2_end_date = {}
        self.other2_start_date = {}
        self.have_tuishi = []
        self.chongzheng = []
        self.pre_chongzheng = []
        self.have_change_main_folder = []
        self.root_dir = root_dir
        self.announce_dir = announce_dir

    def searchOther(self, start, end):
        """
        搜索有其他警示风险的公告
        """
        c = 0
        for stock_code, announces in self.all_announcements.items():
            for ann in announces:
                title = ann.get("title", "")
                notice_date = ann.get("notice_date", "")
                if notice_date >= end:
                    continue
                if notice_date < start:
                    break
                if "*ST" not in title and "其他风险" in title and ("实施" in title or "实行" in title) and "牌" in title and "撤销" not in title and "退市风险" not in title:
                    print(f"{stock_code} {notice_date}: {title}")
                    c = c + 1
                    self.other.append(stock_code)
                    #把notice_date往后延20天
                    new_date = datetime.strptime(notice_date.split(" ")[0], "%Y-%m-%d") + timedelta(days=20)
                    self.other_date[stock_code] = new_date.strftime("%Y-%m-%d")
                    break
        
        print("total=", c)
    def searchOtherByTitle(self, start, end):
        """
        搜索有其他警示风险的公告
        """
        c = 0
        delay = 20
        for stock_code, announces in self.all_announcements.items():
            f = False
            i = 0
            for ann in announces:
                i = i + 1
                title = ann.get("title", "")
                notice_date = ann.get("notice_date", "")
                if notice_date >= end:
                    continue
                if notice_date < start:
                    break
                if "*ST" in title:
                    if f:
                        self.other2_start_date[stock_code] = (datetime.strptime(notice_date.split(" ")[0], "%Y-%m-%d") + timedelta(days=delay)).strftime("%Y-%m-%d")
                        break
                    continue
                if "ST" in title:
                    if not f:
                        c = c + 1
                        f = True
                        self.other2.append(stock_code)
                        if i == 1:
                            self.other2_end_date[stock_code] = datetime.now().strftime("%Y-%m-%d")
                        else:
                            self.other2_end_date[stock_code] = notice_date.split(" ")[0]
                        self.other2_start_date[stock_code] = notice_date.split(" ")[0]
                    else:
                        self.other2_start_date[stock_code] = notice_date.split(" ")[0]
                    continue
                else:
                    if f:
                        self.other2_start_date[stock_code] = (datetime.strptime(notice_date.split(" ")[0], "%Y-%m-%d") + timedelta(days=delay)).strftime("%Y-%m-%d")
                        break
                    
        
        print("total=", c)


    def searchTuiShi(self, start, end):
        """
        搜索有退市风险的公告
        """
        c = 0
        delay = 10
        for stock_code, announces in self.all_announcements.items():
            for ann in announces:
                title = ann.get("title", "")
                notice_date = ann.get("notice_date", "")
                if notice_date >= end:
                    continue
                if notice_date < start:
                    break
                if "退市风险" in title and ("实施" in title or "实行" in title) and "牌" in title and "撤销" not in title:
                    print(f"{stock_code} {notice_date}: {title}")
                    c = c + 1
                    self.tuishi.append(stock_code)
                    #把notice_date往后延5天
                    new_date = datetime.strptime(notice_date.split(" ")[0], "%Y-%m-%d") + timedelta(days=delay)
                    self.tuishi_date[stock_code] = new_date.strftime("%Y-%m-%d")
                    break
        
        print("total=", c)

    def searchHaveTuiShi(self, start, end):
        """
        搜索已经退市的公告
        """
        c = 0
        for stock_code, announces in self.all_announcements.items():
            for ann in announces:
                title = ann.get("title", "")
                notice_date = ann.get("notice_date", "")
                if notice_date >= end:
                    continue
                if notice_date < start:
                    break
                if "终止上市" in title and "风险" not in title and "申请" not in title and "子公司" not in title:
                    print(f"{stock_code} {notice_date}: {title}")
                    c = c + 1
                    self.have_tuishi.append(stock_code)
                    break
        print("total=", c)

    def searchChongZheng(self, start_date, end_date):
        """
        搜索有重整的公告
        """
        for stock_code, announces in self.all_announcements.items():
            if stock_code in ['11002713']:
                continue
            for ann in announces:
                title = ann.get("title", "")
                notice_date = ann.get("notice_date", "")
                if notice_date >= end_date:
                    continue
                if notice_date < start_date:
                    break
                if "受理" in title and ("公司重整" in title) \
                    and "未被" not in title \
                    and "股东" not in title and "债务人" not in title and \
                    ("公司及子公司重整" in title or "子公司" not in title):
                    print(f"{stock_code} {notice_date}: {title}")
                    self.chongzheng.append(stock_code)
    def searchPreChongZheng(self, start_date, end_date):
        """
        搜索有预重整的公告
        """
        for stock_code, announces in self.all_announcements.items():
            for ann in announces:
                title = ann.get("title", "")
                notice_date = ann.get("notice_date", "")
                if notice_date >= end_date:
                    continue
                if notice_date < start_date:
                    break
                if "预重整" in title and "子公司" not in title and "股东" not in title:
                    self.pre_chongzheng.append(stock_code)
                    break

    def process(self):
        for stock_code, announces in self.all_announcements.items():
            li_an_date = None
            xing_zheng_date = None
            
            # 只遍历一次，遇到立案告知就退出，期间顺便记录行政处罚
            for ann in announces:
                title = ann.get("title", "")
                date = ann.get("notice_date", "")
                if not xing_zheng_date and ("行政处罚" in title and "告知书" in title) and ("关于收到" in title or "关于公司收到" in title or "关于公司及" in title or "关于公司、" in title):
                    xing_zheng_date = date
                if ("立案告知" in title or "立案调查" in title) and "公安" not in title and "进展" not in title and ("关于收到" in title or "关于公司收到" in title or "关于公司及" in title):
                    li_an_date = date
                    break
            if li_an_date:
                entry = {"li_an_date": li_an_date}
                try:
                    try:
                        d1 = datetime.strptime(li_an_date, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        d1 = datetime.strptime(li_an_date, "%Y-%m-%d")
                    if xing_zheng_date:
                        try:
                            d2 = datetime.strptime(xing_zheng_date, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            d2 = datetime.strptime(xing_zheng_date, "%Y-%m-%d")
                        entry["xing_zheng_date"] = xing_zheng_date
                    else:
                        d2 = datetime.now()
                    days_interval = abs((d2 - d1).days)
                except Exception as e:
                    print(e)
                    days_interval = None
                entry["days_interval"] = days_interval
                self.result[stock_code] = entry
    def searchHaveChangeMainFolder(self):
        """
        搜索有实控人变更的公告
        """
        c = 0
        for stock_code, announces in self.all_announcements.items():
            if stock_code > "600000":
                continue
            if stock_code in ['300710','300620','000159'
                              , '000595','000615','000702','000762','000813','000818'
                              , '000835', '000868', '000918', '002024','002083'
                              , '002163', '002160', '002226', '002252', '002308'
                              , '002313']:
                continue
            for ann in announces:
                title = ann.get("title", "")
                notice_date = ann.get("notice_date", "")     
                if notice_date < "2020-01-01 00:00:00":
                    break
                if "继承" or "子公司" or "筹划" in title or "拟" in title or "签署" in title or "终止" in title or "参股公司" in title:
                    continue
                if "控制权发生变更" in title or "控制权变更" in title or "控制权33" in title :
                    if notice_date >= "2023-01-01 00:00:00":
                        break
                    print(f"{stock_code} {notice_date}: {title}")
                    c = c + 1
                    self.have_change_main_folder.append(stock_code)
                    break
        print("total=", c)

    def try_load_all_announcements(self):
        if len(self.all_stocks_announce) == 0:
            self.load_all_announcements()
    def load_all_announcements(self):
        """
        加载本地所有股票公告数据。
        """
        directory = self.root_dir + self.announce_dir
        dir_path = os.path.abspath(directory)
        for filename in os.listdir(dir_path):
            if filename.endswith(".json"):
                file_path = os.path.join(dir_path, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        self.all_stocks_announce[filename[:-5]] = data  # 去掉 .json 后缀作为股票代码
                    except Exception as e:
                        print(f"读取 {filename} 时出错: {e}")
        
    # 更新所有股票的公告
    def UpdateAllStockAnnounce(self, all_a_stocks, f=False, start=0):
        for i in range(start, len(all_a_stocks)):
            code = all_a_stocks[i]
            print("process ", i, " code=", code)
            self.getStockAnnounceInfo(code,f)
            
    def getStockAnnounceInfo(self, code, f=False):
        stock_announce = self.all_stocks_announce.get(code, [])
        stock_announce_len = len(stock_announce)
        if stock_announce_len == 0:
            self.all_stocks_announce[code] = stock_announce
        elif not f:
            return
        print(" code=", code)
        url2 = self.stock_announce_url.replace("000951", code)
        need_update = False
        is_end = False
        i = 1
        temp_arr = []
        while True:
            url3 = url2.replace("$PAGE_INDEX$", str(i))
            ret = self.get_message(code, url3)
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
            self.all_stocks_announce[code] = stock_announce
            f = self.root_dir + self.announce_dir + code + ".json"
            with open(f, 'w', encoding='utf-8') as file:
                json.dump(stock_announce, file, indent=4, ensure_ascii=False)

    def get_message(self, code, webhook_url, headers=None):
        response = requests.get(webhook_url, headers=headers)
        if response.status_code == 200:
            return response.text
        else:
            print("消息发送失败", code)
            return ""
    
    def search_announcements_by_keyword(self, keywords, start_date=None, end_date=None):
        """
        根据关键字搜索公告，支持日期范围筛选。
        
        :param keywords: 关键字列表或单个关键字字符串
        :param start_date: 开始日期（格式：YYYY-MM-DD）
        :param end_date: 结束日期（格式：YYYY-MM-DD）
        :return: 搜索结果列表，每个元素包含股票代码、公告日期、公告标题、art_code
        """
        # 确保关键字是列表
        if isinstance(keywords, str):
            keywords = [keywords]
        
        # 先确保加载了所有公告
        self.try_load_all_announcements()
        
        results = []
        for stock_code, announces in self.all_stocks_announce.items():
            for ann in announces:
                title = ann.get("title", "")
                notice_date = ann.get("notice_date", "")
                art_code = ann.get("art_code", "")
                
                # 提取日期部分用于比较
                notice_date_only = notice_date.split(" ")[0] if notice_date else ""
                
                # 检查日期范围
                is_in_date_range = True
                if start_date and notice_date_only < start_date:
                    is_in_date_range = False
                if end_date and notice_date_only > end_date:
                    is_in_date_range = False
                
                # 检查是否包含任何一个关键字
                if is_in_date_range and any(keyword in title for keyword in keywords):
                    results.append({
                        "stock_code": stock_code,
                        "title": title,
                        "notice_date": notice_date,
                        "art_code": art_code
                    })
        
        # 按日期排序（最新的在前）
        results.sort(key=lambda x: x["notice_date"], reverse=True)
        return results