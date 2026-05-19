# coding=utf-8
from datetime import datetime, timedelta

class StockAnnounceProcessor:
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
        processor = StockAnnounceProcessor(all_stocks_announce)
        processor.process()
        result = processor.result
    """
    def __init__(self, all_announcements):
        """
        all_announcements: dict, {stock_code: [公告列表]}
        """
        self.all_announcements = all_announcements
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


