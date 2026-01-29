"""
兑换服务
核心业务逻辑：验证兑换码并发放/显示卡密
"""
from datetime import datetime
from app import db
from app.models import RedeemCode, Card
from app.utils.lock import redeem_lock


class RedeemError(Exception):
    """兑换错误"""
    pass


def redeem_card(code: str) -> dict:
    """
    使用兑换码获取卡密
    
    - 首次使用：分配一张卡密给该兑换码
    - 再次使用：显示已绑定的卡密，并增加查看次数
    
    Args:
        code: 兑换码
        
    Returns:
        dict: 包含账号信息的字典
        
    Raises:
        RedeemError: 兑换失败时抛出
    """
    code = code.strip().upper()
    
    if not code:
        raise RedeemError("请输入兑换码")
    
    # 使用分布式锁防止并发问题
    with redeem_lock(code):
        # 查找兑换码
        redeem_code = RedeemCode.query.filter_by(code=code).first()
        
        if not redeem_code:
            raise RedeemError("兑换码不存在")
        
        now = datetime.utcnow()
        
        # 检查是否已经绑定卡密
        if redeem_code.status == 'active' and redeem_code.card:
            # 已绑定，返回已有卡密，增加查看次数
            card = redeem_code.card
            redeem_code.view_count += 1
            redeem_code.last_used_at = now
            db.session.commit()
            
            return _build_result(card, redeem_code)
        
        # 首次使用，需要分配卡密
        card = Card.query.filter_by(
            group_id=redeem_code.group_id,
            status='available'
        ).first()
        
        if not card:
            raise RedeemError("库存不足，请联系客服")
        
        # 绑定卡密到兑换码
        card.status = 'assigned'
        card.assigned_at = now
        card.redeem_code_id = redeem_code.id
        
        redeem_code.status = 'active'
        redeem_code.first_used_at = now
        redeem_code.last_used_at = now
        redeem_code.view_count = 1
        
        db.session.commit()
        
        return _build_result(card, redeem_code)


def _build_result(card: Card, redeem_code: RedeemCode) -> dict:
    """构建返回结果"""
    return {
        'success': True,
        'account': card.account,
        'password': card.password,
        'totp_secret': card.totp_secret,
        'extra_info': card.extra_info,
        'group_name': card.group.name if card.group else None,
        'view_count': redeem_code.view_count,
        'first_used_at': redeem_code.first_used_at.isoformat() if redeem_code.first_used_at else None
    }
