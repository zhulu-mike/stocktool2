import stock_announce_processor
import json

global all_a_stocks
all_a_stocks = []

root_dir = "stocks/"
base_dir = "base/"
announce_dir = "announce/"
all_a_file = "all_a.json"

def loadAllA():
    f = root_dir + all_a_file
    with open(f, 'r', encoding='utf-8') as file:
        datas = json.load(file)
        stock_num = len(datas)
        for i in range(stock_num):
            all_a_stocks.append(datas[i])
        print("local_a_stock_num=", stock_num)

loadAllA()
stock_announce_processor = stock_announce_processor.StockAnnounceProcessor(root_dir, announce_dir)
stock_announce_processor.load_all_announcements()
stock_announce_processor.UpdateAllStockAnnounce(all_a_stocks, True,4987)
