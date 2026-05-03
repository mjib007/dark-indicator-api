# app.py - 暗黑指標系統API
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
import json

warnings.filterwarnings('ignore')

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

class DarkIndicatorDataCollector:
    def __init__(self):
        """暗黑指標資料收集器"""
        self.base_url = "https://api.finmindtrade.com/api/v4/data"
        
        # 指標對照表 - 根據測試結果確認的資料來源
        self.indicator_mapping = {
            # 基本資料區
            "basic_info": {
                "dataset": "TaiwanStockInfo",
                "fields": {
                    "stock_id": "股票代號",
                    "stock_name": "股票名稱", 
                    "industry_category": "產業別",
                    "type": "股票類型"
                }
            },
            
            # 損益表資料
            "financial_statement": {
                "dataset": "TaiwanStockFinancialStatements",
                "fields": {
                    "營業收入": "最新季營收",
                    "營業利益（損失）": "最新季營業利益",
                    "稅前淨利（淨損）": "最新季稅前淨利",
                    "本期淨利（淨損）": "最新季淨利",
                    "營業外收入及支出": "營業外收支",
                    "基本每股盈餘（元）": "最新季EPS",
                    "營業成本": "營業成本",
                    "營業毛利（毛損）": "營業毛利"
                }
            },
            
            # 月營收資料
            "monthly_revenue": {
                "dataset": "TaiwanStockMonthRevenue",
                "fields": {
                    "revenue": "月營收",
                    "revenue_month": "營收月份",
                    "revenue_year": "營收年份"
                }
            },
            
            # 現金流量表
            "cashflow": {
                "dataset": "TaiwanStockCashFlowsStatement", 
                "fields": {
                    "營業活動之淨現金流入（流出）": "A-營業活動現金流",
                    "投資活動之淨現金流入（流出）": "B-投資活動現金流",
                    "籌資活動之淨現金流入（流出）": "C-融資活動現金流",
                    "期末現金及約當現金餘額": "E-期末現金餘額"
                }
            },
            
            # 資產負債表
            "balance_sheet": {
                "dataset": "TaiwanStockBalanceSheet",
                "fields": {
                    "資產總額": "總資產",
                    "負債總額": "總負債", 
                    "流動資產合計": "流動資產",
                    "流動負債合計": "流動負債",
                    "存貨": "存貨",
                    "應收帳款淨額": "應收帳款",
                    "普通股股本": "股本"
                }
            },
            
            # 交易資訊
            "trading_info": {
                "margin": {
                    "dataset": "TaiwanStockMarginPurchaseShortSale",
                    "fields": {
                        "MarginPurchaseTodayBalance": "融資餘額",
                        "MarginPurchaseLimit": "融資限額",
                        "ShortSaleTodayBalance": "融券餘額",
                        "ShortSaleLimit": "融券限額"
                    }
                },
                "daily_price": {
                    "dataset": "TaiwanStockPrice",
                    "fields": {
                        "Trading_Volume": "成交量",
                        "Trading_money": "成交值",
                        "open": "開盤價",
                        "close": "收盤價",
                        "max": "最高價",
                        "min": "最低價"
                    }
                },
                "day_trading": {
                    "dataset": "TaiwanStockDayTrading",
                    "fields": {
                        "Volume": "當沖成交量",
                        "BuyAmount": "當沖買進金額",
                        "SellAmount": "當沖賣出金額"
                    }
                },
                "per_pbr": {
                    "dataset": "TaiwanStockPER",
                    "fields": {
                        "PER": "本益比",
                        "PBR": "股價淨值比",
                        "dividend_yield": "殖利率"
                    }
                }
            },
            
            # 籌碼資料 (FinMind無資料)
            "institutional": {
                "fields": {
                    "超過1千張增減(%)": "FinMind無資料",
                    "全體董監增減張數": "FinMind無資料",
                    "全體董監質押(%)": "FinMind無資料", 
                    "董監持股比例": "FinMind無資料",
                    "10%大股東變動(近一年)": "FinMind無資料",
                    "10%大股東變動(最新月份)": "FinMind無資料",
                    "10%大股東近12個月增減變動次數": "FinMind無資料"
                }
            },
            
            # 特殊觀察點 (FinMind無資料)
            "special_events": {
                "fields": {
                    "庫藏股次數": "FinMind無資料",
                    "可轉債次數": "FinMind無資料"
                }
            }
        }
    
    def fetch_data(self, dataset, stock_id, start_date=None):
        """通用資料抓取方法"""
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=2*365)).strftime("%Y-%m-%d")
        
        params = {
            "dataset": dataset,
            "data_id": stock_id,
            "start_date": start_date
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == 200 and data.get("data"):
                    return data["data"]
            
            return None
            
        except Exception as e:
            print(f"API Error for {dataset}: {str(e)}")
            return None
    
    def collect_all_data(self, stock_code):
        """收集指定股票的所有暗黑指標資料"""
        try:
            result = {
                "success": True,
                "stock_code": stock_code,
                "timestamp": datetime.now().isoformat(),
                "data_availability": {},
                "raw_data": {},
                "calculated_indicators": {}
            }
            
            # 1. 基本資料
            print(f"抓取基本資料...")
            basic_data = self.fetch_data("TaiwanStockInfo", "")
            if basic_data:
                stock_info = [item for item in basic_data if item.get('stock_id') == stock_code]
                if stock_info:
                    result["raw_data"]["basic_info"] = stock_info[0]
                    result["data_availability"]["基本資料區"] = "可用"
                else:
                    result["data_availability"]["基本資料區"] = "找不到該股票"
            else:
                result["data_availability"]["基本資料區"] = "API錯誤"
            
            # 2. 財務報表資料
            print(f"抓取財務報表...")
            financial_data = self.fetch_data("TaiwanStockFinancialStatements", stock_code)
            if financial_data:
                result["raw_data"]["financial_statement"] = financial_data
                result["data_availability"]["損益表資料"] = f"可用 ({len(financial_data)}筆)"
            else:
                result["data_availability"]["損益表資料"] = "無資料"
            
            # 3. 月營收資料
            print(f"抓取月營收...")
            revenue_data = self.fetch_data("TaiwanStockMonthRevenue", stock_code)
            if revenue_data:
                result["raw_data"]["monthly_revenue"] = revenue_data
                result["data_availability"]["月營收資料"] = f"可用 ({len(revenue_data)}筆)"
            else:
                result["data_availability"]["月營收資料"] = "無資料"
            
            # 4. 現金流量表
            print(f"抓取現金流量表...")
            cashflow_data = self.fetch_data("TaiwanStockCashFlowsStatement", stock_code)
            if cashflow_data:
                result["raw_data"]["cashflow"] = cashflow_data
                result["data_availability"]["現金流量表"] = f"可用 ({len(cashflow_data)}筆)"
            else:
                result["data_availability"]["現金流量表"] = "無資料"
            
            # 5. 資產負債表
            print(f"抓取資產負債表...")
            balance_data = self.fetch_data("TaiwanStockBalanceSheet", stock_code)
            if balance_data:
                result["raw_data"]["balance_sheet"] = balance_data
                result["data_availability"]["資產負債表"] = f"可用 ({len(balance_data)}筆)"
            else:
                result["data_availability"]["資產負債表"] = "無資料"
            
            # 6. 融資融券資料
            print(f"抓取融資融券...")
            margin_data = self.fetch_data("TaiwanStockMarginPurchaseShortSale", stock_code)
            if margin_data:
                result["raw_data"]["margin_trading"] = margin_data
                result["data_availability"]["融資融券"] = f"可用 ({len(margin_data)}筆)"
            else:
                result["data_availability"]["融資融券"] = "無資料"
            
            # 7. 日股價資料
            print(f"抓取日股價...")
            daily_data = self.fetch_data("TaiwanStockPrice", stock_code)
            if daily_data:
                result["raw_data"]["daily_price"] = daily_data
                result["data_availability"]["日股價資料"] = f"可用 ({len(daily_data)}筆)"
            else:
                result["data_availability"]["日股價資料"] = "無資料"
            
            # 8. 當沖資料
            print(f"抓取當沖資料...")
            daytrading_data = self.fetch_data("TaiwanStockDayTrading", stock_code)
            if daytrading_data:
                result["raw_data"]["day_trading"] = daytrading_data
                result["data_availability"]["當沖資料"] = f"可用 ({len(daytrading_data)}筆)"
            else:
                result["data_availability"]["當沖資料"] = "無資料"
            
            # 9. 本益比資料
            print(f"抓取本益比資料...")
            per_data = self.fetch_data("TaiwanStockPER", stock_code)
            if per_data:
                result["raw_data"]["per_pbr"] = per_data
                result["data_availability"]["本益比資料"] = f"可用 ({len(per_data)}筆)"
            else:
                result["data_availability"]["本益比資料"] = "無資料"
            
            # 10. 標記FinMind無資料的項目
            result["data_availability"]["籌碼資料"] = "FinMind無資料 - 需公開資訊觀測站"
            result["data_availability"]["特殊事件"] = "FinMind無資料 - 需重大訊息"
            
            # 計算基本指標
            result["calculated_indicators"] = self._calculate_basic_indicators(result["raw_data"])
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "stock_code": stock_code,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _calculate_basic_indicators(self, raw_data):
        """計算基本指標 - 修正版，加入YoY計算和應收帳款"""
        indicators = {}
        
        try:
            print("🔧 使用修正版的_calculate_basic_indicators函數!")
            
            # 1. 基本資料處理
            if "basic_info" in raw_data:
                basic = raw_data["basic_info"]
                indicators["基本資料"] = {
                    "股票代號": basic.get("stock_id"),
                    "股票名稱": basic.get("stock_name"),
                    "產業別": basic.get("industry_category"),
                    "股票類型": basic.get("type")
                }
            
            # 2. 最新財務指標 + YoY計算
            if "financial_statement" in raw_data:
                financial_df = pd.DataFrame(raw_data["financial_statement"])
                financial_df['date'] = pd.to_datetime(financial_df['date'])
                
                # 找最新日期和去年同期
                latest_date = financial_df['date'].max()
                latest_year = latest_date.year
                latest_quarter = ((latest_date.month - 1) // 3) + 1
                
                # 計算去年同期日期
                try:
                    last_year_same_quarter = latest_date.replace(year=latest_year-1)
                except:
                    # 處理閏年問題
                    last_year_same_quarter = latest_date.replace(year=latest_year-1, month=6, day=30)
                
                print(f"計算YoY: {latest_date.strftime('%Y-%m-%d')} vs {last_year_same_quarter.strftime('%Y-%m-%d')}")
                
                latest_financial = financial_df[financial_df['date'] == latest_date]
                last_year_financial = financial_df[financial_df['date'] == last_year_same_quarter]
                
                # 提取關鍵財務項目
                financial_mapping = {
                    "營業收入": "最新季營收",
                    "營業利益（損失）": "最新季營業利益", 
                    "稅前淨利（淨損）": "最新季稅前淨利",
                    "本期淨利（淨損）": "最新季淨利",
                    "營業外收入及支出": "營業外收支",
                    "基本每股盈餘（元）": "最新季EPS",
                    "營業成本": "營業成本",
                    "營業毛利（毛損）": "營業毛利"
                }
                
                financial_indicators = {"最新財報日期": latest_date.strftime('%Y-%m-%d')}
                
                # 計算當期指標和YoY
                for origin_name, display_name in financial_mapping.items():
                    current_match = latest_financial[latest_financial['origin_name'] == origin_name]
                    last_year_match = last_year_financial[last_year_financial['origin_name'] == origin_name]
                    
                    if not current_match.empty:
                        current_value = float(current_match['value'].iloc[0])
                        financial_indicators[display_name] = current_value
                        financial_indicators[f"{display_name}_億元"] = f"{current_value/1e8:.2f}億" if abs(current_value) >= 1e8 else f"{current_value:,.0f}"
                        
                        # 計算YoY成長率
                        if not last_year_match.empty:
                            last_year_value = float(last_year_match['value'].iloc[0])
                            if last_year_value != 0:
                                yoy_growth = ((current_value - last_year_value) / abs(last_year_value)) * 100
                                financial_indicators[f"{display_name}_YoY成長率"] = f"{yoy_growth:.1f}%"
                                financial_indicators[f"{display_name}_去年同期"] = f"{last_year_value/1e8:.2f}億" if abs(last_year_value) >= 1e8 else f"{last_year_value:,.0f}"
                                print(f"✅ {display_name}YoY: {current_value/1e8:.2f}億 -> {last_year_value/1e8:.2f}億 ({yoy_growth:.1f}%)")
                            else:
                                financial_indicators[f"{display_name}_YoY成長率"] = "去年同期為0"
                        else:
                            financial_indicators[f"{display_name}_YoY成長率"] = "無去年同期資料"
                    else:
                        financial_indicators[display_name] = "無資料"
                
                indicators["損益表指標"] = financial_indicators
                
                # 計算比率
                if "營業收入" in [match['origin_name'] for _, match in latest_financial.iterrows()]:
                    revenue_val = latest_financial[latest_financial['origin_name'] == '營業收入']['value']
                    operating_val = latest_financial[latest_financial['origin_name'] == '營業利益（損失）']['value']
                    gross_val = latest_financial[latest_financial['origin_name'] == '營業毛利（毛損）']['value']
                    
                    if not revenue_val.empty and float(revenue_val.iloc[0]) != 0:
                        revenue_amount = float(revenue_val.iloc[0])
                        
                        if not operating_val.empty:
                            indicators["營業利益率%"] = f"{(float(operating_val.iloc[0]) / revenue_amount) * 100:.1f}%"
                        
                        if not gross_val.empty:
                            indicators["毛利率%"] = f"{(float(gross_val.iloc[0]) / revenue_amount) * 100:.1f}%"
            
            # 3. 月營收指標 (已有YoY)
            if "monthly_revenue" in raw_data:
                revenue_df = pd.DataFrame(raw_data["monthly_revenue"])
                if not revenue_df.empty:
                    revenue_df['date'] = pd.to_datetime(revenue_df['date'])
                    latest_revenue = revenue_df.iloc[-1]
                    
                    # 計算營收年增率
                    current_date = latest_revenue['date']
                    current_year = current_date.year
                    current_month = current_date.month
                    
                    last_year_data = revenue_df[
                        (revenue_df['date'].dt.year == current_year - 1) & 
                        (revenue_df['date'].dt.month == current_month)
                    ]
                    
                    if not last_year_data.empty:
                        current_revenue = latest_revenue['revenue']
                        last_year_revenue = last_year_data['revenue'].iloc[0]
                        yoy_growth = (current_revenue - last_year_revenue) / last_year_revenue * 100
                        
                        indicators["月營收指標"] = {
                            "最新月份": current_date.strftime('%Y-%m'),
                            "最新月營收": f"{current_revenue/1e8:.1f}億",
                            "去年同月營收": f"{last_year_revenue/1e8:.1f}億",
                            "營收年增率": f"{yoy_growth:.1f}%"
                        }
            
            # 4. 現金流指標
            if "cashflow" in raw_data:
                cf_df = pd.DataFrame(raw_data["cashflow"])
                latest_cf_date = cf_df['date'].max()
                latest_cf = cf_df[cf_df['date'] == latest_cf_date]
                
                cf_mapping = {
                    "營業活動之淨現金流入（流出）": "A-營業活動現金流",
                    "投資活動之淨現金流入（流出）": "B-投資活動現金流",
                    "籌資活動之淨現金流入（流出）": "C-融資活動現金流",
                    "期末現金及約當現金餘額": "E-期末現金餘額"
                }
                
                cf_indicators = {"最新現金流日期": latest_cf_date}
                for origin_name, display_name in cf_mapping.items():
                    match = latest_cf[latest_cf['origin_name'] == origin_name]
                    if not match.empty:
                        value = float(match['value'].iloc[0])
                        cf_indicators[display_name] = value
                        cf_indicators[f"{display_name}_億元"] = f"{value/1e8:.2f}億"
                    else:
                        cf_indicators[display_name] = "無資料"
                
                indicators["現金流指標"] = cf_indicators
            
            # 5. 資產負債指標 + YoY計算 + 應收帳款提取
            if "balance_sheet" in raw_data:
                bs_df = pd.DataFrame(raw_data["balance_sheet"])
                bs_df['date'] = pd.to_datetime(bs_df['date'])
                
                # 找最新日期和去年同期
                latest_bs_date = bs_df['date'].max()
                latest_bs_year = latest_bs_date.year
                
                try:
                    last_year_bs_date = latest_bs_date.replace(year=latest_bs_year-1)
                except:
                    last_year_bs_date = latest_bs_date.replace(year=latest_bs_year-1, month=6, day=30)
                
                latest_bs = bs_df[bs_df['date'] == latest_bs_date]
                last_year_bs = bs_df[bs_df['date'] == last_year_bs_date]
                
                print(f"資產負債表YoY計算: {latest_bs_date.strftime('%Y-%m-%d')} vs {last_year_bs_date.strftime('%Y-%m-%d')}")
                
                bs_mapping = {
                    "資產總額": "總資產",
                    "負債總額": "總負債",
                    "流動資產合計": "流動資產", 
                    "流動負債合計": "流動負債",
                    "存貨": "存貨",
                    "應收帳款淨額": "應收帳款",  # 關鍵：加入應收帳款！
                    "普通股股本": "股本"
                }
                
                bs_indicators = {"最新資產負債表日期": latest_bs_date.strftime('%Y-%m-%d')}
                bs_values = {}
                
                for origin_name, display_name in bs_mapping.items():
                    current_match = latest_bs[latest_bs['origin_name'] == origin_name]
                    last_year_match = last_year_bs[last_year_bs['origin_name'] == origin_name]
                    
                    if not current_match.empty:
                        current_value = float(current_match['value'].iloc[0])
                        bs_values[display_name] = current_value
                        bs_indicators[display_name] = current_value
                        bs_indicators[f"{display_name}_億元"] = f"{current_value/1e8:.2f}億"
                        
                        # 計算YoY成長率
                        if not last_year_match.empty:
                            last_year_value = float(last_year_match['value'].iloc[0])
                            if last_year_value != 0:
                                yoy_growth = ((current_value - last_year_value) / abs(last_year_value)) * 100
                                bs_indicators[f"{display_name}_YoY成長率"] = f"{yoy_growth:.1f}%"
                                bs_indicators[f"{display_name}_去年同期"] = f"{last_year_value/1e8:.2f}億"
                                
                                # 特別標註重要指標
                                if display_name in ["應收帳款", "存貨"]:
                                    print(f"✅ {display_name}YoY: {current_value/1e8:.2f}億 -> {last_year_value/1e8:.2f}億 ({yoy_growth:.1f}%)")
                            else:
                                bs_indicators[f"{display_name}_YoY成長率"] = "去年同期為0"
                        else:
                            bs_indicators[f"{display_name}_YoY成長率"] = "無去年同期資料"
                    else:
                        bs_indicators[display_name] = "無資料"
                        print(f"⚠️ 找不到 {origin_name} 欄位")
                
                # 計算比率
                if "總負債" in bs_values and "總資產" in bs_values and bs_values["總資產"] != 0:
                    debt_ratio = (bs_values["總負債"] / bs_values["總資產"]) * 100
                    bs_indicators["負債比率"] = f"{debt_ratio:.1f}%"
                
                if "流動資產" in bs_values and "流動負債" in bs_values and bs_values["流動負債"] != 0:
                    current_ratio = bs_values["流動資產"] / bs_values["流動負債"]
                    bs_indicators["流動比率"] = f"{current_ratio:.2f}"
                
                if all(k in bs_values for k in ["流動資產", "存貨", "流動負債"]) and bs_values["流動負債"] != 0:
                    quick_ratio = (bs_values["流動資產"] - bs_values["存貨"]) / bs_values["流動負債"]
                    bs_indicators["速動比率"] = f"{quick_ratio:.2f}"
                
                indicators["資產負債指標"] = bs_indicators
            
            # 6. 交易指標
            trading_indicators = {}
            
            # 十日平均成交量 + 週轉率 - 新增！
            if "daily_price" in raw_data:
                daily_df = pd.DataFrame(raw_data["daily_price"])
                if not daily_df.empty and len(daily_df) >= 10:
                    # 取最近10天的資料
                    recent_10_days = daily_df.tail(10)
                    avg_volume_10d = recent_10_days['Trading_Volume'].mean()
                    latest_volume = daily_df.iloc[-1]['Trading_Volume']
                    
                    # 計算週轉率（需要股本資料）
                    if "balance_sheet" in raw_data:
                        bs_df = pd.DataFrame(raw_data["balance_sheet"])
                        bs_df['date'] = pd.to_datetime(bs_df['date'])
                        latest_bs = bs_df[bs_df['date'] == bs_df['date'].max()]
                        stock_capital_match = latest_bs[latest_bs['origin_name'] == '普通股股本']
                        
                        if not stock_capital_match.empty:
                            stock_capital = float(stock_capital_match['value'].iloc[0]) / 10  # 股本轉換為股數
                            daily_turnover = (latest_volume / stock_capital) * 100
                            turnover_10d = (avg_volume_10d / stock_capital) * 100
                            
                            trading_indicators.update({
                                "10日平均成交量": f"{avg_volume_10d:,.0f}股",
                                "10日平均成交量_張": f"{avg_volume_10d/1000:,.0f}張",
                                "最新成交量": f"{latest_volume:,.0f}股",
                                "最新成交量_張": f"{latest_volume/1000:,.0f}張",
                                "量比": f"{(latest_volume / avg_volume_10d * 100):.1f}%",
                                "單日週轉率": f"{daily_turnover:.2f}%",
                                "10日平均週轉率": f"{turnover_10d:.2f}%"
                            })
                        else:
                            # 沒有股本資料，只顯示成交量
                            trading_indicators.update({
                                "10日平均成交量": f"{avg_volume_10d:,.0f}股",
                                "10日平均成交量_張": f"{avg_volume_10d/1000:,.0f}張",
                                "最新成交量": f"{latest_volume:,.0f}股",
                                "最新成交量_張": f"{latest_volume/1000:,.0f}張",
                                "量比": f"{(latest_volume / avg_volume_10d * 100):.1f}%"
                            })
                    else:
                        # 沒有資產負債表，只顯示成交量
                        trading_indicators.update({
                            "10日平均成交量": f"{avg_volume_10d:,.0f}股",
                            "10日平均成交量_張": f"{avg_volume_10d/1000:,.0f}張",
                            "最新成交量": f"{latest_volume:,.0f}股",
                            "最新成交量_張": f"{latest_volume/1000:,.0f}張",
                            "量比": f"{(latest_volume / avg_volume_10d * 100):.1f}%"
                        })            
            # 融資融券
            if "margin_trading" in raw_data:
                margin_df = pd.DataFrame(raw_data["margin_trading"])
                if not margin_df.empty:
                    latest_margin = margin_df.iloc[-1]
                    融資餘額 = latest_margin.get('MarginPurchaseTodayBalance', 0)
                    融資限額 = latest_margin.get('MarginPurchaseLimit', 0)
                    
                    trading_indicators.update({
                        "融資餘額": f"{融資餘額:,}張",
                        "融資限額": f"{融資限額:,}張",
                        "融資使用率": f"{(融資餘額/融資限額*100):.2f}%" if 融資限額 > 0 else "無法計算"
                    })
            
            # 本益比
            if "per_pbr" in raw_data:
                per_df = pd.DataFrame(raw_data["per_pbr"])
                if not per_df.empty:
                    latest_per = per_df.iloc[-1]
                    trading_indicators.update({
                        "本益比": latest_per.get('PER', '無資料'),
                        "股價淨值比": latest_per.get('PBR', '無資料'),
                        "殖利率": f"{latest_per.get('dividend_yield', 0):.2f}%" if latest_per.get('dividend_yield') else '無資料'
                    })

            # 當沖率計算
            if "day_trading" in raw_data and "daily_price" in raw_data:
                daytrading_df = pd.DataFrame(raw_data["day_trading"])
                daily_df = pd.DataFrame(raw_data["daily_price"])

                if not daytrading_df.empty and not daily_df.empty:
                    latest_daytrading = daytrading_df.iloc[-1]
                    latest_daily = daily_df.iloc[-1]

                    daytrading_volume = latest_daytrading.get('Volume', 0)
                    total_volume = latest_daily.get('Trading_Volume', 0)

                    if total_volume > 0:
                        daytrading_rate = (daytrading_volume / total_volume) * 100
                        trading_indicators["現股當沖率"] = f"{daytrading_rate:.2f}%"
                    else:
                        trading_indicators["現股當沖率"] = "0%"

            # 整合交易指標
            if trading_indicators:
                indicators["交易指標"] = trading_indicators

            # 7. YoY成長率總結
            yoy_summary = {}

            if "損益表指標" in indicators:
                profit_indicators = indicators["損益表指標"]
                yoy_summary["獲利成長分析"] = {
                    "淨利YoY": profit_indicators.get("最新季淨利_YoY成長率", "無資料"),
                    "EPS_YoY": profit_indicators.get("最新季EPS_YoY成長率", "無資料"),
                    "營收YoY": profit_indicators.get("最新季營收_YoY成長率", "無資料"),
                    "營業利益YoY": profit_indicators.get("最新季營業利益_YoY成長率", "無資料")
                }

            if "資產負債指標" in indicators:
                balance_indicators = indicators["資產負債指標"]
                yoy_summary["資產成長分析"] = {
                    "應收帳款YoY": balance_indicators.get("應收帳款_YoY成長率", "無資料"),
                    "存貨YoY": balance_indicators.get("存貨_YoY成長率", "無資料"),
                    "總資產YoY": balance_indicators.get("總資產_YoY成長率", "無資料")
                }

            if yoy_summary:
                indicators["YoY成長率總結"] = yoy_summary

            # 9. 營運品質雙重過濾規則 (新增功能)
            if "損益表指標" in indicators and "資產負債指標" in indicators:
                try:
                    def parse_yoy(yoy_str):
                        if not isinstance(yoy_str, str) or "%" not in yoy_str:
                            return None
                        return float(yoy_str.replace("%", ""))

                    rev_yoy = parse_yoy(indicators["損益表指標"].get("最新季營收_YoY成長率"))
                    rec_yoy = parse_yoy(indicators["資產負債指標"].get("應收帳款_YoY成長率"))
                    inv_yoy = parse_yoy(indicators["資產負債指標"].get("存貨_YoY成長率"))

                    if rev_yoy is not None:
                        quality_analysis = {"分析基準(營收YoY)": f"{rev_yoy}%"}
                        
                        if rec_yoy is not None:
                            status = "通過 ✅" if rec_yoy < rev_yoy else "警示 ⚠️"
                            quality_analysis["1.應收帳款檢驗(回款能力)"] = {
                                "數值": f"{rec_yoy}%",
                                "結果": status,
                                "說明": "應收帳款增速低於營收" if status == "通過 ✅" else "應收帳款增速過快，注意回款風險"
                            }
                        
                        if inv_yoy is not None:
                            status = "通過 ✅" if inv_yoy < rev_yoy else "警示 ⚠️"
                            quality_analysis["2.存貨檢驗(銷售效率)"] = {
                                "數值": f"{inv_yoy}%",
                                "結果": status,
                                "說明": "存貨增速低於營收" if status == "通過 ✅" else "存貨堆積速度高於銷售速度"
                            }
                        
                        if len(quality_analysis) > 1:
                            indicators["營運品質分析"] = quality_analysis
                except Exception as e:
                    print(f"營運品質分析計算出錯: {e}")

            # 10. 標記無資料項目
            indicators["FinMind無資料項目"] = {
                "籌碼資料": {
                    "超過1千張增減(%)": "需公開資訊觀測站",
                    "全體董監增減張數": "需公開資訊觀測站",
                    "全體董監質押(%)": "需公開資訊觀測站",
                    "董監持股比例": "需公開資訊觀測站",
                    "10%大股東變動(近一年)": "需公開資訊觀測站",
                    "10%大股東變動(最新月份)": "需公開資訊觀測站",
                    "10%大股東近12個月增減變動次數": "需公開資訊觀測站"
                },
                "特殊事件": {
                    "庫藏股次數": "需重大訊息公告",
                    "可轉債次數": "需重大訊息公告"
                }
            }

        except Exception as e:
            indicators["計算錯誤"] = str(e)
            print(f"計算錯誤: {str(e)}")

        return indicators

# 建立資料收集器實例
collector = DarkIndicatorDataCollector()

@app.route('/')
def home():
    """API首頁"""
    return jsonify({
        "message": "暗黑指標系統 API",
        "version": "1.0",
        "description": "提供完整的股票暗黑指標資料收集",
        "endpoints": {
            "/dark-indicators/<stock_code>": "取得指定股票的所有暗黑指標資料",
            "/raw-data/<stock_code>": "取得指定股票的原始資料",
            "/health": "健康檢查"
        },
        "author": "暗黑指標系統",
        "note": "包含FinMind可用資料與無資料項目標記"
    })

@app.route('/dark-indicators/<stock_code>')
def get_dark_indicators(stock_code):
    """取得指定股票的完整暗黑指標資料"""
    if not stock_code or len(stock_code) < 4:
        return jsonify({"success": False, "error": "無效的股票代碼"}), 400
    
    print(f"開始收集 {stock_code} 的暗黑指標資料...")
    result = collector.collect_all_data(stock_code)
    
    if result["success"]:
        return jsonify(result)
    else:
        return jsonify(result), 500

@app.route('/raw-data/<stock_code>')
def get_raw_data(stock_code):
    """取得指定股票的原始資料 (專為OpenAI分析設計)"""
    if not stock_code or len(stock_code) < 4:
        return jsonify({"success": False, "error": "無效的股票代碼"}), 400
    
    try:
        print(f"收集 {stock_code} 的原始資料供AI分析...")
        
        # 收集所有資料
        all_data = collector.collect_all_data(stock_code)
        
        if not all_data["success"]:
            return jsonify(all_data), 500
        
        # 為AI分析重新組織資料格式
        ai_ready_data = {
            "analysis_target": {
                "stock_code": stock_code,
                "analysis_date": datetime.now().strftime("%Y-%m-%d"),
                "data_source": "FinMind API"
            },
            
            "available_data": all_data["data_availability"],
            
            "financial_data": {
                "基本資料": all_data["calculated_indicators"].get("基本資料", {}),
                "最新財務指標": all_data["calculated_indicators"].get("損益表指標", {}),
                "月營收資料": all_data["calculated_indicators"].get("月營收指標", {}),
                "現金流指標": all_data["calculated_indicators"].get("現金流指標", {}),
                "資產負債指標": all_data["calculated_indicators"].get("資產負債指標", {}),
                "交易指標": all_data["calculated_indicators"].get("交易指標", {}),
                "YoY成長率總結": all_data["calculated_indicators"].get("YoY成長率總結", {})
            },
            
            "risk_analysis_framework": {
                "現金流六大檢驗規則": {
                    "規則1": "A營業現金流是否逐年增加",
                    "規則2": "B投資現金流以負值為優，且|B|<A較佳",  
                    "規則3": "B為負值時，A是否增加(資本支出效益)",
                    "規則4": "C融資現金流合理性檢查",
                    "規則5": "A>D較佳(現金流品質)",
                    "規則6": "E期末餘額增加或穩定"
                },
                
                "五大致命組合": {
                    "致命組合1": "債務+現金流危機: 營業現金流<0 + 負債比>50% + 流動比<1.0",
                    "致命組合2": "融資賣壓崩盤: 融資使用率>60% + 融資賣壓倍數>0.3 + 當沖率>30%",
                    "致命組合3": "獲利品質惡化: 營收成長>10% + EPS衰退>-10% + 業外比重>50%",
                    "致命組合4": "內部人逃命: 董監持股下降 + 質押率>30% + 大股東異動>3次",
                    "致命組合5": "矛盾護盤: 庫藏股+可轉債同時發生"
                },
                
                "警示標準": {
                    "營收成長率": "< 0% 為警示",
                    "EPS年增率": "< 0% 為警示", 
                    "營業利益率": "< 5% 為警示",
                    "毛利率": "< 10% 為警示",
                    "業外損益比重": "> 50% 為警示",
                    "負債比率": "> 50% 為警示",
                    "流動比率": "< 1.0 為警示",
                    "速動比率": "< 0.8 為警示",
                    "融資使用率": "> 60% 為警示",
                    "本益比": "< 0 或 > 50 為警示"
                }
            },
            
            "missing_data_items": all_data["calculated_indicators"].get("FinMind無資料項目", {}),
            
            "analysis_instructions": {
                "請分析": [
                    "1. 根據現金流六大檢驗規則分析企業現金流健康度",
                    "2. 檢查是否符合五大致命組合的任一組合",
                    "3. 計算各項財務比率並對照警示標準",
                    "4. 評估整體財務風險等級 (低風險🟢/中風險🟡/高風險🔴)",
                    "5. 提供具體的投資建議和風險提醒"
                ],
                "分析重點": [
                    "財務體質是否健康",
                    "現金流結構是否合理", 
                    "是否有隱藏的財務風險",
                    "籌碼面是否穩定 (雖然FinMind無此資料)",
                    "估值是否合理"
                ],
                "輸出格式": "請提供結構化的分析報告，包含風險等級、主要發現、具體建議"
            }
        }
        
        return jsonify({
            "success": True,
            "ready_for_ai_analysis": True,
            "data": ai_ready_data,
            "timestamp": datetime.now().isoformat(),
            "note": "此資料已格式化供OpenAI分析使用"
        })
        
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/indicators-list')
def get_indicators_list():
    """取得暗黑指標清單與說明"""
    return jsonify({
        "success": True,
        "indicators_overview": {
            "總指標數": "39項",
            "FinMind可用": "32項 (82%)",
            "需其他資料源": "7項 (18%)"
        },
        
        "available_indicators": {
            "基本資料區": ["股票代號", "股票名稱", "產業別", "股票類型"],
            
            "損益表資料": [
                "最新月份營收", "最新月份營收YoY%", "最近十二個月累計營收",
                "最新十二個月累計營收YoY%", "最新營業利益率", "最新營業利益率%",
                "最新季淨利", "最新季淨利YoY%", "最新季EPS", "最新季EPS_YoY%",
                "本益比", "單季業外損益佔稅前淨利%", "累季業外損益佔稅前淨利%"
            ],
            
            "現金流量表": [
                "A-營業活動現金流", "B-投資活動現金流", "C-融資活動現金流",
                "D-稅前淨利", "E-期末現金餘額"
            ],
            
            "交易資訊區": [
                "融資使用率%", "融資餘額", "10日成交量", "融資餘額/10日成交量",
                "股本", "現股當沖率%", "12日週轉率"
            ],
            
            "債務壓力區": ["負債比率", "流動比率", "速動比率"]
        },
        
        "unavailable_indicators": {
            "籌碼區": [
                "超過1千張增減(%)", "全體董監增減張數", "全體董監質押(%)",
                "董監持股比例", "10%大股東變動(近一年)", "10%大股東變動(最新月份)",
                "10%大股東近12個月增減變動次數"
            ],
            "特殊觀察點": ["庫藏股次數", "可轉債次數"]
        },
        
        "data_sources": {
            "FinMind_API": "免費使用，涵蓋核心財務指標",
            "公開資訊觀測站": "籌碼面資料需要",
            "重大訊息公告": "特殊事件資料需要"
        }
    })

@app.route('/health')
def health_check():
    """健康檢查"""
    return jsonify({
        "status": "healthy", 
        "service": "暗黑指標系統API",
        "timestamp": datetime.now().isoformat(),
        "endpoints_available": [
            "/", "/dark-indicators/<stock_code>", "/raw-data/<stock_code>", 
            "/indicators-list", "/health"
        ]
    })

@app.route('/test/<stock_code>')
def test_api(stock_code):
    """測試API功能"""
    return jsonify({
        "message": f"測試 {stock_code} 的API連接",
        "timestamp": datetime.now().isoformat(),
        "next_step": f"請使用 /dark-indicators/{stock_code} 取得完整資料"
    })

if __name__ == '__main__':
    # Zeabur會自動設定PORT環境變數
    import os
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)