class StocKBaseInfo:
    def __init__(self, level="", birth_date="", quanshang="", long_name="", boss_name="", 
                 main_business="", stock_name="", stock_code="", introduce=""):
        self.stock_code = stock_code #证券代码
        self.stock_name = stock_name #证券简称
        self.level = level #市场分层
        self.birth_date = birth_date #挂牌日期
        self.quanshang = quanshang #持续督导券商
        self.long_name = long_name #公司全称
        self.boss_name = boss_name #实际控制人
        self.main_business = main_business #主营业务
        self.introduce = introduce #公司简介

    def __repr__(self):
        return (f"StocKBaseInfo(stock_code={self.stock_code}, "
                f"stock_name={self.stock_name}, market={self.market}, "
                f"industry={self.industry}, listing_date={self.listing_date})")