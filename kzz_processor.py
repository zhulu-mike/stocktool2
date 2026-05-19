import json
import re
import os
import time
import urllib.request
import urllib.error
import http.client
import html
import random
import stock_price_processor

CB_LIST_URL_TEMPLATE = "https://push2.eastmoney.com/api/qt/clist/get?np=1&fltt=1&invt=2&fs=b%3AMK0354&fields=f12%2Cf13%2Cf14%2Cf1%2Cf2%2Cf4%2Cf3%2Cf152%2Cf232%2Cf233%2Cf234%2Cf229%2Cf230%2Cf231%2Cf235%2Cf236%2Cf154%2Cf237%2Cf238%2Cf239%2Cf240%2Cf241%2Cf242%2Cf26%2Cf243&fid=f243&po=1&dect=1&ut=fa5fd1943c7b386f172d6893dbfba10b&wbp2u=%7C0%7C0%7C0%7Cweb&pn={page}&pz={page_size}&_={timestamp}"
REALTIME_URL_TEMPLATE = "https://push2.eastmoney.com/api/qt/clist/get?np=1&fltt=1&invt=2&cb=jQuery37108254419802265193_{timestamp}&fs=b%3AMK0354&fields=f12%2Cf13%2Cf14%2Cf1%2Cf2%2Cf4%2Cf3%2Cf152%2Cf232%2Cf233%2Cf234%2Cf229%2Cf230%2Cf231%2Cf235%2Cf236%2Cf154%2Cf237%2Cf238%2Cf239%2Cf240%2Cf241%2Cf227%2Cf242%2Cf26%2Cf243&fid=f243&pn={page}&pz={page_size}&po=1&dect=1&ut=fa5fd1943c7b386f172d6893dbfba10b&wbp2u=3046094285466864%7C0%7C1%7C0%7Cweb&_={timestamp}"
EASTMONEY_LIST_PAGE_SIZE = 500
REALTIME_PAGE_SIZE = 100


class ConvertBondDetailFetcher:
    """从集思路转债详情页面获取指定转债信息，并返回键值对 JSON。"""

    URL_TEMPLATE = "https://www.jisilu.cn/data/convert_bond_detail/{bond_code}"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

    def __init__(self, bond_code: str):
        self.bond_code = bond_code.strip()

    def fetch(self) -> dict:
        html_text = self._download_html()
        return self._parse_detail(html_text)

    def fetch_json(self, ensure_ascii: bool = False, indent: int = 2) -> str:
        detail = self.fetch()
        return json.dumps(detail, ensure_ascii=ensure_ascii, indent=indent)

    def _download_html(self) -> str:
        url = self.URL_TEMPLATE.format(bond_code=self.bond_code)
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.jisilu.cn/",
            "Connection": "keep-alive",
        }
        request = urllib.request.Request(url, headers=headers)
        
        # 设置较短的超时时间，避免长时间等待
        for retry in range(3):
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    raw = response.read()
                return raw.decode("utf-8", errors="ignore")
            except Exception as e:
                if retry < 2:
                    time.sleep(random.uniform(1, 2))
                    continue
                raise

    def _parse_detail(self, html_text: str) -> dict:
        html_text = html.unescape(html_text)
        redeem_info = self._extract_redeem_status_info(html_text)
        return {
            "convert_ratio": self._extract_text_by_id(html_text, "cvt_rt"),
            "market_value_ratio": self._extract_text_by_id(html_text, "convert_amt_ratio2"),
            "force_redeem_days": redeem_info["days"],
            "lowering_trigger_price": self._extract_text_by_id(html_text, "threshold_value"),
            "last_trade_date": self._extract_label_value(html_text, "最后交易日"),
            "last_convert_date": self._extract_label_value(html_text, "最后转股日"),
            "year_left": self._extract_text_by_id(html_text, "year_term"),
            "sell_start_date": self._extract_label_value(html_text, "回售起算日"),
            "maturity_dt": self._extract_label_value(html_text, "到期日"),
            "maturity_price": self._extract_label_value(html_text, "到期赎回价"),
            "convert_price": self._extract_label_value(html_text, "转股价"),
            "listing_date": self._extract_label_value(html_text, "上市日"),
            "force_redeem_price": self._extract_force_redeem_price(html_text),
            "left_market_value": self._extract_label_value(html_text, "剩余规模(亿)"),
            "force_redeem_status": redeem_info["status"],
        }

    def _extract_text_by_id(self, html_text: str, element_id: str) -> str:
        pattern = rf'id="{re.escape(element_id)}"[^>]*>(.*?)</td>'
        match = re.search(pattern, html_text, re.S)
        if not match:
            return ""
        value = match.group(1)
        return self._normalize_text(value)

    def _extract_force_redeem_price(self, html_text: str) -> str:
        pattern = r'id="force_redeem_price"[^>]*>(.*?)<sup'
        match = re.search(pattern, html_text, re.S)
        if not match:
            return ""
        value = match.group(1)
        return self._normalize_text(value)

    def _extract_label_value(self, html_text: str, label: str) -> str:
        pattern = rf'<td[^>]*class="jisilu_title"[^>]*>\s*{re.escape(label)}\s*</td>\s*<td[^>]*>([^<]*)</td>'
        match = re.search(pattern, html_text, re.S)
        if match:
            return self._normalize_text(match.group(1))
        pattern = rf'<td[^>]*>\s*{re.escape(label)}\s*</td>\s*<td[^>]*>([^<]*)</td>'
        match = re.search(pattern, html_text, re.S)
        return self._normalize_text(match.group(1)) if match else ""

    def _extract_redeem_status_info(self, html_text: str) -> dict:
        raw = self._extract_text_by_id(html_text, "redeem_status")
        if not raw:
            return {"days": "", "status": ""}

        raw = raw.replace("！", "!").replace("　", " ").strip()
        count_match = re.search(r"(\d+)\s*/\s*(\d+)\s*\|\s*(\d+)", raw)
        if count_match:
            days = f"{count_match.group(1)}/{count_match.group(2)} | {count_match.group(3)}"
        else:
            days = raw

        if "已公告" in raw and "强赎" in raw:
            status = "强赎中"
            days = ""
        elif "公告要强赎" in raw:
            status = "公告强赎"
            days = ""
        elif count_match and count_match.group(1) == "0":
            status = "未满足"
            days = ""
        elif "暂不强赎" in raw:
            date_match = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", raw)
            if date_match:
                status = "暂不强赎"
                days = f"{date_match.group(1)}后重新计数"
            else:
                status = "暂不强赎"
                days = ""
        elif count_match:
            status = "计数中" #f"{count_match.group(1)}-{count_match.group(2)}-{count_match.group(3)}"
        else:
            status = raw

        return {"days": days, "status": status}

    def _extract_bond_name(self, html_text: str) -> str:
        pattern = r'class="bond_nm">.*?<span[^>]*>([^<]+)</span>\s*([0-9]+)'
        match = re.search(pattern, html_text, re.S)
        if match:
            return self._normalize_text(match.group(1))
        pattern = r'class="bond_nm">\s*([^<\n]+)'
        match = re.search(pattern, html_text, re.S)
        return self._normalize_text(match.group(1)) if match else ""

    def _extract_bond_code(self, html_text: str) -> str:
        pattern = r'class="bond_nm">.*?<span[^>]*>[^<]+</span>\s*([0-9]+)'
        match = re.search(pattern, html_text, re.S)
        return match.group(1).strip() if match else self.bond_code

    def _extract_underlying_stock_name(self, html_text: str) -> str:
        pattern = r'class="stock_nm">.*?<a[^>]*>\s*<span[^>]*>(.*?)</span>'
        match = re.search(pattern, html_text, re.S)
        return self._normalize_text(match.group(1)) if match else ""

    def _extract_underlying_stock_code(self, html_text: str) -> str:
        pattern = r'class="stock_nm">.*?<a[^>]*>.*?<span[^>]*>.*?</span>\s*([0-9]+)'
        match = re.search(pattern, html_text, re.S)
        return match.group(1).strip() if match else ""

    def _extract_force_redeem_days(self, html_text: str) -> str:
        value = self._extract_text_by_id(html_text, "redeem_status")
        if not value:
            return ""
        parts = re.split(r"\|", value)
        if len(parts) < 2:
            return self._normalize_text(value)

        left = parts[0].strip()
        right = parts[1].strip()

        # left 部分通常是 month/day
        left_match = re.search(r"(\d{1,2})\s*/\s*(\d{1,2})", left)
        if not left_match:
            left_part = self._normalize_text(left)
        else:
            month = int(left_match.group(1))
            day = int(left_match.group(2))
            left_part = f"{month:d}-{day:d}"

        # right 部分通常是 days [date ...]
        right_days = ""
        right_date = ""
        days_match = re.search(r"(\d{1,4})", right)
        if days_match:
            right_days = days_match.group(1)
        date_match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", right)
        if date_match:
            right_date = f"{int(date_match.group(1)):04d}{int(date_match.group(2)):02d}{int(date_match.group(3)):02d}"

        components = [c for c in [left_part, right_days, right_date] if c]
        return "-".join(components)

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = re.sub(r"<[^>]+>", "", text)
        text = text.replace("\n", " ").replace("\r", " ").strip()
        return re.sub(r"\s+", " ", text)


def _download_json(url: str, max_retries: int = 3) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://quote.eastmoney.com/",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "Sec-Ch-Ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"",
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": "\"Windows\"",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Cookie": "qgqp_b_id=c602561399c14fa86676fd697988d417; st_nvi=PSnFaLpR8DVTq6FiTEaAg5fb5; AUTH_FUND.EASTMONEY.COM_GSJZ=AUTH*TTJJ*TOKEN; nid18=0e17cb22ecf6960f4858bfd8cbdced17; nid18_create_time=1773137308838; gviem=hAdwL4sBO0qxKoAeDWiiUad92; gviem_create_time=1773137308838; fullscreengg=1; fullscreengg2=1; st_si=78234811771278; has_jump_to_web=1; p_origin=https%3A%2F%2Fpassport2.eastmoney.com; mtp=1; sid=2505195; vtpst=|; wsc_checkuser_ok=1; st_asi=delete; st_sn=34; st_psi=20260519152807449-113300300986-6946077726; st_pvi=60390339319309; st_sp=2025-08-25%2022%3A04%3A09; st_inirUrl=https%3A%2F%2Fwww.baidu.com%2Flink",
    }
    
    for retry in range(max_retries):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read().decode("utf-8", errors="ignore")
            
            # 检查返回内容是否为空
            if not raw or raw.strip() == "":
                raise ValueError("服务器返回空内容")
            
            # 尝试解析JSON
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                # 如果不是标准JSON，尝试处理JSONP格式
                # JSONP格式: jQueryXXXXX({...}) 或 jQueryXXXXX({...});
                raw_stripped = raw.strip()
                
                # 移除末尾可能的分号
                if raw_stripped.endswith(';'):
                    raw_stripped = raw_stripped[:-1]
                
                # 使用更健壮的正则表达式提取JSON内容
                jsonp_match = re.match(r'^[\w\d_]+\(\s*(.+?)\s*\)$', raw_stripped)
                if jsonp_match:
                    json_content = jsonp_match.group(1)
                    try:
                        return json.loads(json_content)
                    except json.JSONDecodeError as e:
                        print(f"JSONP解析失败 (重试 {retry + 1}/{max_retries}): {e}")
                        print(f"JSONP内容: {json_content[:500]}")
                        raise
                else:
                    print(f"不是有效的JSON或JSONP格式 (重试 {retry + 1}/{max_retries})")
                    print(f"返回内容预览: {raw[:500]}")
                    raise ValueError("不是有效的JSON或JSONP格式")
        
        except (http.client.RemoteDisconnected, urllib.error.URLError, ValueError, json.JSONDecodeError) as e:
            print(f"请求失败 (重试 {retry + 1}/{max_retries}): {e}")
            if retry < max_retries - 1:
                delay = random.uniform(2, 5)
                print(f"等待 {delay:.2f} 秒后重试...")
                time.sleep(delay)
            else:
                raise
        except Exception as e:
            print(f"请求异常: {e}")
            raise


def _normalize_eastmoney_price(value) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{int(value) / 100:.2f}"
    except (ValueError, TypeError):
        return str(value)


def _format_eastmoney_date(value) -> str:
    if value is None or value == "":
        return ""
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[0:4]}-{text[4:6]}-{text[6:8]}"
    return text


def _normalize_date(date_text: str) -> str:
    date_text = date_text.strip()
    if not date_text:
        return ""
    date_text = date_text.replace("年", "-").replace("月", "-").replace("日", "")
    date_text = date_text.replace("/", "-")
    match = re.search(r"(\d{4})[^0-9]+(\d{1,2})[^0-9]+(\d{1,2})", date_text)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"
    return date_text


def _extract_labeled_date(text: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}\s*[:：]?\s*([0-9\-年月\/\s]+)", text)
    if not match:
        return ""
    return _normalize_date(match.group(1))


def _extract_redeem_price(text: str) -> str:
    match = re.search(r"(?:赎回价|到期赎回价|��ؼ�|\bprice\b)[:：\s]*([0-9]+(?:\.[0-9]+)?)", text)
    return match.group(1) if match else ""


def _extract_first_trade_date(text: str) -> str:
    if not text:
        return ""
    # 优先匹配像 “自2026年5月26日” 这样的表达
    m = re.search(r"自\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # 否则匹配所有年月日格式，取最后一个（通常为重新计算的首个交易日）
    matches = re.findall(r"(\d{4})[^0-9]{1,3}(\d{1,2})[^0-9]{1,3}(\d{1,2})", text)
    if matches:
        y, mth, d = matches[-1]
        return f"{int(y):04d}-{int(mth):02d}-{int(d):02d}"

    # 回退到常见的 yyyy-mm-dd / yyyy/mm/dd
    m2 = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
    if m2:
        return _normalize_date(m2.group(0))

    return ""


def _parse_redeem_status(icons: dict) -> dict:
    status = ""
    last_trade_date = ""
    last_convert_date = ""
    redeem_price_detail = ""
    first_trade_date = ""

    if not icons:
        return {
            "redeem_status": status,
            "last_trade_date": last_trade_date,
            "last_convert_date": last_convert_date,
            "redeem_price_detail": redeem_price_detail,
            "first_trade_date": first_trade_date,
        }

    if "O" in icons:
        status = "公告强赎"
    elif "B" in icons:
        status = "满足强赎"
    elif "R" in icons:
        status = "自然到期" if "到期" in icons.get("R", "") else "执行强赎中"
        raw_text = icons.get("R", "")
        last_trade_date = _extract_labeled_date(raw_text, "最后交易日")
        last_convert_date = _extract_labeled_date(raw_text, "最后转股日")
        redeem_price_detail = _extract_redeem_price(raw_text)
    elif "G" in icons:
        status = "不提前赎回"
        raw_text = icons.get("G", "")
        first_trade_date = _extract_first_trade_date(raw_text)

    return {
        "redeem_status": status,
        "last_trade_date": last_trade_date,
        "last_convert_date": last_convert_date,
        "redeem_price_detail": redeem_price_detail,
        "first_trade_date": first_trade_date,
    }


def fetch_realtime_data():
    """获取所有可转债的实时行情数据"""
    realtime_data = {}
    page = 1
    
    while True:
        timestamp = int(time.time() * 1000)
        url = REALTIME_URL_TEMPLATE.format(page=page, page_size=REALTIME_PAGE_SIZE, timestamp=timestamp)
        page_data = _download_json(url)
        data = page_data.get("data", {}) or {}
        rows = data.get("diff", []) or []
        
        for row in rows:
            bond_id = str(row.get("f12", "") or "")
            if bond_id:
                realtime_data[bond_id] = {
                    "realtime_bond_price": _normalize_eastmoney_price(row.get("f2")),
                    "realtime_bond_pct": _normalize_eastmoney_price(row.get("f3")),
                    "realtime_stock_price": _normalize_eastmoney_price(row.get("f229")),
                    "realtime_stock_pct": _normalize_eastmoney_price(row.get("f230")),
                    "realtime_premium": _normalize_eastmoney_price(row.get("f237")),
                }
        
        if not rows or len(rows) < REALTIME_PAGE_SIZE:
            break
        page += 1
        
        delay = random.uniform(1.3, 1.8)
        time.sleep(delay)
    
    return realtime_data

def fetch_all_convert_bonds(save_path: str = None) -> str:
    bonds = []
    page = 1
    total_count = None

    while True:
        timestamp = int(time.time() * 1000)
        url = CB_LIST_URL_TEMPLATE.format(page=page, page_size=EASTMONEY_LIST_PAGE_SIZE, timestamp=timestamp)
        page_data = _download_json(url)
        data = page_data.get("data", {}) or {}
        rows = data.get("diff", []) or []
        if total_count is None:
            total_count = int(data.get("total", 0) or 0)

        for row in rows:
            bond_record = {
                "bond_id": str(row.get("f12", "") or ""),
                "bond_name": str(row.get("f14", "") or ""),
                "stock_id": str(row.get("f232", "") or ""),
                "stock_name": str(row.get("f234", "") or ""),
            }
            bonds.append(bond_record)

        if not rows or (total_count and len(bonds) >= total_count):
            break
        page += 1
        if page > 100:
            break
        print(f"已获取 {len(bonds)} 条可转债数据")
        # 分页请求间隔1-1.5秒
        delay = random.uniform(1, 1.5)
        time.sleep(delay)

    print(f"正在获取 {len(bonds)} 条可转债的详细信息...")
    for i, bond_record in enumerate(bonds):
        detail = {}
        try:
            detail = ConvertBondDetailFetcher(bond_record["bond_id"]).fetch()
        except Exception as e:
            print(f"获取可转债 {bond_record['bond_id']} 详情失败: {e}")
            detail = {}
        bond_record.update({k: str(v) if v is not None else "" for k, v in detail.items()})
        
        # 每处理10条输出一次进度
        if (i + 1) % 10 == 0:
            print(f"已处理 {i + 1}/{len(bonds)} 条可转债详情")

    output_dir = save_path or os.path.join(os.path.dirname(__file__), "kzz", "all.json")
    output_folder = os.path.dirname(output_dir)
    os.makedirs(output_folder, exist_ok=True)
    with open(output_dir, "w", encoding="utf-8") as handle:
        json.dump(bonds, handle, ensure_ascii=False, indent=2)
    print("获取实时行情数据...")
    bonds = stock_price_processor.StockPirceProcessor().update_kzz_with_market_data()
    return bonds


if __name__ == "__main__":
    fetcher = ConvertBondDetailFetcher("128129")
    print(fetcher.fetch_json())
