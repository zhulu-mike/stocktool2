class StockAnnounceInfo:
    def __init__(self, notice_date="", title="", art_code=""):
        self.notice_date = notice_date #公告日期
        self.title = title #公告标题
        self.art_code = art_code #公告代码
  
    def __repr__(self):
        return (f"StockAnnounceInfo(date={self.date}, "
                f"title={self.title}, "
                f"art_code={self.art_code})")
    
    import os
    import json

    def load_all_announcements(directory="stocks/announce"):
        """
        加载本地所有股票公告数据。
        返回一个列表，每个元素为一个公告数据（dict）。
        """
        announcements = []
        dir_path = os.path.abspath(directory)
        for filename in os.listdir(dir_path):
            if filename.endswith(".json"):
                file_path = os.path.join(dir_path, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        announcements.append(data)
                    except Exception as e:
                        print(f"读取 {filename} 时出错: {e}")
        return announcements

    