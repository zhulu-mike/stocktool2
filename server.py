from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import http.client
import socket
import time
import traceback
import json
import os

# 公告处理器（延迟导入）
stock_announce_processor = None

# 全局变量，用于缓存股票标签数据和股票基础数据
stock_labels_cache = {}
stock_base_cache = {}
DATA_FILE = "stocks/stock_label.json"
BASE_FILE = "stocks/all_base.json"

def load_stock_labels():
    """加载股票标签数据到内存"""
    global stock_labels_cache
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                stock_labels_cache = json.load(f)
            print(f"已加载股票标签数据，共 {len(stock_labels_cache)} 只股票")
        except Exception as e:
            print(f"加载股票标签数据失败: {e}")
            stock_labels_cache = {}
    else:
        stock_labels_cache = {}
        print("股票标签文件不存在，创建空缓存")

def load_stock_base():
    """加载股票基础数据到内存"""
    global stock_base_cache
    if os.path.exists(BASE_FILE):
        try:
            # 尝试使用UTF-8编码读取
            with open(BASE_FILE, "r", encoding="utf-8") as f:
                base_data = json.load(f)
            stock_base_cache = {item["stock_code"]: item["stock_name"] for item in base_data}
            print(f"已加载股票基础数据，共 {len(stock_base_cache)} 只股票")
        except UnicodeDecodeError:
            # 如果UTF-8失败，尝试GBK编码（中文Windows常见编码）
            try:
                with open(BASE_FILE, "r", encoding="gbk") as f:
                    base_data = json.load(f)
                stock_base_cache = {item["stock_code"]: item["stock_name"] for item in base_data}
                print(f"已加载股票基础数据(GBK)，共 {len(stock_base_cache)} 只股票")
            except Exception as e:
                print(f"加载股票基础数据失败(GBK): {e}")
                stock_base_cache = {}
        except Exception as e:
            print(f"加载股票基础数据失败: {e}")
            stock_base_cache = {}
    else:
        stock_base_cache = {}
        print("股票基础数据文件不存在")

def get_stock_name(stock_code):
    """根据股票代码获取股票名称"""
    if stock_code in stock_labels_cache and stock_labels_cache[stock_code].get("name"):
        return stock_labels_cache[stock_code]["name"]
    if stock_code in stock_base_cache:
        return stock_base_cache[stock_code]
    return stock_code

def init_announce_processor():
    global stock_announce_processor
    if stock_announce_processor is None:
        import stock_announce_processor as sap
        stock_announce_processor = sap.StockAnnounceProcessor("", "stocks/announce/")
        stock_announce_processor.load_all_announcements()
        print("公告处理器初始化完成")

REMOTE_BASE = "https://push2.eastmoney.com/api/qt/clist/get"
FIELD_LIST = "f12,f13,f14,f1,f2,f4,f3,f152,f232,f233,f234,f229,f230,f231,f235,f236,f154,f237,f238,f239,f240,f241,f227,f242,f26,f243"
FILTER = "b:MK0354"
UT = "fa5fd1943c7b386f172d6893dbfba10b"
WBP2U = "|0|0|0|web"
COOKIE = "qgqp_b_id=c602561399c14fa86676fd697988d417; st_nvi=PSnFaLpR8DVTq6FiTEaAg5fb5; AUTH_FUND.EASTMONEY.COM_GSJZ=AUTH*TTJJ*TOKEN; nid18=0e17cb22ecf6960f4858bfd8cbdced17; nid18_create_time=1773137308838; gviem=hAdwL4sBO0qxKoAeDWiiUad92; gviem_create_time=1773137308838; fullscreengg=1; fullscreengg2=1; st_si=78234811771278; has_jump_to_web=1; wsc_checkuser_ok=1; p_origin=https%3A%2F%2Fpassport2.eastmoney.com; st_sn=24; st_psi=20260518092111880-0-1219735377; st_asi=20260518092111880-0-1219735377-grzx.dlym.dxdl.dl-2; mtp=1; ct=XVvzFAHEIVL_W71AeSFlsACiKxk3GyBjNoLQJzZ1zR-lRJ7l6NL4_iNyQsE7mwaeCYK1I1qCsPkqf8Z2negQ0xyC00VdSQ8szDXPaT7aetLqGV4fLYxdKadDa2iBC9Fnwcgxiyq5ywL-CfiZYngLwn7cT86xatqpAt5XQblcLd4; ut=FobyicMgeV7bfas_M05TDCCfixGq5u61uTr05XZSFlyyaT025fNXNRO-NuLSGFjil6CJRyOHCAsxVV18fE4GqFz9t8p690tQRdONqLVPO_NwVVfYGl2t_wIyvEFTU9yyH_J2ec1bVmm72dY0TygqY4y_frj5KKcfuf0SYR9xzdORfqY6rvMNmj7fTUWHqOzEA9pCw3RNWLCXmjqhUs9AJNCquLp3NWMJ8h8BZJbNwHd53NgkdRv_liebEUYzomSXvGZHQQZL-9zfDKp3NDPT9dM1b43dIHU0; pi=3046094285466864%3Bm3046094285466864%3Briverriverriver%3BTKeYW30mHhkuMtGMpnKOXt3z1PmS4N7Kfyp2qtaska%2BV66j6cSL6UACo6t9DiCYtIER0uTNkESaXnNefvV4MfoVffRn9Yd2tw1i7gHKV1SxuI0aGYX2IGWx5vRG5uXYGta8BbnQtSGarN8LHLxbHR2sP%2FjIA1UnIwLPDRkfptg5TLyJHbkyChq8vTiHMNiF2Mp5kX2jr%3BYiDZP1U1jigOHg%2FfMse7O3V%2FjoujGIcQEmk3nFN6GS8TB59MAeSJV4P05Ms6JY%2BMkgntkunKcHcOFCbfRxXDYJTtQF2KP4p3jkDRKv0F8ICRkSU93aihvl2DR%2BO8bq09dPQQZD2cCOsOlzkQeNCoE9E8V7xcsg%3D%3D; uidal=3046094285466864riverriverriver; sid=2505195; vtpst=|; st_pvi=60390339319309; st_sp=2025-08-25%2022%3A04%3A09; st_inirUrl=https%3A%2F%2Fwww.baidu.com%2Flink"
MAX_RETRIES = 3
RETRY_BASE_DELAY = 0.5


def is_retryable_exception(exc):
    return isinstance(
        exc,
        (
            socket.timeout,
            ConnectionResetError,
            ConnectionAbortedError,
            BrokenPipeError,
            ConnectionRefusedError,
            http.client.RemoteDisconnected,
            OSError,
        ),
    )


class RealtimeProxyHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/realtime-proxy":
            self.handle_realtime_proxy(parsed.query)
        elif parsed.path == "/search-announce":
            self.handle_search_announce(parsed.query)
        elif parsed.path == "/stocks/stock_label.json":
            self.handle_get_stock_labels()
        else:
            super().do_GET()
    
    def do_PUT(self):
        print("PUT request received")
        parsed = urlparse(self.path)
        print(f"Request path: {parsed.path}")
        if parsed.path == "/stocks/stock_label.json":
            print("Handling save stock labels")
            self.handle_save_stock_labels()
        else:
            print(f"Path not found: {parsed.path}")
            self.send_response(404)
            self.end_headers()
    
    def handle_get_stock_labels(self):
        """处理获取股票标签数据请求"""
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(stock_labels_cache, ensure_ascii=False).encode("utf-8"))
            print(f"已返回股票标签数据，共 {len(stock_labels_cache)} 只股票")
        except Exception as exc:
            print(f"获取股票标签数据失败: {exc}", flush=True)
            traceback.print_exc()
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))
    
    def handle_save_stock_labels(self):
        """处理保存股票标签数据请求"""
        global stock_labels_cache
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            print(data)
            # 更新内存缓存，同时自动补充股票名称
            for stock_code, stock_data in data.items():
                print(f"自动补充股票名称前: {stock_code} -> {stock_data['name']}")
                if not stock_data.get("name") or stock_data["name"] == stock_code:
                    stock_data["name"] = get_stock_name(stock_code)
                    print(f"自动补充股票名称: {stock_code} -> {stock_data['name']}")
            
            stock_labels_cache = data
            
            # 保存到文件
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(stock_labels_cache, f, ensure_ascii=False, indent=2)
            
            print("股票标签数据已保存")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            # 返回更新后的数据，包含正确的股票名称
            self.wfile.write(json.dumps({"success": True, "data": stock_labels_cache}, ensure_ascii=False).encode("utf-8"))
        except Exception as exc:
            print(f"保存股票标签时发生错误: {exc}", flush=True)
            traceback.print_exc()
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))
    
    def handle_search_announce(self, query_string):
        params = parse_qs(query_string)
        keywords = params.get("keywords", [])
        
        if not keywords:
            self.send_response(400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "缺少关键字参数"}).encode("utf-8"))
            return
        
        # 获取日期范围参数和股票代码参数
        start_date = params.get("start_date", [None])[0]
        end_date = params.get("end_date", [None])[0]
        stock_code = params.get("stock_code", [None])[0]
        
        try:
            # 初始化公告处理器
            init_announce_processor()
            
            # 搜索公告（支持日期范围和股票代码）
            results = stock_announce_processor.search_announcements_by_keyword(
                keywords, 
                start_date=start_date, 
                end_date=end_date,
                stock_code=stock_code
            )
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(results, ensure_ascii=False).encode("utf-8"))
        except Exception as exc:
            print(f"搜索公告时发生错误: {exc}", flush=True)
            traceback.print_exc()
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def handle_realtime_proxy(self, query_string):
        params = parse_qs(query_string)
        page = params.get("pn", ["1"])[0]
        page_size = params.get("pz", ["100"])[0]
        remote_params = {
            "np": "1",
            "fltt": "1",
            "invt": "2",
            "fs": FILTER,
            "fields": FIELD_LIST,
            "fid": "f243",
            "pn": page,
            "pz": page_size,
            "po": "1",
            "dect": "1",
            "ut": UT,
            "wbp2u": WBP2U,
            "_": str(int(time.time() * 1000)),
        }
        url = REMOTE_BASE + "?" + urlencode(remote_params)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7",
            "Referer": "https://quote.eastmoney.com/center/gridlist.html",
            "Origin": "https://quote.eastmoney.com",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Sec-Ch-Ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"",
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "\"Windows\"",
            "Sec-Ch-Ua-Platform-Version": "\"10.0.0\"",
            "Sec-Ch-Ua-Arch": "\"x86\"",
            "Sec-Ch-Ua-Model": "\"\"",
            "Sec-Ch-Ua-Bitness": "\"64\"",
            "Sec-Ch-Ua-Full-Version": "\"120.0.6099.109\"",
            "Sec-Ch-Ua-Full-Version-List": "\"Not_A Brand\";v=\"8.0.0.0\", \"Chromium\";v=\"120.0.6099.109\", \"Google Chrome\";v=\"120.0.6099.109\"",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "TE": "trailers",
            "DNT": "1",
            "X-Requested-With": "XMLHttpRequest",
        }
        if COOKIE:
            headers["Cookie"] = COOKIE

        req = Request(url, headers=headers)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"Proxy attempt {attempt} -> {url}", flush=True)
                with urlopen(req, timeout=20) as resp:
                    data = resp.read()
                    status_code = getattr(resp, "status", resp.getcode())
                    print("Remote returned", status_code, "len=", len(data), flush=True)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(data)
                    return
            except HTTPError as exc:
                print("HTTPError from remote:", repr(exc), flush=True)
                traceback.print_exc()
                self.send_response(exc.code)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                try:
                    self.wfile.write(exc.read())
                except Exception:
                    pass
                return
            except URLError as exc:
                print(f"URLError contacting remote (attempt {attempt}):", repr(exc), flush=True)
                traceback.print_exc()
                reason = getattr(exc, "reason", exc)
                if attempt < MAX_RETRIES and is_retryable_exception(reason):
                    delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    print(f"Retrying after {delay:.1f}s", flush=True)
                    time.sleep(delay)
                    continue
                self.send_response(502)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                try:
                    self.wfile.write(str(exc).encode("utf-8"))
                except Exception:
                    pass
                return
            except Exception as exc:
                print(f"Unexpected exception in proxy handler (attempt {attempt}):", repr(exc), flush=True)
                traceback.print_exc()
                if attempt < MAX_RETRIES and is_retryable_exception(exc):
                    delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    print(f"Retrying after {delay:.1f}s", flush=True)
                    time.sleep(delay)
                    continue
                self.send_response(500)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                try:
                    self.wfile.write(str(exc).encode("utf-8"))
                except Exception:
                    pass
                return

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    # 启动时加载股票基础数据和标签数据到内存（公告数据延迟加载）
    load_stock_base()
    load_stock_labels()
    
    port = 8000
    server = HTTPServer(("0.0.0.0", port), RealtimeProxyHandler)
    print(f"Serving at http://localhost:{port}")
    print("Use http://localhost:8000/web/index.html to open the UI")
    print("Use http://localhost:8000/web/label.html to open the Label UI")
    server.serve_forever()
