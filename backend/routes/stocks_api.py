"""Routes: stocks_api - 股票 API"""
from flask import Blueprint, jsonify, request
from routes.helpers import get_db, row_to_dict
from datetime import timedelta
import os
import json
from datetime import datetime

bp = Blueprint("routes_stocks_api", __name__)
logger = __import__("logging").getLogger(__name__)

@bp.route('/api/stocks', methods=['GET'])
def get_stocks():
    """获取所有股票"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, symbol as code, name, market as type, shares, 
                   avg_cost as cost_price, current_price,
                   (shares * current_price) as market_value,
                   CASE WHEN avg_cost > 0 
                        THEN ((current_price - avg_cost) / avg_cost * 100) 
                        ELSE 0 END as return_rate
            FROM stocks
            ORDER BY market, symbol
        ''')
        stocks = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'stocks': stocks})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/stock-fund-links', methods=['GET'])
def get_stock_fund_links():
    """获取股票基金关联"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT * FROM stock_fund_links
            ORDER BY correlation DESC
        ''')
        links = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'links': links})
    except Exception as e:
        return jsonify({'success': True, 'links': []})

@bp.route('/api/stocks/<symbol>', methods=['GET'])
def get_stock_detail(symbol):
    """获取股票详情"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM stocks WHERE symbol = %s', (symbol,))
        stock = c.fetchone()
    
        # 获取历史价格（使用total_value代替close_price）
        c.execute('''
            SELECT date, total_value as value FROM stock_history
            ORDER BY date DESC
            LIMIT 30
        ''')
        history = [row_to_dict(row, c) for row in c.fetchall()]
    
        conn.close()
    
        if stock:
            return jsonify({
                'success': True,
                'stock': dict(stock),
                'history': history
            })
        return jsonify({'success': False, 'error': '股票不存在'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/stocks/stats', methods=['GET'])
def get_stock_stats():
    """获取股票统计"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        c.execute('SELECT SUM(shares * avg_cost) FROM stocks')
        total_cost = list(c.fetchone().values())[0] or 0
    
        c.execute('SELECT SUM(shares * current_price) FROM stocks')
        total_value = list(c.fetchone().values())[0] or 0
    
        total_profit = total_value - total_cost
        total_return = (total_profit / total_cost * 100) if total_cost > 0 else 0
    
        conn.close()
    
        return jsonify({
            'success': True,
            'total_value': total_value,
            'total_cost': total_cost,
            'total_profit': total_profit,
            'total_return': total_return
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/stocks/portfolio', methods=['GET'])
def get_stock_portfolio():
    """获取投资组合（兼容前端调用）"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        # 获取持仓列表
        c.execute('''
            SELECT id, symbol, name, market, shares, 
                   avg_cost, current_price,
                   (shares * current_price) as market_value,
                   ((current_price - avg_cost) * shares) as profit_loss
            FROM stocks
            WHERE shares > 0
            ORDER BY market, symbol
        ''')
        holdings = [row_to_dict(row, c) for row in c.fetchall()]
    
        # 计算统计
        c.execute('SELECT SUM(shares * avg_cost) FROM stocks')
        total_cost = list(c.fetchone().values())[0] or 0
    
        c.execute('SELECT SUM(shares * current_price) FROM stocks')
        total_value = list(c.fetchone().values())[0] or 0
    
        total_profit = total_value - total_cost
        total_return = (total_profit / total_cost * 100) if total_cost > 0 else 0
    
        conn.close()
    
        return jsonify({
            'success': True,
            'holdings': holdings,
            'summary': {
                'total_value': total_value,
                'total_cost': total_cost,
                'total_profit': total_profit,
                'total_return': total_return,
                'holdings_count': len(holdings)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

