"""
金融市场自动交易API模块
包含：市场调查、交易执行、交易记录、资产分析
"""

from flask import Blueprint, request, jsonify
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from functools import wraps
import random

logger = logging.getLogger(__name__)

# 创建蓝图
trading_bp = Blueprint('trading', __name__, url_prefix='/api')

DB_PATH = '/opt/kanban-react/backend/kanban_v5.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def generate_trade_number():
    """生成交易编号"""
    date_str = datetime.now().strftime('%Y%m%d')
    random_num = ''.join([str(random.randint(0, 9)) for _ in range(4)])
    return f"T{date_str}{random_num}"

# ============================================
# 市场调查 API
# ============================================

@trading_bp.route('/market/research', methods=['GET'])
def get_market_research():
    """获取市场调查研究"""
    try:
        research_type = request.args.get('type', 'daily')
        days = int(request.args.get('days', 7))
        
        conn = get_db()
        c = conn.cursor()
        
        # 获取最近的市场调研
        c.execute('''
            SELECT * FROM market_research 
            WHERE research_type = ? 
            AND research_date >= date('now', '-{} days')
            ORDER BY research_date DESC
        '''.format(days), (research_type,))
        
        researches = []
        for row in c.fetchall():
            research = dict(row)
            # 解析JSON字段
            for field in ['stock_analysis', 'fund_analysis', 'key_events', 
                         'opportunities', 'risks', 'recommendations']:
                if research.get(field):
                    try:
                        research[field] = json.loads(research[field])
                    except:
                        pass
            researches.append(research)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'researches': researches,
            'count': len(researches)
        })
    except Exception as e:
        logger.error(f"获取市场调查失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@trading_bp.route('/market/research', methods=['POST'])
def create_market_research():
    """创建市场调查研究"""
    try:
        data = request.get_json()
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO market_research 
            (research_date, research_type, market_overview, stock_analysis, 
             fund_analysis, gold_analysis, bond_analysis, key_events,
             opportunities, risks, recommendations, target_progress, ai_conclusion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('research_date', datetime.now().strftime('%Y-%m-%d')),
            data.get('research_type', 'daily'),
            data.get('market_overview', ''),
            json.dumps(data.get('stock_analysis', {})),
            json.dumps(data.get('fund_analysis', {})),
            data.get('gold_analysis', ''),
            data.get('bond_analysis', ''),
            json.dumps(data.get('key_events', [])),
            json.dumps(data.get('opportunities', [])),
            json.dumps(data.get('risks', [])),
            json.dumps(data.get('recommendations', [])),
            data.get('target_progress', 0),
            data.get('ai_conclusion', '')
        ))
        
        research_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'research_id': research_id,
            'message': '市场调查创建成功'
        })
    except Exception as e:
        logger.error(f"创建市场调查失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@trading_bp.route('/market/research/latest', methods=['GET'])
def get_latest_market_research():
    """获取最新市场调查研究"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            SELECT * FROM market_research 
            ORDER BY research_date DESC, created_at DESC
            LIMIT 1
        ''')
        
        row = c.fetchone()
        conn.close()
        
        if not row:
            return jsonify({
                'success': True,
                'research': None,
                'message': '暂无市场调查数据'
            })
        
        research = dict(row)
        # 解析JSON字段
        for field in ['stock_analysis', 'fund_analysis', 'key_events', 
                     'opportunities', 'risks', 'recommendations']:
            if research.get(field):
                try:
                    research[field] = json.loads(research[field])
                except:
                    pass
        
        return jsonify({
            'success': True,
            'research': research
        })
    except Exception as e:
        logger.error(f"获取最新市场调查失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 交易执行 API
# ============================================

@trading_bp.route('/trading/execute', methods=['POST'])
def execute_trade():
    """执行交易"""
    try:
        data = request.get_json()
        
        # 验证必要字段
        required_fields = ['asset_id', 'trade_type', 'quantity', 'price']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'缺少必要字段: {field}'}), 400
        
        asset_id = data['asset_id']
        trade_type = data['trade_type']  # buy, sell
        quantity = float(data['quantity'])
        price = float(data['price'])
        
        conn = get_db()
        c = conn.cursor()
        
        # 获取资产信息
        c.execute('SELECT * FROM stocks WHERE id = ?', (asset_id,))
        asset = c.fetchone()
        
        if not asset:
            conn.close()
            return jsonify({'success': False, 'error': '资产不存在'}), 404
        
        asset = dict(asset)
        
        # 计算交易金额和费用
        total_amount = quantity * price
        fee = data.get('fee', total_amount * 0.0003)  # 默认万3手续费
        tax = data.get('tax', 0)
        
        if trade_type == 'sell':
            tax = total_amount * 0.001  # 卖出印花税千1
        
        net_amount = total_amount - fee - tax
        
        # 生成交易编号
        record_number = generate_trade_number()
        
        # 创建交易记录
        c.execute('''
            INSERT INTO trading_records 
            (record_number, asset_id, asset_symbol, asset_name, asset_type,
             trade_type, trade_strategy, quantity, price, total_amount,
             fee, tax, net_amount, trade_date, status, executed_by,
             trigger_condition, market_source, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record_number,
            asset_id,
            asset['symbol'],
            asset['name'],
            asset.get('asset_type', 'stock'),
            trade_type,
            data.get('trade_strategy', ''),
            quantity,
            price,
            total_amount,
            fee,
            tax,
            net_amount,
            data.get('trade_date', datetime.now().isoformat()),
            data.get('status', 'completed'),
            data.get('executed_by', 'manual'),
            data.get('trigger_condition', ''),
            data.get('market_source', ''),
            data.get('notes', '')
        ))
        
        record_id = c.lastrowid
        
        # 更新持仓
        if trade_type == 'buy':
            # 买入 - 增加持仓
            new_shares = (asset.get('shares') or 0) + quantity
            # 计算新的平均成本
            old_cost = (asset.get('shares') or 0) * (asset.get('avg_cost') or 0)
            new_cost = old_cost + total_amount
            new_avg_cost = new_cost / new_shares if new_shares > 0 else 0
            
            c.execute('''
                UPDATE stocks 
                SET shares = ?, avg_cost = ?, asset_value = ? * current_price,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_shares, new_avg_cost, new_shares, asset_id))
            
        elif trade_type == 'sell':
            # 卖出 - 减少持仓
            new_shares = (asset.get('shares') or 0) - quantity
            if new_shares < 0:
                conn.rollback()
                conn.close()
                return jsonify({'success': False, 'error': '卖出数量超过持仓'}), 400
            
            c.execute('''
                UPDATE stocks 
                SET shares = ?, asset_value = ? * current_price,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_shares, new_shares, asset_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'record_id': record_id,
            'record_number': record_number,
            'message': f'{"买入" if trade_type == "buy" else "卖出"}交易执行成功',
            'trade_summary': {
                'asset_name': asset['name'],
                'quantity': quantity,
                'price': price,
                'total_amount': total_amount,
                'fee': fee,
                'tax': tax,
                'net_amount': net_amount
            }
        })
    except Exception as e:
        logger.error(f"执行交易失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@trading_bp.route('/trading/auto-evaluate', methods=['POST'])
def auto_trade_evaluate():
    """自动交易评估 - AI评估是否执行交易"""
    try:
        data = request.get_json()
        
        conn = get_db()
        c = conn.cursor()
        
        # 获取所有启用了自动交易的资产
        c.execute('''
            SELECT * FROM stocks 
            WHERE is_auto_trade = 1 AND shares > 0
        ''')
        
        assets = [dict(row) for row in c.fetchall()]
        
        # 获取自动交易配置
        c.execute('SELECT * FROM auto_trade_config WHERE is_active = 1 LIMIT 1')
        config = c.fetchone()
        config = dict(config) if config else None
        
        conn.close()
        
        # 模拟AI评估结果
        evaluations = []
        for asset in assets:
            # 简单示例：如果收益率超过15%，建议卖出
            return_rate = ((asset.get('current_price', 0) - asset.get('avg_cost', 0)) 
                          / asset.get('avg_cost', 1) * 100) if asset.get('avg_cost', 0) > 0 else 0
            
            evaluation = {
                'asset_id': asset['id'],
                'asset_name': asset['name'],
                'symbol': asset['symbol'],
                'current_price': asset.get('current_price', 0),
                'avg_cost': asset.get('avg_cost', 0),
                'return_rate': return_rate,
                'shares': asset.get('shares', 0),
                'market_value': asset.get('shares', 0) * asset.get('current_price', 0),
                'recommendation': 'hold',
                'confidence': 0.7,
                'reason': '持有观望'
            }
            
            if return_rate > 15:
                evaluation['recommendation'] = 'sell'
                evaluation['reason'] = '收益率超过15%，建议止盈'
                evaluation['suggested_quantity'] = asset.get('shares', 0) * 0.3  # 建议卖出30%
            elif return_rate < -8:
                evaluation['recommendation'] = 'buy'
                evaluation['reason'] = '跌幅超过8%，建议逢低加仓'
                evaluation['suggested_quantity'] = 100  # 建议买入数量
            
            evaluations.append(evaluation)
        
        return jsonify({
            'success': True,
            'evaluations': evaluations,
            'total_assets': len(assets),
            'config': config,
            'target_amount': config.get('target_amount', 4000000) if config else 4000000,
            'target_date': config.get('target_date', '2026-12-31') if config else '2026-12-31'
        })
    except Exception as e:
        logger.error(f"自动交易评估失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 交易记录 API
# ============================================

@trading_bp.route('/trading/history', methods=['GET'])
def get_trading_history():
    """获取交易记录历史"""
    try:
        asset_id = request.args.get('asset_id')
        trade_type = request.args.get('trade_type')
        days = int(request.args.get('days', 90))
        limit = int(request.args.get('limit', 100))
        
        conn = get_db()
        c = conn.cursor()
        
        query = '''
            SELECT * FROM trading_records 
            WHERE trade_date >= date('now', '-{} days')
        '''.format(days)
        params = []
        
        if asset_id:
            query += ' AND asset_id = ?'
            params.append(asset_id)
        
        if trade_type:
            query += ' AND trade_type = ?'
            params.append(trade_type)
        
        query += ' ORDER BY trade_date DESC LIMIT ?'
        params.append(limit)
        
        c.execute(query, params)
        
        records = [dict(row) for row in c.fetchall()]
        
        # 获取统计
        c.execute('''
            SELECT 
                COUNT(*) as total_count,
                SUM(CASE WHEN trade_type = 'buy' THEN total_amount ELSE 0 END) as total_buy,
                SUM(CASE WHEN trade_type = 'sell' THEN total_amount ELSE 0 END) as total_sell,
                SUM(fee) as total_fee,
                SUM(tax) as total_tax
            FROM trading_records 
            WHERE trade_date >= date('now', '-{} days')
        '''.format(days))
        
        stats = dict(c.fetchone())
        
        conn.close()
        
        return jsonify({
            'success': True,
            'records': records,
            'stats': stats,
            'count': len(records)
        })
    except Exception as e:
        logger.error(f"获取交易记录失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@trading_bp.route('/trading/record/<int:record_id>', methods=['GET'])
def get_trade_record(record_id):
    """获取单条交易记录详情"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('SELECT * FROM trading_records WHERE id = ?', (record_id,))
        record = c.fetchone()
        conn.close()
        
        if not record:
            return jsonify({'success': False, 'error': '交易记录不存在'}), 404
        
        return jsonify({
            'success': True,
            'record': dict(record)
        })
    except Exception as e:
        logger.error(f"获取交易记录详情失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 资产分析 API
# ============================================

@trading_bp.route('/assets/analysis', methods=['GET'])
def get_assets_analysis():
    """获取资产分析"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 获取当前资产统计
        c.execute('''
            SELECT 
                COUNT(*) as asset_count,
                SUM(shares * avg_cost) as total_cost,
                SUM(shares * current_price) as total_value,
                SUM(shares * (current_price - avg_cost)) as total_profit,
                AVG(CASE WHEN avg_cost > 0 
                    THEN (current_price - avg_cost) / avg_cost * 100 
                    ELSE 0 END) as avg_return,
                asset_type
            FROM stocks
            WHERE shares > 0
            GROUP BY asset_type
        ''')
        
        asset_types = [dict(row) for row in c.fetchall()]
        
        # 总体统计
        c.execute('''
            SELECT 
                COUNT(*) as total_assets,
                SUM(shares * avg_cost) as total_cost,
                SUM(shares * current_price) as total_value,
                SUM(shares * (current_price - avg_cost)) as total_profit
            FROM stocks
            WHERE shares > 0
        ''')
        
        total_stats = dict(c.fetchone())
        total_cost = total_stats.get('total_cost') or 0
        total_value = total_stats.get('total_value') or 0
        total_profit = total_value - total_cost
        total_return = (total_profit / total_cost * 100) if total_cost > 0 else 0
        
        # 获取目标配置
        c.execute('SELECT * FROM auto_trade_config WHERE is_active = 1 LIMIT 1')
        config = c.fetchone()
        target_amount = dict(config).get('target_amount', 4000000) if config else 4000000
        
        # 计算距离目标的差距
        target_distance = target_amount - total_value
        target_progress = (total_value / target_amount * 100) if target_amount > 0 else 0
        
        # 获取历史分析数据（最近30天）
        c.execute('''
            SELECT * FROM asset_analysis 
            ORDER BY analysis_date DESC
            LIMIT 30
        ''')
        
        history = [dict(row) for row in c.fetchall()]
        
        # 获取交易历史
        c.execute('''
            SELECT 
                DATE(trade_date) as date,
                SUM(CASE WHEN trade_type = 'buy' THEN net_amount ELSE 0 END) as buy_amount,
                SUM(CASE WHEN trade_type = 'sell' THEN net_amount ELSE 0 END) as sell_amount,
                COUNT(*) as trade_count
            FROM trading_records
            WHERE trade_date >= date('now', '-30 days')
            GROUP BY DATE(trade_date)
            ORDER BY date
        ''')
        
        trade_history = [dict(row) for row in c.fetchall()]
        
        conn.close()
        
        # 资产配置分析
        allocation = []
        for at in asset_types:
            value = at.get('total_value') or 0
            allocation.append({
                'asset_type': at.get('asset_type', 'unknown'),
                'value': value,
                'percentage': (value / total_value * 100) if total_value > 0 else 0,
                'count': at.get('asset_count', 0)
            })
        
        return jsonify({
            'success': True,
            'summary': {
                'total_assets': total_stats.get('total_assets', 0),
                'total_cost': total_cost,
                'total_value': total_value,
                'total_profit': total_profit,
                'total_return': total_return,
                'target_amount': target_amount,
                'target_distance': target_distance,
                'target_progress': target_progress,
                'days_to_year_end': (datetime(2026, 12, 31) - datetime.now()).days
            },
            'allocation': allocation,
            'asset_types': asset_types,
            'history': history,
            'trade_history': trade_history
        })
    except Exception as e:
        logger.error(f"获取资产分析失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@trading_bp.route('/assets/analysis/save', methods=['POST'])
def save_asset_analysis():
    """保存资产分析"""
    try:
        data = request.get_json()
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO asset_analysis 
            (analysis_date, total_value, total_cost, total_profit, total_return,
             asset_allocation, risk_level, sharpe_ratio, max_drawdown, volatility,
             analysis_result, suggestions, target_distance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('analysis_date', datetime.now().strftime('%Y-%m-%d')),
            data.get('total_value', 0),
            data.get('total_cost', 0),
            data.get('total_profit', 0),
            data.get('total_return', 0),
            json.dumps(data.get('asset_allocation', {})),
            data.get('risk_level', 'medium'),
            data.get('sharpe_ratio', 0),
            data.get('max_drawdown', 0),
            data.get('volatility', 0),
            data.get('analysis_result', ''),
            data.get('suggestions', ''),
            data.get('target_distance', 0)
        ))
        
        analysis_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'analysis_id': analysis_id,
            'message': '资产分析保存成功'
        })
    except Exception as e:
        logger.error(f"保存资产分析失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@trading_bp.route('/assets/timeline', methods=['GET'])
def get_assets_timeline():
    """获取资产时间线数据（用于图表）"""
    try:
        days = int(request.args.get('days', 90))
        
        conn = get_db()
        c = conn.cursor()
        
        # 生成日期序列和模拟数据
        # 实际应用中，这里应该查询历史数据表
        c.execute('''
            SELECT 
                DATE(created_at) as date,
                AVG(total_value) as avg_value
            FROM asset_analysis
            WHERE analysis_date >= date('now', '-{} days')
            GROUP BY DATE(created_at)
            ORDER BY date
        '''.format(days))
        
        timeline = [dict(row) for row in c.fetchall()]
        
        # 如果没有历史数据，生成基于当前值的模拟数据
        if not timeline:
            c.execute('SELECT SUM(shares * current_price) FROM stocks WHERE shares > 0')
            current_value = c.fetchone()[0] or 0
            
            # 生成最近N天的数据（模拟）
            timeline = []
            for i in range(days, 0, -1):
                date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                # 模拟波动
                variation = random.uniform(-0.02, 0.02)
                value = current_value * (1 + variation * (days - i) / days)
                timeline.append({
                    'date': date,
                    'value': round(value, 2)
                })
            
            # 最后一天使用真实当前值
            if timeline:
                timeline[-1]['value'] = round(current_value, 2)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'timeline': timeline,
            'days': len(timeline)
        })
    except Exception as e:
        logger.error(f"获取资产时间线失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 自动交易配置 API
# ============================================

@trading_bp.route('/trading/config', methods=['GET'])
def get_trading_config():
    """获取自动交易配置"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('SELECT * FROM auto_trade_config ORDER BY id DESC LIMIT 1')
        config = c.fetchone()
        conn.close()
        
        if not config:
            return jsonify({
                'success': True,
                'config': None,
                'message': '使用默认配置'
            })
        
        config_dict = dict(config)
        if config_dict.get('strategy_params'):
            try:
                config_dict['strategy_params'] = json.loads(config_dict['strategy_params'])
            except:
                pass
        
        return jsonify({
            'success': True,
            'config': config_dict
        })
    except Exception as e:
        logger.error(f"获取交易配置失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@trading_bp.route('/trading/config', methods=['POST'])
def update_trading_config():
    """更新自动交易配置"""
    try:
        data = request.get_json()
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            INSERT OR REPLACE INTO auto_trade_config 
            (id, config_name, strategy_type, target_amount, target_date,
             risk_tolerance, max_position_size, stop_loss_percent, take_profit_percent,
             rebalance_frequency, is_active, strategy_params, updated_at)
            VALUES (
                (SELECT id FROM auto_trade_config ORDER BY id DESC LIMIT 1),
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
            )
        ''', (
            data.get('config_name', '默认配置'),
            data.get('strategy_type', 'balanced'),
            data.get('target_amount', 4000000),
            data.get('target_date', '2026-12-31'),
            data.get('risk_tolerance', 'moderate'),
            data.get('max_position_size', 0.8),
            data.get('stop_loss_percent', 0.08),
            data.get('take_profit_percent', 0.15),
            data.get('rebalance_frequency', 'weekly'),
            data.get('is_active', 1),
            json.dumps(data.get('strategy_params', {}))
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '交易配置更新成功'
        })
    except Exception as e:
        logger.error(f"更新交易配置失败: {e}")
        return jsonify({'success': False, 'error': str(e)})
