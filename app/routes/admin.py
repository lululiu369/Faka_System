"""
管理后台路由
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, session
from functools import wraps
from app import db
from app.models import Group, Card, RedeemCode
from datetime import datetime, timedelta
import json

admin_bp = Blueprint('admin', __name__, url_prefix='/console')


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """管理员登录"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == current_app.config.get('ADMIN_PASSWORD'):
            session['admin_logged_in'] = True
            return redirect(url_for('admin.dashboard'))
        else:
            flash('密码错误', 'error')
    
    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    """退出登录"""
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin.login'))


@admin_bp.route('/')
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """仪表盘"""
    # 统计数据
    stats = {
        'total_groups': Group.query.count(),
        'total_cards': Card.query.count(),
        'available_cards': Card.query.filter_by(status='available').count(),
        'assigned_cards': Card.query.filter_by(status='assigned').count(),
        'total_codes': RedeemCode.query.count(),
        'unused_codes': RedeemCode.query.filter_by(status='unused').count(),
        'active_codes': RedeemCode.query.filter_by(status='active').count(),
    }
    
    # 最近分配记录
    recent_redeems = Card.query.filter_by(status='assigned').order_by(
        Card.assigned_at.desc()
    ).limit(10).all()
    
    return render_template('admin/dashboard.html', stats=stats, recent_redeems=recent_redeems)


# ==================== 分组管理 ====================

@admin_bp.route('/groups')
@login_required
def groups():
    """分组列表"""
    groups = Group.query.order_by(Group.id.desc()).all()
    return render_template('admin/groups.html', groups=groups)


@admin_bp.route('/groups/add', methods=['POST'])
@login_required
def add_group():
    """添加分组"""
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name:
        flash('请输入分组名称', 'error')
        return redirect(url_for('admin.groups'))
    
    group = Group(name=name, description=description)
    db.session.add(group)
    db.session.commit()
    
    flash(f'分组 "{name}" 创建成功', 'success')
    return redirect(url_for('admin.groups'))


@admin_bp.route('/groups/<int:group_id>/delete', methods=['POST'])
@login_required
def delete_group(group_id):
    """删除分组"""
    group = Group.query.get_or_404(group_id)
    
    # 检查是否有关联数据
    if group.cards.count() > 0 or group.redeem_codes.count() > 0:
        flash('该分组下还有卡密或兑换码，无法删除', 'error')
        return redirect(url_for('admin.groups'))
    
    db.session.delete(group)
    db.session.commit()
    
    flash('分组已删除', 'success')
    return redirect(url_for('admin.groups'))


# ==================== 卡密管理 ====================

@admin_bp.route('/cards')
@login_required
def cards():
    """卡密列表"""
    group_id = request.args.get('group_id', type=int)
    status = request.args.get('status', '')
    
    query = Card.query
    
    if group_id:
        query = query.filter_by(group_id=group_id)
    if status:
        query = query.filter_by(status=status)
    
    cards = query.order_by(Card.id.desc()).all()
    groups = Group.query.all()
    
    return render_template('admin/cards.html', cards=cards, groups=groups,
                           current_group_id=group_id, current_status=status)


@admin_bp.route('/cards/add', methods=['POST'])
@login_required
def add_cards():
    """批量添加卡密"""
    group_id = request.form.get('group_id', type=int)
    cards_text = request.form.get('cards', '').strip()
    
    if not group_id:
        flash('请选择分组', 'error')
        return redirect(url_for('admin.cards'))
    
    if not cards_text:
        flash('请输入卡密信息', 'error')
        return redirect(url_for('admin.cards'))
    
    group = Group.query.get_or_404(group_id)
    
    # 解析卡密
    # 支持格式：
    # 1. 账号----密码
    # 2. 账号----密码----2FA密钥
    # 3. 账号----密码----2FA密钥----其他信息
    # 4. JSON 格式
    count = 0
    for line in cards_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        try:
            account = ''
            password = ''
            totp_secret = None
            extra = None
            
            # 尝试 JSON 格式
            if line.startswith('{'):
                data = json.loads(line)
                account = data.get('account', '')
                password = data.get('password', '')
                totp_secret = data.get('totp_secret', data.get('2fa', data.get('totp', '')))
                # 剩余字段作为 extra_info
                extra_data = {k: v for k, v in data.items() 
                             if k not in ('account', 'password', 'totp_secret', '2fa', 'totp')}
                if extra_data:
                    extra = json.dumps(extra_data, ensure_ascii=False)
            else:
                # 分隔符格式: 账号----密码----2FA密钥----其他
                parts = line.split('----')
                account = parts[0].strip() if len(parts) > 0 else ''
                password = parts[1].strip() if len(parts) > 1 else ''
                totp_secret = parts[2].strip() if len(parts) > 2 else None
                extra = '----'.join(parts[3:]).strip() if len(parts) > 3 else None
                
                # 清理空值
                if totp_secret == '':
                    totp_secret = None
                if extra == '':
                    extra = None
            
            if account and password:
                card = Card(
                    account=account,
                    password=password,
                    totp_secret=totp_secret,
                    extra_info=extra,
                    group_id=group_id
                )
                db.session.add(card)
                count += 1
        except Exception as e:
            continue
    
    db.session.commit()
    flash(f'成功添加 {count} 张卡密', 'success')
    return redirect(url_for('admin.cards', group_id=group_id))


@admin_bp.route('/cards/<int:card_id>/delete', methods=['POST'])
@login_required
def delete_card(card_id):
    """删除卡密"""
    card = Card.query.get_or_404(card_id)
    group_id = card.group_id
    
    db.session.delete(card)
    db.session.commit()
    
    flash('卡密已删除', 'success')
    return redirect(url_for('admin.cards', group_id=group_id))


# ==================== 兑换码管理 ====================

@admin_bp.route('/codes')
@login_required
def codes():
    """兑换码列表"""
    group_id = request.args.get('group_id', type=int)
    status = request.args.get('status', '')
    
    query = RedeemCode.query
    
    if group_id:
        query = query.filter_by(group_id=group_id)
    if status:
        query = query.filter_by(status=status)
    
    codes = query.order_by(RedeemCode.id.desc()).all()
    groups = Group.query.all()
    
    return render_template('admin/codes.html', codes=codes, groups=groups,
                           current_group_id=group_id, current_status=status)


@admin_bp.route('/codes/generate', methods=['POST'])
@login_required
def generate_codes():
    """批量生成兑换码"""
    group_id = request.form.get('group_id', type=int)
    count = request.form.get('count', 1, type=int)
    expires_days = request.form.get('expires_days', type=int)
    
    if not group_id:
        flash('请选择分组', 'error')
        return redirect(url_for('admin.codes'))
    
    if count < 1 or count > 1000:
        flash('生成数量应在 1-1000 之间', 'error')
        return redirect(url_for('admin.codes'))
    
    group = Group.query.get_or_404(group_id)
    
    expires_at = None
    if expires_days and expires_days > 0:
        expires_at = datetime.utcnow() + timedelta(days=expires_days)
    
    generated = []
    for _ in range(count):
        # 生成唯一兑换码
        while True:
            code = RedeemCode.generate_code()
            if not RedeemCode.query.filter_by(code=code).first():
                break
        
        redeem_code = RedeemCode(
            code=code,
            group_id=group_id,
            expires_at=expires_at
        )
        db.session.add(redeem_code)
        generated.append(code)
    
    db.session.commit()
    
    flash(f'成功生成 {count} 个兑换码', 'success')
    return redirect(url_for('admin.codes', group_id=group_id))


@admin_bp.route('/codes/<int:code_id>/delete', methods=['POST'])
@login_required
def delete_code(code_id):
    """删除兑换码"""
    code = RedeemCode.query.get_or_404(code_id)
    group_id = code.group_id
    
    db.session.delete(code)
    db.session.commit()
    
    flash('兑换码已删除', 'success')
    return redirect(url_for('admin.codes', group_id=group_id))


@admin_bp.route('/codes/export')
@login_required
def export_codes():
    """导出兑换码"""
    group_id = request.args.get('group_id', type=int)
    status = request.args.get('status', 'unused')
    
    query = RedeemCode.query.filter_by(status=status)
    if group_id:
        query = query.filter_by(group_id=group_id)
    
    codes = query.all()
    
    # 返回纯文本格式
    text = '\n'.join([c.code for c in codes])
    
    return text, 200, {
        'Content-Type': 'text/plain; charset=utf-8',
        'Content-Disposition': f'attachment; filename=codes_{status}.txt'
    }
