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
import subprocess
import sys
import bisect
import re

# 公告处理器（延迟导入）
stock_announce_processor = None

# 全局变量，用于缓存股票标签数据和股票基础数据
stock_labels_cache = {}
stock_base_cache = {}
stock_industry_cache = {}
stock_delisted_set = set()
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
    global stock_base_cache, stock_industry_cache, stock_delisted_set
    if os.path.exists(BASE_FILE):
        try:
            # 尝试使用UTF-8编码读取
            with open(BASE_FILE, "r", encoding="utf-8") as f:
                base_data = json.load(f)
            stock_base_cache = {item["stock_code"]: item["stock_name"] for item in base_data}
            stock_industry_cache = {item["stock_code"]: (item.get("industry_level1") or "") for item in base_data}
            stock_delisted_set = {item["stock_code"] for item in base_data if item.get("delisted_date") and item.get("delisted_date") != "2038-01-01"}
            print(f"已加载股票基础数据，共 {len(stock_base_cache)} 只股票")
        except UnicodeDecodeError:
            # 如果UTF-8失败，尝试GBK编码（中文Windows常见编码）
            try:
                with open(BASE_FILE, "r", encoding="gbk") as f:
                    base_data = json.load(f)
                stock_base_cache = {item["stock_code"]: item["stock_name"] for item in base_data}
                stock_industry_cache = {item["stock_code"]: (item.get("industry_level1") or "") for item in base_data}
                stock_delisted_set = {item["stock_code"] for item in base_data if item.get("delisted_date") and item.get("delisted_date") != "2038-01-01"}
                print(f"已加载股票基础数据(GBK)，共 {len(stock_base_cache)} 只股票")
            except Exception as e:
                print(f"加载股票基础数据失败(GBK): {e}")
                stock_base_cache = {}
                stock_industry_cache = {}
                stock_delisted_set = set()
        except Exception as e:
            print(f"加载股票基础数据失败: {e}")
            stock_base_cache = {}
            stock_industry_cache = {}
            stock_delisted_set = set()
    else:
        stock_base_cache = {}
        stock_industry_cache = {}
        stock_delisted_set = set()
        print("股票基础数据文件不存在")

def get_stock_name(stock_code):
    """根据股票代码获取股票名称"""
    if stock_code in stock_labels_cache and stock_labels_cache[stock_code].get("name"):
        return stock_labels_cache[stock_code]["name"]
    if stock_code in stock_base_cache:
        return stock_base_cache[stock_code]
    return stock_code


# ==================== 财务公式查询 ====================
# 资产负债表字段与中文名映射(46个,与 domain.py balance_fields 一致)
BALANCE_FIELDS = [
    ("mny_cptl", "货币资金"),
    ("trd_fin_ast", "交易性金融资产"),
    ("note_acct_rcv", "应收票据及应收账款"),
    ("acct_rcv_fin", "应收款项融资"),
    ("oth_rcv", "其他应收款"),
    ("ttl_oth_rcv", "其他应收款合计"),
    ("invt", "存货"),
    ("contr_ast", "合同资产"),
    ("ncur_ast_one_y", "一年内到期的非流动资产"),
    ("oth_cur_ast", "其他流动资产"),
    ("ttl_cur_ast", "流动资产合计"),
    ("lt_rcv", "长期应收款"),
    ("lt_eqy_inv", "长期股权投资"),
    ("oth_eqy_inv", "其他权益工具投资"),
    ("fix_ast", "固定资产"),
    ("const_prog", "在建工程"),
    ("cptl_bio_ast", "生产性生物资产"),
    ("rig_ast", "使用权资产"),
    ("intg_ast", "无形资产"),
    ("gw", "商誉"),
    ("lt_ppay_exp", "长期待摊费用"),
    ("dfr_tax_ast", "递延所得税资产"),
    ("oth_ncur_ast", "其他非流动资产"),
    ("ttl_ncur_ast", "非流动资产合计"),
    ("oth_ast", "其他资产"),
    ("ttl_ast", "资产总计"),
    ("sht_ln", "短期借款"),
    ("adv_acct", "预收款项"),
    ("contr_liab", "合同负债"),
    ("note_acct_pay", "应付票据及应付账款"),
    ("emp_comp_pay", "应付职工薪酬"),
    ("tax_pay", "应交税费"),
    ("ttl_oth_pay", "其他应付款合计"),
    ("ncur_liab_one_y", "一年内到期的非流动负债"),
    ("oth_cur_liab", "其他流动负债"),
    ("ttl_cur_liab", "流动负债合计"),
    ("lt_ln", "长期借款"),
    ("lt_pay", "长期应付款"),
    ("leas_liab", "租赁负债"),
    ("dfr_tax_liab", "递延所得税负债"),
    ("bnd_pay", "应付债券"),
    ("ttl_ncur_liab", "非流动负债合计"),
    ("ttl_liab", "负债合计"),
    ("ret_prof", "未分配利润"),
    ("ttl_eqy_pcom", "归母股东权益合计"),
    ("min_sheqy", "少数股东权益"),
]
BALANCE_FIELD_CN = dict(BALANCE_FIELDS)
FINANCE_DIR = "stocks/finance/zzfzb"
_finance_cache = {}
_finance_cache_loaded = False

# 行情字段与中文名映射(来自 stocks/kline 日线数据)
KLINE_FIELDS = [
    ("date", "日期"),
    ("close", "收盘价"),
    ("high", "最高价"),
    ("tot_mv", "总市值"),
    ("pe_ttm_cut", "市盈率(TTM)"),
    ("dy_lfy", "股息率"),
]
KLINE_FIELD_CN = dict(KLINE_FIELDS)
_kline_cache = {}
_kline_all_codes_cache = None


def load_all_balance_data():
    """惰性加载全部资产负债表数据到内存,首次查询时加载"""
    global _finance_cache_loaded
    if _finance_cache_loaded:
        return
    if os.path.exists(FINANCE_DIR):
        for prefix in os.listdir(FINANCE_DIR):
            prefix_dir = os.path.join(FINANCE_DIR, prefix)
            if not os.path.isdir(prefix_dir):
                continue
            for fn in os.listdir(prefix_dir):
                if not fn.endswith(".json"):
                    continue
                code = fn[:-5]
                try:
                    with open(os.path.join(prefix_dir, fn), "r", encoding="utf-8") as f:
                        _finance_cache[code] = json.load(f)
                except Exception:
                    pass
    _finance_cache_loaded = True
    print(f"已加载资产负债表数据，共 {len(_finance_cache)} 只股票")


FINANCE_SCHEMES_FILE = "stocks/finance_schemes.json"


def load_finance_schemes():
    """读取已保存的方案"""
    if os.path.exists(FINANCE_SCHEMES_FILE):
        try:
            with open(FINANCE_SCHEMES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_finance_schemes(schemes):
    """写入方案文件"""
    with open(FINANCE_SCHEMES_FILE, "w", encoding="utf-8") as f:
        json.dump(schemes, f, ensure_ascii=False, indent=2)


def _kline_all_codes():
    """扫描 kline 目录得到全部股票代码"""
    global _kline_all_codes_cache
    if _kline_all_codes_cache is None:
        codes = set()
        base = "stocks/kline"
        if os.path.exists(base):
            for prefix in os.listdir(base):
                d = os.path.join(base, prefix)
                if os.path.isdir(d):
                    for fn in os.listdir(d):
                        if fn.endswith(".parquet"):
                            codes.add(fn[:-8])
        _kline_all_codes_cache = codes
    return _kline_all_codes_cache


def _load_kline_code(code):
    """加载单只股票kline数据到内存缓存,返回 (dates升序列表, {字段:数值数组}) 或 None"""
    if code in _kline_cache:
        return _kline_cache[code]
    f = os.path.join("stocks/kline", code[:2], code + ".parquet")
    if not os.path.exists(f):
        _kline_cache[code] = None
        return None
    try:
        import pandas as pd
        df = pd.read_parquet(f)
        dates = df["date"].astype(str).tolist()
        arr = {}
        for col in ("close", "high", "tot_mv", "pe_ttm_cut", "dy_lfy"):
            arr[col] = df[col].to_numpy(dtype="float64")
        _kline_cache[code] = (dates, arr)
    except Exception:
        _kline_cache[code] = None
    return _kline_cache[code]


def _kline_index(dates, period):
    """返回行情日期索引: latest=最后一条; 具体日期=<=该日期最近一条; 无匹配返回None"""
    if not dates:
        return None
    if period and period != "latest":
        i = bisect.bisect_right(dates, period) - 1
        return i if i >= 0 else None
    return len(dates) - 1


def _safe_num(v):
    """把值转成数值, 缺失/NaN 按 0 处理"""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return 0
    return v if v == v else 0


class _ExprError(Exception):
    pass


def _tokenize_formula(expr):
    """公式词法分析,返回 token 列表,每个 token 为 ("op"/"num"/"field", 值)"""
    tokens = []
    i, n = 0, len(expr)
    while i < n:
        ch = expr[i]
        if ch in " \t\r\n":
            i += 1
            continue
        two = expr[i:i + 2]
        if two in (">=", "<=", "==", "!=", "&&", "||"):
            tokens.append(("op", two))
            i += 2
            continue
        if ch in "+-*/()><":
            tokens.append(("op", ch))
            i += 1
            continue
        if ch.isdigit() or ch == ".":
            j = i
            while j < n and (expr[j].isdigit() or expr[j] == "."):
                j += 1
            if j < n and expr[j] in "eE":
                j += 1
                if j < n and expr[j] in "+-":
                    j += 1
                while j < n and expr[j].isdigit():
                    j += 1
            try:
                tokens.append(("num", float(expr[i:j])))
            except ValueError:
                raise _ExprError(f"无效的数字: {expr[i:j]}")
            i = j
            continue
        if ch.isalpha() or ch == "_":
            j = i
            while j < n and (expr[j].isalnum() or expr[j] == "_"):
                j += 1
            tokens.append(("field", expr[i:j]))
            i = j
            continue
        raise _ExprError(f"无法识别的字符: {ch}")
    return tokens


class _FormulaParser:
    """递归下降解析器,AST 节点: ('num',v) ('field',name) ('neg',child)
    ('bin',op,l,r) ('cmp',op,l,r) ('logic',op,l,r)"""

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def expect_op(self, ops):
        tok = self.peek()
        if tok and tok[0] == "op" and tok[1] in ops:
            self.pos += 1
            return tok[1]
        return None

    def parse(self):
        node = self.parse_logic_or()
        if self.peek() is not None:
            raise _ExprError("公式存在多余内容")
        return node

    def parse_logic_or(self):
        left = self.parse_logic_and()
        while self.expect_op(["||"]):
            left = ("logic", "||", left, self.parse_logic_and())
        return left

    def parse_logic_and(self):
        left = self.parse_comparison()
        while self.expect_op(["&&"]):
            left = ("logic", "&&", left, self.parse_comparison())
        return left

    def parse_comparison(self):
        left = self.parse_additive()
        op = self.expect_op([">=", "<=", ">", "<", "==", "!="])
        if op:
            return ("cmp", op, left, self.parse_additive())
        return left

    def parse_additive(self):
        left = self.parse_term()
        while True:
            op = self.expect_op(["+", "-"])
            if not op:
                break
            left = ("bin", op, left, self.parse_term())
        return left

    def parse_term(self):
        left = self.parse_factor()
        while True:
            op = self.expect_op(["*", "/"])
            if not op:
                break
            left = ("bin", op, left, self.parse_factor())
        return left

    def parse_factor(self):
        tok = self.peek()
        if tok is None:
            raise _ExprError("公式不完整")
        if tok[0] == "num":
            self.pos += 1
            return ("num", tok[1])
        if tok[0] == "field":
            self.pos += 1
            return ("field", tok[1])
        if tok[0] == "op" and tok[1] == "-":
            self.pos += 1
            return ("neg", self.parse_factor())
        if tok[0] == "op" and tok[1] == "(":
            self.pos += 1
            node = self.parse_logic_or()
            if not self.expect_op([")"]):
                raise _ExprError("缺少右括号 )")
            return node
        raise _ExprError(f"意外的符号: {tok[1]}")


def _collect_fields(node, out):
    """收集公式中引用的所有字段名"""
    t = node[0]
    if t == "field":
        out.add(node[1])
    elif t == "neg":
        _collect_fields(node[1], out)
    elif t in ("bin", "cmp", "logic"):
        _collect_fields(node[2], out)
        _collect_fields(node[3], out)


def _eval_node(node, values):
    """计算 AST,values 为 {字段:数值},缺失字段已按 0 处理"""
    t = node[0]
    if t == "num":
        return node[1]
    if t == "field":
        return values[node[1]]
    if t == "neg":
        return -_eval_node(node[1], values)
    if t == "bin":
        op, left, right = node[1], node[2], node[3]
        a, b = _eval_node(left, values), _eval_node(right, values)
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if b == 0:
            raise ZeroDivisionError()
        return a / b
    if t == "cmp":
        op, left, right = node[1], node[2], node[3]
        a, b = _eval_node(left, values), _eval_node(right, values)
        if op == ">":
            return a > b
        if op == "<":
            return a < b
        if op == ">=":
            return a >= b
        if op == "<=":
            return a <= b
        if op == "==":
            return a == b
        return a != b
    if t == "logic":
        op, left, right = node[1], node[2], node[3]
        a, b = _eval_node(left, values), _eval_node(right, values)
        if op == "&&":
            return bool(a) and bool(b)
        return bool(a) or bool(b)
    return None


def _formula_to_text(node):
    """把 AST 转成中文解析文本"""
    t = node[0]
    if t == "num":
        v = node[1]
        return str(int(v)) if v == int(v) else str(v)
    if t == "field":
        return BALANCE_FIELD_CN.get(node[1], node[1])
    if t == "neg":
        return "(-" + _formula_to_text(node[1]) + ")"
    op, left, right = node[1], node[2], node[3]
    return f"({_formula_to_text(left)} {op} {_formula_to_text(right)})"


def _pick_record(records, period):
    """按报告期选取记录: latest=最新一期; 指定日期=严格匹配该报告期"""
    if period and period != "latest":
        matches = [r for r in records if (r.get("rpt_date") or "") == period]
        if not matches:
            return None
        return max(matches, key=lambda r: r.get("pub_date") or "")
    return max(records, key=lambda r: (r.get("rpt_date") or "", r.get("pub_date") or ""))


def finance_periods():
    """返回数据中出现过的报告期,从新到旧,取最近40期(约10年)"""
    load_all_balance_data()
    periods = set()
    for records in _finance_cache.values():
        for rec in records:
            d = rec.get("rpt_date")
            if d:
                periods.add(d)
    return {"periods": sorted(periods, reverse=True)[:40]}


def finance_fields():
    """返回按一级分类组织的字段列表(财务/行情)"""
    return {"categories": [
        {"cat": "财务", "fields": [{"field": f, "cn": cn} for f, cn in BALANCE_FIELDS]},
        {"cat": "行情", "fields": [{"field": f, "cn": cn} for f, cn in KLINE_FIELDS]},
    ]}


def finance_industries():
    """返回一级行业去重列表"""
    load_stock_base()
    return {"industries": sorted({v for v in stock_industry_cache.values() if v})}


def finance_query(formula, period=None, exclude_industry=None):
    """解析公式并遍历财务/行情数据计算,返回结果字典"""
    try:
        root = _FormulaParser(_tokenize_formula(formula)).parse()
    except _ExprError as e:
        return {"error": str(e)}
    excluded = set()
    if exclude_industry:
        excluded = {x for x in exclude_industry.split(",") if x}
    fields_used = set()
    _collect_fields(root, fields_used)
    finance_used = [f for f in fields_used if f in BALANCE_FIELD_CN]
    kline_used = [f for f in fields_used if f in KLINE_FIELD_CN]
    unknown = [f for f in fields_used if f not in BALANCE_FIELD_CN and f not in KLINE_FIELD_CN]
    if unknown:
        return {"error": "未知字段: " + ", ".join(unknown)}
    if finance_used:
        load_all_balance_data()
    if kline_used:
        codes = _kline_all_codes() if not finance_used else (set(_finance_cache.keys()) & _kline_all_codes())
    else:
        codes = set(_finance_cache.keys())
    is_bool = root[0] in ("cmp", "logic")
    cmp_parts = None
    if root[0] == "cmp":
        cmp_parts = {"op": root[1], "left_node": root[2], "right_node": root[3]}
    rows = []
    total = 0
    for code in sorted(codes):
        # 固定排除 900 开头的沪市 B 股
        if code.startswith("900"):
            continue
        # 排除已退市股票
        if code in stock_delisted_set:
            continue
        if excluded and stock_industry_cache.get(code) in excluded:
            continue
        rec = None
        if finance_used:
            records = _finance_cache.get(code)
            if not records:
                continue
            rec = _pick_record(records, period)
            if rec is None:
                continue
            if all(rec.get(f) is None for f in finance_used):
                continue
        krec = None
        kline_date = ""
        if kline_used:
            kl = _load_kline_code(code)
            if kl is None:
                continue
            dates, arr = kl
            idx = _kline_index(dates, period)
            if idx is None:
                continue
            kline_date = dates[idx]
            krec = {f: _safe_num(arr[f][idx]) for f in kline_used}
        # 市值列：优先复用已取的行情数据，否则补充读取 kline 的 tot_mv
        market_cap = None
        if krec is not None and "tot_mv" in kline_used:
            market_cap = krec["tot_mv"]
        else:
            kl = _load_kline_code(code)
            if kl is not None:
                dates, arr = kl
                idx = _kline_index(dates, period)
                if idx is not None:
                    market_cap = _safe_num(arr["tot_mv"][idx])
        values = {}
        if finance_used:
            for f in finance_used:
                v = rec.get(f)
                values[f] = v if v is not None else 0
        if kline_used:
            for f in kline_used:
                values[f] = krec[f]
        left = right = None
        try:
            if cmp_parts:
                left = _eval_node(cmp_parts["left_node"], values)
                right = _eval_node(cmp_parts["right_node"], values)
            result = _eval_node(root, values)
        except ZeroDivisionError:
            continue
        if is_bool and not result:
            continue
        total += 1
        row = {
            "code": code,
            "name": get_stock_name(code),
            "period": (rec.get("rpt_date") if rec else "") or kline_date,
            "value": result,
            "market_cap": round(market_cap / 1e8, 2) if market_cap else None,
        }
        if cmp_parts:
            row["left"] = left
            row["right"] = right
            row["op"] = cmp_parts["op"]
        rows.append(row)
    if not is_bool:
        rows.sort(key=lambda r: r["value"], reverse=True)
    return {
        "parsed": _formula_to_text(root),
        "is_bool": is_bool,
        "count": len(rows),
        "total": total,
        "rows": rows,
    }

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
        elif parsed.path == "/announce-pdf":
            self.handle_announce_pdf(parsed.query)
        elif parsed.path == "/stocks/stock_label.json":
            self.handle_get_stock_labels()
        elif parsed.path == "/update-canzhai":
            self.handle_update_canzhai()
        elif parsed.path == "/finance-fields":
            self.handle_finance_fields()
        elif parsed.path == "/finance-industries":
            self.handle_finance_industries()
        elif parsed.path == "/finance-periods":
            self.handle_finance_periods()
        elif parsed.path == "/finance-query":
            self.handle_finance_query(parsed.query)
        elif parsed.path == "/finance-schemes":
            self.handle_get_finance_schemes()
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
    
    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/finance-schemes":
            self.handle_post_finance_schemes()
        else:
            self.send_response(404)
            self.end_headers()

    def handle_get_finance_schemes(self):
        """处理获取已保存方案请求"""
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"schemes": load_finance_schemes()}, ensure_ascii=False).encode("utf-8"))
        except Exception as exc:
            print(f"获取方案失败: {exc}", flush=True)
            traceback.print_exc()
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def handle_post_finance_schemes(self):
        """处理保存/删除方案请求"""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            schemes = load_finance_schemes()
            action = data.get("action")
            if action == "save" and data.get("name"):
                schemes[data["name"]] = data.get("formula", "")
                save_finance_schemes(schemes)
            elif action == "delete" and data.get("name"):
                schemes.pop(data["name"], None)
                save_finance_schemes(schemes)
            else:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "参数错误"}).encode("utf-8"))
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "schemes": schemes}, ensure_ascii=False).encode("utf-8"))
        except Exception as exc:
            print(f"保存方案失败: {exc}", flush=True)
            traceback.print_exc()
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

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

    def handle_announce_pdf(self, query_string):
        """通过服务端代理获取东财公告PDF：带本地磁盘缓存，未命中时触发JSL反爬挑战并计算cookie后重新请求"""
        params = parse_qs(query_string)
        art_code = params.get("artCode", [None])[0]
        if not art_code:
            self.send_response(400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "缺少artCode参数"}).encode("utf-8"))
            return
        cache_path = os.path.join("stocks", "announce_pdf", f"{art_code}.pdf")
        if os.path.exists(cache_path):
            print(f"公告PDF命中缓存: {art_code}", flush=True)
            with open(cache_path, "rb") as f:
                data = f.read()
        else:
            pdf_url = f"https://pdf.dfcfw.com/pdf/H2_{art_code}_1.pdf"
            headers = {
                "Referer": "https://data.eastmoney.com/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/pdf,*/*",
            }
            try:
                with urlopen(Request(pdf_url, headers=headers), timeout=30) as resp:
                    data = resp.read()
                #JSL挑战页为script内容，解析其中的常量计算cookie后带cookie重新请求
                if data.startswith(b"<script") and b"EO_Bot_Ssid" in data:
                    js = data.decode("utf-8", errors="ignore")
                    t_sum = sum(int(x) for x in re.findall(r":(\d+)", js))
                    m = re.search(r"\(t,(\d+)\)", js)
                    ssid = m.group(1) if m else ""
                    cookie = f"EO_Bot_Ssid={ssid}; __tst_status={t_sum},EO_Bot_Ssid={ssid}#"
                    with urlopen(Request(pdf_url, headers=dict(headers, Cookie=cookie)), timeout=30) as resp:
                        data = resp.read()
                    print(f"公告PDF挑战页为script内容: {art_code}", flush=True)
            except Exception as exc:
                print(f"下载公告PDF失败: {exc}", flush=True)
                self.send_response(502)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))
                return
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, "wb") as f:
                f.write(data)
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

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

    def handle_update_canzhai(self):
        """处理更新可转债数据请求"""
        try:
            print("开始更新可转债数据...", flush=True)
            result = subprocess.run(
                [sys.executable, 'update_canzhai.py'],
                capture_output=True, text=True, timeout=120,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            output = result.stdout
            if result.stderr:
                output += '\n' + result.stderr
            success = result.returncode == 0
            print(f"更新可转债数据完成, success={success}", flush=True)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"success": success, "output": output}).encode("utf-8"))
        except subprocess.TimeoutExpired:
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "output": "更新超时（120秒）"}).encode("utf-8"))
        except Exception as exc:
            print(f"更新可转债数据失败: {exc}", flush=True)
            traceback.print_exc()
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "output": str(exc)}).encode("utf-8"))

    def handle_finance_fields(self):
        """处理获取财务字段列表请求"""
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(finance_fields(), ensure_ascii=False).encode("utf-8"))
        except Exception as exc:
            print(f"获取财务字段失败: {exc}", flush=True)
            traceback.print_exc()
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def handle_finance_industries(self):
        """处理获取一级行业列表请求"""
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(finance_industries(), ensure_ascii=False).encode("utf-8"))
        except Exception as exc:
            print(f"获取行业列表失败: {exc}", flush=True)
            traceback.print_exc()
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def handle_finance_periods(self):
        """处理获取报告期列表请求"""
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(finance_periods(), ensure_ascii=False).encode("utf-8"))
        except Exception as exc:
            print(f"获取报告期失败: {exc}", flush=True)
            traceback.print_exc()
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def handle_finance_query(self, query_string):
        """处理财务公式查询请求"""
        params = parse_qs(query_string)
        formula = params.get("formula", [None])[0]
        period = params.get("period", [None])[0]
        exclude_industry = params.get("exclude_industry", [None])[0]
        if not formula:
            self.send_response(400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "缺少公式参数"}).encode("utf-8"))
            return
        try:
            result = finance_query(formula, period, exclude_industry)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
        except Exception as exc:
            print(f"财务公式查询失败: {exc}", flush=True)
            traceback.print_exc()
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

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
    print("Use http://localhost:8000/web/finance_query.html to open the Finance Query UI")
    server.serve_forever()
