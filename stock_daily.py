# 生成{target_date}日收益日志内容，沿用"第一个空行前数据"计算规则
import argparse
import requests
import pandas as pd
import re
import json
from bs4 import BeautifulSoup
import warnings
warnings.filterwarnings('ignore')
from datetime import datetime

parser = argparse.ArgumentParser(description='生成可转债收益日志')
parser.add_argument('date', nargs='?', help='目标日期，支持 MMDD 或 YYYYMMDD 格式，例如 0517 或 20260517')
args = parser.parse_args()

if args.date:
    try:
        if len(args.date) == 4:
            dt = datetime.strptime(args.date, '%m%d')
            dt = dt.replace(year=datetime.now().year)
        elif len(args.date) == 8:
            dt = datetime.strptime(args.date, '%Y%m%d')
        else:
            dt = datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        raise SystemExit(f'日期格式错误，请使用 MMDD 或 YYYYMMDD，例如 0517 或 20260517：{args.date}')
else:
    dt = datetime.now()

# 参数变量
target_date = dt.strftime('%m%d')
month_str = dt.strftime('%Y%m')
month = int(target_date[:2])
day = int(target_date[2:])
jisilu_url = 'https://www.jisilu.cn/data/cbnew/cb_index/'
session = requests.Session()
session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        })

def fix_json_string(json_str):
    """修复非标准JSON字符串（单引号转双引号、处理特殊字符）"""
    # 1. 单引号转双引号（排除字符串内的单引号）
    json_str = re.sub(r"(?<!\\)'", '"', json_str)
    # 2. 处理末尾多余的逗号
    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*]", "]", json_str)
    # 3. 处理undefined/null等
    json_str = json_str.replace("undefined", "null")
    return json_str

def crawl_jisilu_data():
        """
        抓取集思录可转债等权指数核心数据
        :return: 价格中位数、转股价值中位数、转股溢价率中位数
        """
        try:
            response = session.get(jisilu_url, timeout=10)
            response.raise_for_status()
             # 2. 提取__data数据
            print("\n=== 提取__data字段 ===")
            data_match = re.search(r'var __data\s*=\s*({[\s\S]*?});', response.text)
            if not data_match:
                print("❌ 未找到__data字段！")
                return
            # 修复JSON格式
            raw_json = data_match.group(1)
            fixed_json = fix_json_string(raw_json)
            print("✅ 修复非标准JSON格式完成")
            
            # 解析JSON
            __data = json.loads(fixed_json)
            print("✅ 成功解析__data数据！")
            print(f"__data包含的顶级字段：{list(__data.keys())[:15]}...")  # 显示前15个字段
            
            # 4. 提取目标字段并取最后一条
            print("\n=== 提取目标字段（取最后一条） ===")
            target_fields = {
                'mid_price': '价格中位数',
                'mid_convert_value': '转股价值中位数',
                'mid_premium_rt': '转股溢价率中位数'
            }
            
            result = {}
            for field, field_name in target_fields.items():
                if field not in __data:
                    print(f"❌ {field_name}（{field}）：字段不存在")
                    continue
                
                # 获取字段数据
                field_data = __data[field]
                print(f"\n{field_name}（{field}）原始数据类型：{type(field_data)}")
                
                # 处理数据：取最后一条
                if isinstance(field_data, list):
                    print(f"{field_name}原始数据长度：{len(field_data)}")
                    # 取最后一条非空数据
                    last_value = None
                    for item in reversed(field_data):
                        if item is not None and str(item).strip() != '':
                            last_value = item
                            break
                    result[field] = last_value
                    print(f"✅ {field_name}最后一条有效数据：{last_value}")
                else:
                    # 非列表直接使用
                    result[field] = field_data
                    print(f"✅ {field_name}数据（非列表）：{field_data}")
            
            # 5. 格式化输出最终结果
            print("\n=== 最终提取结果（格式化） ===")
            price_median = round(float(result.get('mid_price', 0)), 3) if result.get('mid_price') else 0
            value_median = round(float(result.get('mid_convert_value', 0)), 3) if result.get('mid_convert_value') else 0
            premium_median = f"{round(float(result.get('mid_premium_rt', 0)), 2)}%" if result.get('mid_premium_rt') else "0%"
            
            print(f"价格中位数（mid_price）：{price_median}")
            print(f"转股价值中位数（mid_convert_value）：{value_median}")
            print(f"转股溢价率中位数（mid_premium_rt）：{premium_median}")
            
            return {
                'price_median': str(price_median),
                'value_median': str(value_median),
                'premium_median': premium_median
            }
        except Exception as e:
            print(f"抓取集思录数据失败，使用默认值：{e}")
            # 失败时返回默认值（0306日验证通过）
            return {
                'price_median': 'none',
                'value_median': 'none',
                'premium_median': 'none'
            }

def get_data_before_first_empty_row(df, key_columns):
    """取第一个空行之前的数据"""
    first_empty_row_idx = None
    for idx, row in df.iterrows():
        empty_count = sum(pd.isna(row[col]) or str(row[col]).strip() in ['', '空', 'NaN'] for col in key_columns)
        empty_ratio = empty_count / len(key_columns)
        if empty_ratio >= 0.8:
            first_empty_row_idx = idx
            break
    
    if first_empty_row_idx is not None:
        valid_data = df[df.index < first_empty_row_idx].copy()
    else:
        valid_data = df.copy()
    
    # 清理数值列
    numeric_cols = ['市价', '溢价率']
    for col in numeric_cols:
        if col in valid_data.columns:
            valid_data[col] = pd.to_numeric(valid_data[col], errors='coerce')
    
    # 最终有效数据
    final_valid_data = valid_data[
        (valid_data['市价'].notna()) & 
        (valid_data['溢价率'].notna()) & 
        (valid_data['市价'] > 0) & 
        (valid_data['溢价率'] >= 0)
    ]
    
    return final_valid_data, first_empty_row_idx

# 1. 读取Excel文件
file_path = 'D:\\my\\投资\\仓位结构.xlsx'
df_bond = pd.read_excel(file_path, sheet_name='转债')  # 转债sheet（假设数据结构不变，空行位置仍为第12行）
df_profit = pd.read_excel(file_path, sheet_name='收益日记')  # 收益日记sheet

# 2. 处理转债数据（取第一个空行前数据）
key_columns = ['证券名称', '市价', '溢价率', '证券代码']
df_valid_bond, first_empty_idx = get_data_before_first_empty_row(df_bond, key_columns)

# 计算转债轮动策略指标
strategy_avg_price = round(df_valid_bond['市价'].mean(), 2)
strategy_avg_premium = round(df_valid_bond['溢价率'].mean(), 2)


print(f"=== 转债数据处理结果（{target_date}日） ===")
print(f"第一个空行位置：第{first_empty_idx+1}行")
print(f"有效转债数量：{len(df_valid_bond)}支")
print(f"转债轮动策略均价：{strategy_avg_price}")
print(f"平均溢价率：{strategy_avg_premium}")

# 3. 提取{target_date}日收益数据
print(f"\n=== 提取{target_date}日收益数据 ===")
# 查找{target_date}相关数据
march_6_data = None
# 方式1：按日期格式筛选（{month}月{day}日）
march_6_data = df_profit[
    (pd.to_datetime(df_profit['日期'], errors='coerce').dt.month == month) & 
    (pd.to_datetime(df_profit['日期'], errors='coerce').dt.day == day)
]

# 方式2：按文本包含筛选（兼容不同日期格式）
if len(march_6_data) == 0:
    march_6_data = df_profit[df_profit['日期'].astype(str).str.contains(target_date, na=False)]

if len(march_6_data) > 0:
    day_data = march_6_data.iloc[0]
    print(f"找到{target_date}日数据，行号：{day_data.name+1}")
    
    # 提取当日核心数据（转换为百分比格式）
    stock_avg_increase = round(day_data['对应正股涨幅'] * 100, 2) if pd.notna(day_data['对应正股涨幅']) else 0.00
    bond_avg_increase = round(day_data['可转债轮动组合'] * 100, 2) if pd.notna(day_data['可转债轮动组合']) else 0.00
    actual_profit = round(day_data['可转债实盘'] * 100, 2) if pd.notna(day_data['可转债实盘']) else 0.00
    dengquan_profit = round(day_data['可转债等权指数'] * 100, 2) if pd.notna(day_data['可转债等权指数']) else 0.00

    # ST板块当日数据
    st_reorg_daily = round(day_data['ST重整'] * 100, 2) if pd.notna(day_data['ST重整']) else 0.00
    st_equal_daily = round(day_data['ST等权'] * 100, 2) if pd.notna(day_data['ST等权']) else 0.00
    st_star_daily = round(day_data['ST星等权'] * 100, 2) if pd.notna(day_data['ST星等权']) else 0.00
    st_sector_daily = round(day_data['ST板块'] * 100, 2) if pd.notna(day_data['ST板块']) else 0.00
    st_shipan_daily = round(day_data['ST实盘'] * 100, 2) if pd.notna(day_data['ST实盘']) else 0.00
    st_up_5pct = int(day_data['ST涨\n超5%']) if pd.notna(day_data['ST涨\n超5%']) else 0
    st_down_5pct = int(day_data['ST跌\n超5%']) if pd.notna(day_data['ST跌\n超5%']) else 0
    volatility = day_data['波动率'] if pd.notna(day_data['波动率']) else 0.00
    xindi = day_data['创新低'] if pd.notna(day_data['创新低']) else 0.00
    up_sectors = day_data['上涨板块'] if pd.notna(day_data['上涨板块']) else '无'
    today_profit = day_data['盈亏'] if pd.notna(day_data['盈亏']) else 0.00
    
    print(f"{target_date}日核心数据：")
    print(f"正股平均涨幅：{stock_avg_increase}%")
    print(f"转债平均涨幅：{bond_avg_increase}%")
    print(f"实际收益：{actual_profit}%")
    print(f"ST重整当日涨幅：{st_reorg_daily}%")
    print(f"上涨板块：{up_sectors}")
    print(f"今日盈亏：{today_profit}")

else:
    print(f"未找到{target_date}日数据，使用默认值填充（请检查数据）")
    # 若未找到数据，使用占位符（实际使用时需补充真实数据）
    stock_avg_increase = 0.00
    bond_avg_increase = 0.00
    actual_profit = 0.00
    st_reorg_daily = 0.00
    st_equal_daily = 0.00
    st_star_daily = 0.00
    st_sector_daily = 0.00
    st_up_5pct = 0
    st_down_5pct = 0
    volatility = 0.00
    xindi = 0
    up_sectors = "待补充"

# 4. 提取3月月度汇总数据（沿用202603汇总行）
print(f"\n=== 提取当月月度汇总数据 ===", month_str)
summary_data = df_profit[df_profit['日期'].astype(str).str.contains(month_str+'汇总', na=False)]
if len(summary_data) > 0:
    summary_row = summary_data.iloc[0]
    monthly_profit = round(summary_row['可转债实盘'] * 100, 2) if pd.notna(summary_row['可转债实盘']) else 0.00
    monthly_index = round(summary_row['可转债等权指数'] * 100, 2) if pd.notna(summary_row['可转债等权指数']) else 0.00
    
    # ST板块月度数据
    st_reorg_monthly = round(summary_row['ST重整'] * 100, 2) if pd.notna(summary_row['ST重整']) else 0.00
    st_equal_monthly = round(summary_row['ST等权'] * 100, 2) if pd.notna(summary_row['ST等权']) else 0.00
    st_star_monthly = round(summary_row['ST星等权'] * 100, 2) if pd.notna(summary_row['ST星等权']) else 0.00
    st_sector_monthly = round(summary_row['ST板块'] * 100, 2) if pd.notna(summary_row['ST板块']) else 0.00
    
    st_monthly_index = round(summary_row['ST实盘'] * 100, 2) if pd.notna(summary_row['ST实盘']) else 0.00

    print(f"3月月度汇总数据：")
    print(f"本月收益（可转债实盘）：{monthly_profit}%")
    print(f"可转债等权指数本月收益：{monthly_index}%")
    print(f"ST重整本月收益：{st_reorg_monthly}%")
else:
    print("未找到202603汇总行，月度数据使用默认值")
    monthly_profit = 0.00
    monthly_index = 0.00
    st_reorg_monthly = 0.00
    st_equal_monthly = 0.00
    st_star_monthly = 0.00
    st_sector_monthly = 0.00

# 5. 可转债等权指数参考数据（沿用标准值）

# 步骤5：抓取集思录数据（转股价值直接抓取，无推导）
jisilu_data = crawl_jisilu_data()
cb_price_median = jisilu_data["price_median"]
cb_value_median = jisilu_data["value_median"]
cb_premium_median = jisilu_data["premium_median"]

# 6. 生成{target_date}日收益日志报告
if today_profit > 0:
    profit_status = "正收益，"
else:
    profit_status = "负收益，"
dengquan_status = "赢" if actual_profit >= dengquan_profit else "输"
final_report = f"""{target_date}操作：
操作不说了，避险
==================================================================
转债轮动策略均价{strategy_avg_price}，平均溢价率{strategy_avg_premium}，仓位46，正股平均涨幅{stock_avg_increase}%，转债平均涨幅{bond_avg_increase}%，实际收益{actual_profit}%。跑{dengquan_status}等权指数。本月收益{monthly_profit}%
转债等权：价格中位数 {cb_price_median} 转股价值中位数 {cb_value_median} 转股溢价率中位数 {cb_premium_median}。本月收益{monthly_index}%
==================================================================
各种杂毛超市仓位80。
==================================================================
ST组合，仓位17，当日收益{st_shipan_daily}%，本月收益{st_monthly_index}%。
==================================================================
本日：ST重整{st_reorg_daily}%，ST等权 {st_equal_daily}%，ST星等权{st_star_daily}%，ST板块{st_sector_daily}%，涨超5%{st_up_5pct}支，跌超5%{st_down_5pct}支。
本月：ST重整{st_reorg_monthly}%，ST等权 {st_equal_monthly}%，ST星等权{st_star_monthly}%，ST板块{st_sector_monthly}%。
本日：上涨板块：{up_sectors}，波动率{volatility}， 新低股票数量{int(xindi)}支。
==================================================================
{profit_status}"""

# 7. 打印并保存报告
#print(f"\n=== {target_date}日收益日志报告 ===")
print(final_report)

# 保存报告文件
report_filename = f'D:\\my\\投资\\{target_date}日收益日志报告.txt'
#with open(report_filename, 'w', encoding='utf-8') as f:
#    f.write(final_report)

#print(f"\n{target_date}日报告已保存至：{report_filename}")

# 8. 生成数据核对表
verification_table = f"""=== {target_date}日数据核对表 ===
1. 转债策略数据
   - 计算范围：第一个空行（第{first_empty_idx+1}行）之前的{len(df_valid_bond)}支转债
   - 策略均价：{strategy_avg_price}
   - 平均溢价率：{strategy_avg_premium}
   - 仓位：38（固定）

2. 当日收益数据来源
   - 数据行数：{len(march_6_data)}行
   - 正股平均涨幅：{stock_avg_increase}%（原始值：{stock_avg_increase/100:.4f}）
   - 转债平均涨幅：{bond_avg_increase}%（原始值：{bond_avg_increase/100:.4f}）
   - 实际收益：{actual_profit}%（原始值：{actual_profit/100:.4f}）

3. 月度数据来源
   - 汇总行标识：202603汇总
   - 本月收益：{monthly_profit}%
   - 可转债等权指数本月收益：{monthly_index}%

4. 数据完整性说明
   - 转债数据：完整（{len(df_valid_bond)}/{len(df_valid_bond)}支有效）
   - 当日收益数据：{"完整" if len(march_6_data) > 0 else "缺失，需补充"}
   - 月度数据：{"完整" if len(summary_data) > 0 else "缺失，需补充"}
"""

#print(verification_table)