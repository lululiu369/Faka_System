"""
兑换相关路由（公开接口）
"""
from flask import Blueprint, render_template, request, jsonify
from app.services.redeem_service import redeem_card, RedeemError

redeem_bp = Blueprint('redeem', __name__)


@redeem_bp.route('/')
def index():
    """兑换页面"""
    return render_template('public/redeem.html')


@redeem_bp.route('/api/redeem', methods=['POST'])
def api_redeem():
    """
    兑换接口
    
    Request JSON:
        code: 兑换码
        
    Response JSON:
        success: bool
        data: 卡密信息 (成功时)
        error: 错误信息 (失败时)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求'}), 400
        
        code = data.get('code', '')
        result = redeem_card(code)
        
        return jsonify(result)
        
    except RedeemError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': '系统错误，请稍后重试'}), 500
