"""
数据模型定义
"""
from datetime import datetime
from app import db
import secrets
import string


class Group(db.Model):
    """卡密分组"""
    __tablename__ = 'groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联
    cards = db.relationship('Card', backref='group', lazy='dynamic')
    redeem_codes = db.relationship('RedeemCode', backref='group', lazy='dynamic')
    
    @property
    def available_count(self):
        """可用卡密数量"""
        return self.cards.filter_by(status='available').count()
    
    @property
    def total_count(self):
        """总卡密数量"""
        return self.cards.count()
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'available_count': self.available_count,
            'total_count': self.total_count
        }


class Card(db.Model):
    """卡密（账号信息）"""
    __tablename__ = 'cards'
    
    id = db.Column(db.Integer, primary_key=True)
    account = db.Column(db.String(255), nullable=False)  # 账号
    password = db.Column(db.String(255), nullable=False)  # 密码
    totp_secret = db.Column(db.String(64))  # 2FA TOTP 密钥
    extra_info = db.Column(db.Text)  # 其他信息 (JSON格式)
    
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    status = db.Column(db.String(20), default='available')  # available, assigned
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_at = db.Column(db.DateTime)  # 分配给兑换码的时间
    redeem_code_id = db.Column(db.Integer, db.ForeignKey('redeem_codes.id'))
    
    def to_dict(self, include_sensitive=True):
        result = {
            'id': self.id,
            'group_id': self.group_id,
            'group_name': self.group.name if self.group else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None
        }
        if include_sensitive:
            result.update({
                'account': self.account,
                'password': self.password,
                'totp_secret': self.totp_secret,
                'extra_info': self.extra_info
            })
        return result


class RedeemCode(db.Model):
    """兑换码"""
    __tablename__ = 'redeem_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    status = db.Column(db.String(20), default='unused')  # unused, active (已绑定卡密)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    first_used_at = db.Column(db.DateTime)  # 首次查看时间
    last_used_at = db.Column(db.DateTime)   # 最近查看时间
    view_count = db.Column(db.Integer, default=0)  # 查看次数
    
    # 关联的卡密
    card = db.relationship('Card', backref='redeem_code', uselist=False)
    
    @staticmethod
    def generate_code(length=16):
        """生成随机兑换码"""
        alphabet = string.ascii_uppercase + string.digits
        # 移除容易混淆的字符
        alphabet = alphabet.replace('O', '').replace('0', '').replace('I', '').replace('1', '').replace('L', '')
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'group_id': self.group_id,
            'group_name': self.group.name if self.group else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'first_used_at': self.first_used_at.isoformat() if self.first_used_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'view_count': self.view_count
        }
