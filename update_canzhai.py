"""
更新可转债等权指数数据：
1. 从集思录获取最新数据（所有字段）
2. 与本地Excel比较，增量新增日期行（插入到顶部）
3. 导出数据到 data.json
"""
import requests, re, json, openpyxl, os, sys
from datetime import datetime
from copy import copy

# ===== 配置 =====
JISILU_URL = 'https://www.jisilu.cn/data/cbnew/cb_index/'
EXCEL_PATH = r'D:\.goldminer3\projects\fe28bb3f-a453-11ee-b878-14755b767e75\仓位结构.xlsx'
SHEET_NAME = '可转债等权指数'
ASSETS_DIR = r'web\canzhai-trend\assets'

# 集思录 cookies（从浏览器获取，过期后需更新）
JISILU_COOKIES = {
    'kbzw__Session': '7jcf9f5b78v516f6tuj9ondet4',
    'Hm_lvt_164fe01b1433a19b507595a43bf58262': '1788696539',
    'HMACCOUNT': 'D0A4965A530C1314',
    'kbz_newcookie': '1',
    'kbzw__user_login': '7Obd08_P1ebax9aX7sPkyK6vq66ZqIKvpuXK7N_u0ejF1dSeqJihxqWpp6GqpK6X15Gv26Oxxtaa2t-rm6qjsJPZx66YrqXW2cXS1qCasp6olqiCsqS0zL_NjKWwraGvpa2YppaYsqC9tc6-n6qsobKfp5OqkayYrqW0xL_RpNfKq5yrxdeUp6ym3Zegkdnbpc-yjbKPy6LV1J7F0OrK4OXWmK6ap4KeuODl1-fY44HCzZWaqZqnnZa44OWprJyQ2aqtnom63OfO27jc2b7h1Z-Wp7CjnK-Mn62-tcTDn5jN2czZmbzO3Nfmi5a1ybi4y7C8sLfHpJqnnaeZpJKXutvq0N3Go6qpm6ecpZmqlaulpauWkKbg3tjd69vlkamapamhr4HDwtra59KooaqZpJSt',
    'Hm_lpvt_164fe01b1433a19b507595a43bf58262': '1788696616',
}


def fix_json_string(json_str):
    """修复非标准JSON字符串"""
    json_str = re.sub(r"(?<!\\)'", '"', json_str)
    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*]", "]", json_str)
    json_str = json_str.replace("undefined", "null")
    return json_str


def extract_json_object(text, var_name):
    """从JS代码中提取 JSON 对象"""
    idx = text.find(f'var {var_name} = ')
    if idx < 0:
        return None
    start = text.index('{', idx)
    depth = 0
    end = start
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    return text[start:end]


def fetch_jisilu_data():
    """从集思录获取可转债等权指数历史数据，返回所有字段"""
    session = requests.Session()
    session.cookies.update(JISILU_COOKIES)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    })

    resp = session.get(JISILU_URL, timeout=15)
    resp.raise_for_status()

    # 提取 dates 数组（定义在 __data 之前）
    dates_match = re.search(r"(\[[\s\S]*?\])\s*;\s*var\s+__data\s*=", resp.text)
    if not dates_match:
        raise ValueError('未能从页面提取日期数据')
    dates = re.findall(r"'(\d{4}-\d{2}-\d{2})'", dates_match.group(1))
    if not dates:
        raise ValueError('未能从页面提取日期数据')

    # 提取 __data JSON 对象
    raw = extract_json_object(resp.text, '__data')
    if not raw:
        raise ValueError('无法从集思录页面获取数据，请检查 cookies 是否过期')

    fixed = fix_json_string(raw)
    __data = json.loads(fixed)

    # __data 中的数组顺序与 dates 数组顺序一致（旧到新）
    n = len(dates)

    # 构建结果：所有字段
    # 注意：百分比字段需要 /100 转换为小数（Excel 存储格式）
    # 有些字段在 __data 中可能不存在或为空，需要处理
    def get_list(key, default=None):
        v = __data.get(key, [])
        if isinstance(v, list) and len(v) == n:
            return v
        # 如果长度不够，补齐
        if isinstance(v, list):
            return v + [default] * (n - len(v)) if len(v) < n else v[:n]
        return [default] * n

    result = {
        'dates': dates,
        # 数值字段（直接使用）
        'price': get_list('price'),
        'increase_val': get_list('increase_val'),
        'temperature': get_list('temperature'),
        'avg_price': get_list('avg_price'),
        'mid_price': get_list('mid_price'),
        'mid_convert_value': get_list('mid_convert_value'),
        'avg_dblow': get_list('avg_dblow'),
        'premium_temp': get_list('premium_temp'),
        'count': get_list('count'),
        'volume': get_list('volume'),          # 成交额
        'amount': get_list('amount'),           # 剩余规模
        # 百分比字段（__data 中是百分数，需 /100 转为小数）
        'increase_rt': [round(v / 100, 4) if isinstance(v, (int, float)) else None for v in get_list('increase_rt')],
        'avg_premium_rt': [round(v / 100, 4) if isinstance(v, (int, float)) else None for v in get_list('avg_premium_rt')],
        'mid_premium_rt': [round(v / 100, 4) if isinstance(v, (int, float)) else None for v in get_list('mid_premium_rt')],
        'avg_ytm_rt': [round(v / 100, 4) if isinstance(v, (int, float)) else None for v in get_list('avg_ytm_rt')],
        'turnover_rt': [round(v / 100, 4) if isinstance(v, (int, float)) else None for v in get_list('turnover_rt')],
        # 分布数量字段
        'price_90': get_list('price_90'),
        'price_90_100': get_list('price_90_100'),
        'price_100_110': get_list('price_100_110'),
        'price_110_120': get_list('price_110_120'),
        'price_120_130': get_list('price_120_130'),
        'price_130': get_list('price_130'),
        # 分布涨幅字段（也是百分数，需 /100）
        'increase_rt_90': [round(v / 100, 4) if isinstance(v, (int, float)) else None for v in get_list('increase_rt_90')],
        'increase_rt_90_100': [round(v / 100, 4) if isinstance(v, (int, float)) else None for v in get_list('increase_rt_90_100')],
        'increase_rt_100_110': [round(v / 100, 4) if isinstance(v, (int, float)) else None for v in get_list('increase_rt_100_110')],
        'increase_rt_110_120': [round(v / 100, 4) if isinstance(v, (int, float)) else None for v in get_list('increase_rt_110_120')],
        'increase_rt_120_130': [round(v / 100, 4) if isinstance(v, (int, float)) else None for v in get_list('increase_rt_120_130')],
        'increase_rt_130': [round(v / 100, 4) if isinstance(v, (int, float)) else None for v in get_list('increase_rt_130')],
    }

    return result


def format_distribution(count, change_pct):
    """格式化分布列显示文本，如 '2 ↑ +1.67%' 或 '5 ↓ -0.06%'"""
    if count is None or count == 0:
        return '0'
    arrow = '↑' if (change_pct is not None and change_pct >= 0) else '↓'
    change_str = f'{change_pct:+.2%}' if change_pct is not None else '0.00%'
    return f'{count} {arrow} {change_str}'


def update_excel(data):
    """将增量数据写入 Excel（插入到顶部）"""
    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb[SHEET_NAME]

    # 读取 Excel 中已有的日期集合（第1行是表头，从第2行开始）
    existing_dates = set()
    for r in range(2, ws.max_row + 1):
        dt = ws.cell(r, 1).value
        if isinstance(dt, datetime):
            existing_dates.add(dt.strftime('%Y-%m-%d'))

    # 找到增量数据（__data 是旧到新顺序）
    new_indices = []
    for i in range(len(data['dates'])):
        if data['dates'][i] not in existing_dates:
            new_indices.append(i)

    if not new_indices:
        print('没有新的数据需要更新')
        wb.close()
        return 0

    # 新数据按日期从旧到新排序（__data 已经是旧到新）
    # 插入时从最新的开始插入到顶部，这样保持 Excel 最新在前
    # 所以先反转，从最新往最旧插入
    new_indices.reverse()

    # 如果新数据都在已有数据最新日期之后，插入位置固定为第2行
    # 否则需要找到正确的位置（按日期降序插入）
    existing_dates_sorted = []
    for r in range(2, ws.max_row + 1):
        dt = ws.cell(r, 1).value
        if isinstance(dt, datetime):
            existing_dates_sorted.append((r, dt.strftime('%Y-%m-%d')))

    for idx in new_indices:
        date_str = data['dates'][idx]

        # 找到插入位置：保持 Excel 中日期降序（最新在前）
        pos = 2  # 默认插入到表头后第一行
        for r, d in existing_dates_sorted:
            if date_str < d:
                # 新日期比当前行日期小，继续往下找
                pos = r + 1
            else:
                # 新日期 >= 当前行日期，插入到当前行前
                pos = r
                break
        # 如果新日期比所有已有日期都大，pos=2（插入到最前面）
        # 如果新日期比所有已有日期都小，pos=最后一行+1

        # 插入新行
        ws.insert_rows(pos)
        row = pos

        # 写入日期（保持和文件一致的格式 yyyy/m/d）
        cell = ws.cell(row, 1, datetime.strptime(date_str, '%Y-%m-%d'))
        cell.number_format = 'yyyy/m/d'

        # 写入各字段（按Excel列映射）
        ws.cell(row, 2, data['price'][idx])                     # 指数
        ws.cell(row, 3, data['increase_val'][idx])              # 涨跌
        ws.cell(row, 4, data['increase_rt'][idx])               # 涨幅（已转小数）
        ws.cell(row, 5, data['temperature'][idx])               # 温度
        ws.cell(row, 6, round(data['avg_price'][idx], 2) if data['avg_price'][idx] else None)  # 平均价格
        ws.cell(row, 7, round(data['mid_price'][idx], 2) if data['mid_price'][idx] else None)  # 价格中位数
        ws.cell(row, 8, round(data['mid_convert_value'][idx], 2) if data['mid_convert_value'][idx] else None)  # 转股价值中位数
        ws.cell(row, 9, round(data['avg_dblow'][idx], 2) if data['avg_dblow'][idx] else None)  # 平均双低
        ws.cell(row, 10, round(data['premium_temp'][idx], 2) if data['premium_temp'][idx] else None)  # 溢价率
        ws.cell(row, 11, data['avg_premium_rt'][idx])           # 平均溢价率（已转小数）
        ws.cell(row, 12, data['mid_premium_rt'][idx])           # 溢价率中位数（已转小数）
        ws.cell(row, 13, data['avg_ytm_rt'][idx])               # 平均收益率（已转小数）
        ws.cell(row, 14, round(data['volume'][idx], 2) if data['volume'][idx] else None)  # 成交额
        ws.cell(row, 15, round(data['amount'][idx], 2) if data['amount'][idx] else None)  # 剩余规模
        ws.cell(row, 16, data['turnover_rt'][idx])              # 换手率（已转小数）
        ws.cell(row, 17, data['count'][idx])                    # 数量

        # 分布列（带涨跌箭头格式）
        ws.cell(row, 18, format_distribution(data['price_90'][idx], data['increase_rt_90'][idx]))       # <90
        ws.cell(row, 19, format_distribution(data['price_90_100'][idx], data['increase_rt_90_100'][idx]))  # 90-100
        ws.cell(row, 20, format_distribution(data['price_100_110'][idx], data['increase_rt_100_110'][idx]))  # 100-110
        ws.cell(row, 21, format_distribution(data['price_110_120'][idx], data['increase_rt_110_120'][idx]))  # 110-120
        ws.cell(row, 22, format_distribution(data['price_120_130'][idx], data['increase_rt_120_130'][idx]))  # 120-130
        ws.cell(row, 23, format_distribution(data['price_130'][idx], data['increase_rt_130'][idx]))     # >=130

        # 复制上一行的格式（如果有）
        if row > 2:
            for col in range(1, ws.max_column + 1):
                src = ws.cell(row + 1, col)
                dst = ws.cell(row, col)
                if src.has_style:
                    dst.font = copy(src.font)
                    dst.border = copy(src.border)
                    dst.fill = copy(src.fill)
                    dst.number_format = copy(src.number_format)
                    dst.alignment = copy(src.alignment)

        # 更新 existing_dates_sorted（插入后后面的行号+1）
        for k in range(len(existing_dates_sorted)):
            if existing_dates_sorted[k][0] >= row:
                existing_dates_sorted[k] = (existing_dates_sorted[k][0] + 1, existing_dates_sorted[k][1])
        existing_dates_sorted.insert(0, (row, date_str))  # 保持最新在前

        print(f'  新增行: {date_str}')

    wb.save(EXCEL_PATH)
    wb.close()
    print(f'共新增 {len(new_indices)} 行数据')
    return len(new_indices)


def export_data():
    """从 Excel 导出数据到 data.json"""
    import subprocess
    result = subprocess.run(
        [sys.executable, 'extract_data.py'],
        capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__))
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f'导出数据失败: {result.stderr}')
        return False
    return True


def main():
    print('=== 开始更新可转债等权指数数据 ===')
    print('1. 从集思录获取数据...')
    try:
        data = fetch_jisilu_data()
        print(f'   获取到 {len(data["dates"])} 条数据')
        print(f'   日期范围: {data["dates"][0]} ~ {data["dates"][-1]}')
    except Exception as e:
        print(f'   获取数据失败: {e}')
        return False

    print('2. 更新 Excel 文件...')
    try:
        new_count = update_excel(data)
    except Exception as e:
        print(f'   更新 Excel 失败: {e}')
        return False

    print('3. 导出数据到 data.json...')
    try:
        success = export_data()
        if success:
            print('   导出成功')
        else:
            return False
    except Exception as e:
        print(f'   导出数据失败: {e}')
        return False

    print('=== 更新完成 ===')
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)