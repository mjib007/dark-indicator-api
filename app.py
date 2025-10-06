# app_dark_indicator.py - 暗黑指標 Flask API
from flask import Flask, jsonify, request
from flask_cors import CORS
from FinMind.data import DataLoader
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

app = Flask(__name__)
CORS(app)

class DarkIndicatorCalculator:
    def __init__(self):
        self.dl = DataLoader()
        self.end_date = datetime.now().strftime("%Y-%m-%d")
        self.start_date = (datetime.now() - timedelta(days=365*3)).strftime("%Y-%m-%d")
    
    def safe_get_last(self, df, column_name):
        """安全地取得最後一筆資料"""
        if column_name in df.columns and len(df[column_name].dropna()) > 0:
            return df[column_name].dropna().iloc[-1]
        return None
    
    def get_basic_info(self, stock_id):
        """取得股票基本資料"""
        try:
            info = self.dl.taiwan_stock_info()
            stock_info = info[info['stock_id'] == stock_id]
            return stock_info.iloc[0] if not stock_info.empty else None
        except:
            return None
    
    def calculate_revenue_indicators(self, stock_id):
        """計算營收相關指標"""
        try:
            revenue = self.dl.taiwan_stock_month_revenue(
                stock_id=stock_id,
                start_date=self.start_date,
                end_date=self.end_date
            )
            
            if revenue.empty:
                return {}
            
            revenue = revenue.sort_values('date')
            revenue['revenue'] = pd.to_numeric(revenue['revenue'], errors='coerce')
            revenue['revenue_yoy'] = revenue['revenue'].pct_change(12) * 100
            
            latest = revenue.iloc[-1]
            
            # 累計年營收成長率
            if len(revenue) >= 24:
                recent_12m = revenue.iloc[-12:]['revenue'].sum()
                previous_12m = revenue.iloc[-24:-12]['revenue'].sum()
                annual_revenue_growth = ((recent_12m - previous_12m) / previous_12m * 100) if previous_12m > 0 else None
            else:
                annual_revenue_growth = None
            
            return {
                'latest_revenue': float(latest['revenue']),
                'revenue_yoy': float(latest['revenue_yoy']) if pd.notna(latest['revenue_yoy']) else None,
                'annual_revenue_growth': float(annual_revenue_growth) if annual_revenue_growth is not None else None
            }
        except Exception as e:
            print(f"營收指標錯誤: {e}")
            return {}
    
    def calculate_financial_indicators(self, stock_id):
        """計算財務報表指標"""
        try:
            # 損益表
            income = self.dl.taiwan_stock_financial_statement(
                stock_id=stock_id,
                start_date=self.start_date,
                end_date=self.end_date
            )
            
            # 資產負債表
            balance = self.dl.taiwan_stock_balance_sheet(
                stock_id=stock_id,
                start_date=self.start_date,
                end_date=self.end_date
            )
            
            # 現金流量表
            cashflow = self.dl.taiwan_stock_cash_flows_statement(
                stock_id=stock_id,
                start_date=self.start_date,
                end_date=self.end_date
            )
            
            results = {}
            
            # 處理損益表
            if not income.empty:
                income_pivot = income.pivot_table(index='date', columns='type', values='value', aggfunc='first')
                
                if 'Revenue' in income_pivot.columns and 'GrossProfit' in income_pivot.columns:
                    income_pivot['gross_margin'] = (income_pivot['GrossProfit'] / income_pivot['Revenue'] * 100)
                    results['latest_gross_margin'] = float(self.safe_get_last(income_pivot, 'gross_margin')) if self.safe_get_last(income_pivot, 'gross_margin') is not None else None
                
                if 'ProfitLossFromContinuingOperations' in income_pivot.columns:
                    net_income_series = income_pivot['ProfitLossFromContinuingOperations'].dropna()
                    if len(net_income_series) >= 8:
                        recent_4q_profit = net_income_series.iloc[-4:].sum()
                        previous_4q_profit = net_income_series.iloc[-8:-4].sum()
                        results['annual_profit_growth'] = float((recent_4q_profit - previous_4q_profit) / abs(previous_4q_profit) * 100) if previous_4q_profit != 0 else None
            
            # 處理資產負債表
            if not balance.empty:
                balance_pivot = balance.pivot_table(index='date', columns='type', values='value', aggfunc='first')
                
                # 存貨、應收帳款成長率
                if 'Inventories' in balance_pivot.columns:
                    balance_pivot['inventory_growth'] = balance_pivot['Inventories'].pct_change(4) * 100
                    results['inventory_growth'] = float(self.safe_get_last(balance_pivot, 'inventory_growth')) if self.safe_get_last(balance_pivot, 'inventory_growth') is not None else None
                
                if 'AccountsReceivableNet' in balance_pivot.columns:
                    balance_pivot['ar_growth'] = balance_pivot['AccountsReceivableNet'].pct_change(4) * 100
                    results['ar_growth'] = float(self.safe_get_last(balance_pivot, 'ar_growth')) if self.safe_get_last(balance_pivot, 'ar_growth') is not None else None
                
                # 基本財務數據
                results['cash_A'] = float(self.safe_get_last(balance_pivot, 'CashAndCashEquivalents')) if self.safe_get_last(balance_pivot, 'CashAndCashEquivalents') is not None else None
                results['current_liabilities'] = float(self.safe_get_last(balance_pivot, 'CurrentLiabilities')) if self.safe_get_last(balance_pivot, 'CurrentLiabilities') is not None else None
                results['current_assets'] = float(self.safe_get_last(balance_pivot, 'CurrentAssets')) if self.safe_get_last(balance_pivot, 'CurrentAssets') is not None else None
                results['total_liabilities'] = float(self.safe_get_last(balance_pivot, 'Liabilities')) if self.safe_get_last(balance_pivot, 'Liabilities') is not None else None
                results['total_assets'] = float(self.safe_get_last(balance_pivot, 'TotalAssets')) if self.safe_get_last(balance_pivot, 'TotalAssets') is not None else None
                
                # 債務比率
                if results.get('total_liabilities') and results.get('total_assets'):
                    results['debt_ratio'] = float(results['total_liabilities'] / results['total_assets'] * 100)
                
                if results.get('current_assets') and results.get('current_liabilities'):
                    results['current_ratio'] = float(results['current_assets'] / results['current_liabilities'])
                
                inventory = self.safe_get_last(balance_pivot, 'Inventories')
                if results.get('current_assets') and results.get('current_liabilities') and inventory:
                    results['quick_ratio'] = float((results['current_assets'] - inventory) / results['current_liabilities'])
            
            # 處理現金流量表
            if not cashflow.empty:
                cashflow_pivot = cashflow.pivot_table(index='date', columns='type', values='value', aggfunc='first')
                
                results['operating_cashflow'] = float(self.safe_get_last(cashflow_pivot, 'CashFlowsFromOperatingActivities')) if self.safe_get_last(cashflow_pivot, 'CashFlowsFromOperatingActivities') is not None else None
                results['investing_cashflow'] = float(self.safe_get_last(cashflow_pivot, 'CashFlowsFromInvestingActivities')) if self.safe_get_last(cashflow_pivot, 'CashFlowsFromInvestingActivities') is not None else None
                results['financing_cashflow'] = float(self.safe_get_last(cashflow_pivot, 'CashFlowsFromFinancingActivities')) if self.safe_get_last(cashflow_pivot, 'CashFlowsFromFinancingActivities') is not None else None
            
            return results
        except Exception as e:
            print(f"財務指標錯誤: {e}")
            return {}
    
    def calculate_trading_indicators(self, stock_id):
        """計算交易面指標"""
        try:
            # 股價資料
            price = self.dl.taiwan_stock_daily(
                stock_id=stock_id,
                start_date=self.start_date,
                end_date=self.end_date
            )
            
            # 融資融券
            margin = self.dl.taiwan_stock_margin_purchase_short_sale(
                stock_id=stock_id,
                start_date=self.start_date,
                end_date=self.end_date
            )
            
            # 當沖
            day_trading = self.dl.taiwan_stock_day_trading(
                stock_id=stock_id,
                start_date=self.start_date,
                end_date=self.end_date
            )
            
            results = {}
            
            if not price.empty:
                price = price.sort_values('date')
                latest_price = price.iloc[-1]
                
                results['latest_close'] = float(latest_price['close'])
                results['latest_volume'] = int(latest_price['Trading_Volume'])
                
                if len(price) >= 10:
                    results['avg_10day_volume'] = float(price.tail(10)['Trading_Volume'].mean())
                if len(price) >= 60:
                    results['avg_60day_volume'] = float(price.tail(60)['Trading_Volume'].mean())
            
            if not margin.empty:
                margin = margin.sort_values('date')
                latest_margin = margin.iloc[-1]
                
                margin_balance = latest_margin.get('MarginPurchaseTodayBalance', 0)
                margin_limit = latest_margin.get('MarginPurchaseLimit', 1)
                
                results['margin_balance_shares'] = float(margin_balance)
                results['margin_usage_rate'] = float(margin_balance / margin_limit * 100) if margin_limit > 0 else 0
            
            if not day_trading.empty and not price.empty:
                day_trading = day_trading.sort_values('date')
                merged = pd.merge(day_trading, price, on=['date', 'stock_id'], how='inner')
                if not merged.empty:
                    merged['day_trading_rate'] = (merged['Volume'] / merged['Trading_Volume'] * 100)
                    results['day_trading_rate'] = float(merged['day_trading_rate'].iloc[-1])
            
            return results
        except Exception as e:
            print(f"交易指標錯誤: {e}")
            return {}
    
    def analyze_stock(self, stock_id):
        """分析股票 - API主要方法"""
        try:
            # 基本資料
            basic_info = self.get_basic_info(stock_id)
            if basic_info is None:
                return {"success": False, "error": f"找不到股票 {stock_id}"}
            
            # 計算各類指標
            revenue_indicators = self.calculate_revenue_indicators(stock_id)
            financial_indicators = self.calculate_financial_indicators(stock_id)
            trading_indicators = self.calculate_trading_indicators(stock_id)
            
            # 整合結果
            all_indicators = {
                'stock_id': stock_id,
                'stock_name': basic_info['stock_name'],
                'industry': basic_info['industry_category'],
                **revenue_indicators,
                **financial_indicators,
                **trading_indicators
            }
            
            # 計算衍生指標和警示
            warnings_result = self.generate_warnings(all_indicators)
            
            return {
                "success": True,
                "stock_id": stock_id,
                "stock_name": basic_info['stock_name'],
                "industry": basic_info['industry_category'],
                "indicators": all_indicators,
                "warnings": warnings_result['warnings'],
                "warning_explanations": warnings_result['warning_explanations'],
                "warning_count": warnings_result['warning_count'],
                "total_indicators_checked": warnings_result['total_indicators_checked'],
                "warning_ratio": warnings_result['warning_ratio'],
                "risk_level": warnings_result['risk_level'],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def generate_warnings(self, indicators):
        """生成警示（簡化版，包含白話解釋）"""
        warnings = []
        warning_explanations = []
        warning_count = 0
        
        # 檢查各項指標
        revenue_yoy = indicators.get('revenue_yoy')
        inventory_growth = indicators.get('inventory_growth')
        ar_growth = indicators.get('ar_growth')
        debt_ratio = indicators.get('debt_ratio')
        current_ratio = indicators.get('current_ratio')
        op_cf = indicators.get('operating_cashflow')
        margin_usage_rate = indicators.get('margin_usage_rate')
        day_trading_rate = indicators.get('day_trading_rate')
        
        # 營收應收比例落差
        if revenue_yoy is not None and ar_growth is not None:
            revenue_ar_gap = ar_growth - revenue_yoy
            if abs(revenue_ar_gap) > 30:
                warnings.append("營收與應收帳款成長差異過大")
                if revenue_ar_gap > 30:
                    explanation = f"營收成長{revenue_yoy:.1f}%，但應收帳款成長{ar_growth:.1f}%，應收帳款成長快很多，可能是客戶延遲付款或營收灌水。"
                else:
                    if ar_growth < 0:
                        explanation = f"營收成長{revenue_yoy:.1f}%，但應收帳款反而減少{abs(ar_growth):.1f}%。雖然看似收款變快，但落差太大需確認營收真實性。"
                    else:
                        explanation = f"營收成長{revenue_yoy:.1f}%，但應收帳款只成長{ar_growth:.1f}%，落差過大需注意營收品質。"
                warning_explanations.append({"warning": "營收與應收帳款成長差異過大", "explanation": explanation})
                warning_count += 1
        
        # 負債比率
        if debt_ratio is not None and debt_ratio > 50:
            warnings.append("負債比率過高")
            warning_explanations.append({
                "warning": "負債比率過高",
                "explanation": f"負債比率{debt_ratio:.1f}%，超過50%。公司資產有一半以上是借來的，負債太高會增加財務風險。"
            })
            warning_count += 1
        
        # 流動比率
        if current_ratio is not None and current_ratio < 1.0:
            warnings.append("流動比率低於1，短期償債能力不足")
            warning_explanations.append({
                "warning": "流動比率低於1，短期償債能力不足",
                "explanation": f"流動比率{current_ratio:.2f}，低於1.0。短期內要還的錢比手上可快速變現的資產還多，可能會周轉不靈。"
            })
            warning_count += 1
        
        # 營業現金流
        if op_cf is not None and op_cf < 0:
            warnings.append("營業現金流為負")
            warning_explanations.append({
                "warning": "營業現金流為負",
                "explanation": f"營業現金流為負值{op_cf:,.0f}。公司做生意不但沒賺到現金，還倒貼錢出去，長期這樣會出問題。"
            })
            warning_count += 1
        
        # 融資使用率
        if margin_usage_rate is not None and margin_usage_rate > 50:
            warnings.append("融資使用率過高")
            warning_count += 1
        
        # 融資賣壓
        margin_shares = indicators.get('margin_balance_shares')
        avg_10d_vol = indicators.get('avg_10day_volume')
        if margin_shares and avg_10d_vol:
            margin_vol_ratio = (margin_shares * 1000 / avg_10d_vol)
            if margin_vol_ratio > 0.3:
                warnings.append("融資餘額過高且成交量不足，可能形成賣壓")
                warning_explanations.append({
                    "warning": "融資餘額過高且成交量不足，可能形成賣壓",
                    "explanation": f"融資餘額是10日平均成交量的{margin_vol_ratio:.1f}倍。就像小河道裡太多船想出港，如果融資戶想賣出，可能造成股價大跌。"
                })
                warning_count += 1
        
        # 當沖率
        if day_trading_rate is not None and day_trading_rate > 30:
            warnings.append("當沖率過高")
            warning_count += 1
        
        # 計算檢查指標數
        indicator_checks = [revenue_yoy, inventory_growth, ar_growth, debt_ratio, current_ratio, op_cf, margin_usage_rate, day_trading_rate]
        total_indicators_checked = sum(1 for x in indicator_checks if x is not None)
        if margin_shares and avg_10d_vol:
            total_indicators_checked += 1
        
        # 風險等級
        warning_ratio = (warning_count / total_indicators_checked * 100) if total_indicators_checked > 0 else 0
        
        if warning_ratio >= 40:
            risk_level = "高風險"
        elif warning_ratio >= 20:
            risk_level = "中風險"
        else:
            risk_level = "低風險"
        
        return {
            'warnings': warnings,
            'warning_explanations': warning_explanations,
            'warning_count': warning_count,
            'total_indicators_checked': total_indicators_checked,
            'warning_ratio': round(warning_ratio, 1),
            'risk_level': risk_level
        }

# 創建分析器實例
analyzer = DarkIndicatorCalculator()

@app.route('/')
def home():
    """API 首頁"""
    return jsonify({
        "message": "暗黑指標分析 API",
        "version": "1.0",
        "endpoints": {
            "/analyze/<stock_code>": "分析指定股票的暗黑指標",
            "/health": "健康檢查"
        }
    })

@app.route('/analyze/<stock_code>')
def analyze_stock(stock_code):
    """分析指定股票"""
    if not stock_code or len(stock_code) < 4:
        return jsonify({"success": False, "error": "無效的股票代碼"}), 400
    
    result = analyzer.analyze_stock(stock_code)
    
    if result["success"]:
        return jsonify(result)
    else:
        return jsonify(result), 500

@app.route('/health')
def health_check():
    """健康檢查"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)