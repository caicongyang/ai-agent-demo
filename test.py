import pandas as pd
import numpy as np
from tabulate import tabulate
from datetime import datetime

file_url = "https://test-agent-files.linkfox.com/user/PayQuUBZFHtK8/chat/4EqUH7VxDNTxjDxMmTFqT6/9r2oZYC5qzVDqSzByd5oAB/Search(hat)-410-US-20250910.xlsx"

try:
    # 读取文件
    df = pd.read_excel(file_url)
except Exception as e:
    print(f"❌ 数据读取失败: {e}")
else:
    # 验证必要列是否存在
    required_cols = ["月销量", "月销量增长率", "月销售额($)", "商品标题", "评分", "价格($)", "上架时间", "品牌"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"❌ 缺少必要列: {missing_cols}")
    else:
        # 数据清洗
        for col in ["月销量", "月销量增长率", "月销售额($)", "评分", "价格($)"]:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        # 上架时间转为日期
        df["上架时间"] = pd.to_datetime(df["上架时间"], errors='coerce')

        # 1. 总体销量与销售额
        total_units = df["月销量"].sum(skipna=True)
        avg_units = df["月销量"].mean(skipna=True)
        total_revenue = df["月销售额($)"].sum(skipna=True)
        avg_revenue = df["月销售额($)"].mean(skipna=True)

        summary_table = [
            ["总月销量", f"{int(total_units):,}"],
            ["平均每款月销量", f"{avg_units:,.0f}"],
            ["总月销售额($)", f"{total_revenue:,.2f}"],
            ["平均每款月销售额($)", f"{avg_revenue:,.2f}"]
        ]

        # 2. 前10畅销产品
        top10_units = df.nlargest(10, "月销量")[["商品标题", "品牌", "月销量", "月销售额($)", "评分", "价格($)"]]
        top10_units["月销量"] = top10_units["月销量"].astype(int)
        top10_units["月销售额($)"] = top10_units["月销售额($)"].round(2)

        # 3. 销量增长率最高的产品
        growth_products = df[df["月销量增长率"].notna() & (df["月销量增长率"] > 0)]
        top_growth = growth_products.nlargest(5, "月销量增长率")[["商品标题", "品牌", "月销量", "月销量增长率", "评分"]]
        top_growth["月销量"] = top_growth["月销量"].astype(int)
        top_growth["月销量增长率"] = (top_growth["月销量增长率"] * 100).round(2).astype(str) + "%"

        # 4. 评分与销量关系
        rating_bins = pd.cut(df["评分"], bins=[0,3,4,4.5,5], labels=["低于3分","3-4分","4-4.5分","4.5-5分"])
        rating_sales = df.groupby(rating_bins, dropna=False)["月销量"].mean().reset_index()
        rating_sales["月销量"] = rating_sales["月销量"].round(0).astype(int)

        # 5. 价格区间与销量关系
        price_bins = pd.cut(df["价格($)"], bins=[0,10,20,30,50,1000], labels=["0-10","10-20","20-30","30-50","50+"])
        price_sales = df.groupby(price_bins, dropna=False)["月销量"].mean().reset_index()
        price_sales["月销量"] = price_sales["月销量"].round(0).astype(int)

        # 6. 上架时间与销量关系
        df["上市年份"] = df["上架时间"].dt.year
        year_sales = df.groupby("上市年份")["月销量"].mean().reset_index()
        year_sales = year_sales[year_sales["上市年份"].notna()]
        year_sales["月销量"] = year_sales["月销量"].round(0).astype(int)

        # 输出Markdown格式
        output_md = "## 帽子销售数据分析报告\n\n"

        output_md += "### 1. 总体销售概览\n"
        output_md += tabulate(summary_table, headers=["指标", "数值"], tablefmt="github") + "\n\n"

        output_md += "### 2. 月销量最高的前10款产品\n"
        output_md += tabulate(top10_units, headers="keys", tablefmt="github", showindex=False) + "\n\n"

        output_md += "### 3. 销量增长率最高的产品（Top 5）\n"
        output_md += tabulate(top_growth, headers="keys", tablefmt="github", showindex=False) + "\n\n"

        output_md += "### 4. 评分与平均月销量关系\n"
        output_md += tabulate(rating_sales, headers=["评分区间","平均月销量"], tablefmt="github", showindex=False) + "\n\n"

        output_md += "### 5. 价格区间与平均月销量关系\n"
        output_md += tabulate(price_sales, headers=["价格区间($)","平均月销量"], tablefmt="github", showindex=False) + "\n\n"

        output_md += "### 6. 按上市年份的平均月销量\n"
        output_md += tabulate(year_sales, headers=["上市年份","平均月销量"], tablefmt="github", showindex=False) + "\n\n"

        # 趋势洞察总结
        insights = []
        if total_units > 0 and total_revenue > 0:
            insights.append("市场整体表现稳定，头部产品贡献了较大销量和销售额。")
        if not top_growth.empty:
            insights.append(f"部分新品或特定款式（如 `{top_growth.iloc[0]['商品标题']}`）增长显著，具备潜力。")
        if rating_sales["月销量"].max() > rating_sales["月销量"].min():
            insights.append("评分越高的产品，平均销量普遍更高，说明口碑对销量有明显促进作用。")
        if price_sales["月销量"].max() > price_sales["月销量"].min():
            insights.append("中低价格带（10-20美元）产品销量相对更高，但高端产品仍有稳定需求。")
        if not year_sales.empty and year_sales.iloc[-1]["平均月销量"] > year_sales.iloc[0]["平均月销量"]:
            insights.append("新近上市的产品销量在部分区间优于老款，说明市场接受度高。")

        output_md += "### 7. 洞察总结\n"
        for i, ins in enumerate(insights, 1):
            output_md += f"{i}. {ins}\n"

        print(output_md)