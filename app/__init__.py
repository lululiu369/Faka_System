"""
Project Nexus - 卡密兑换系统
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import redis
import os

db = SQLAlchemy()
login_manager = LoginManager()
redis_client = None


def create_app():
    """创建并配置 Flask 应用"""
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    # 加载配置
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', 'admin123')
    
    # 数据库配置
    db_url = os.environ.get('DATABASE_URL', 'sqlite:///data/nexus.db')
    if db_url.startswith('sqlite:///') and not db_url.startswith('sqlite:////'):
        # 相对路径转绝对路径
        db_path = db_url.replace('sqlite:///', '')
        db_dir = os.path.dirname(os.path.abspath(db_path))
        os.makedirs(db_dir, exist_ok=True)
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.abspath(db_path)}'
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'admin.login'
    
    # 由于我们使用简单的 session 认证，不需要真正的用户模型
    # 但 Flask-Login 需要 user_loader，所以添加一个简单的回调
    @login_manager.user_loader
    def load_user(user_id):
        return None  # 我们不使用 Flask-Login 的用户管理，只用 session
    
    # 初始化 Redis
    global redis_client
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    try:
        redis_client = redis.from_url(redis_url, decode_responses=True)
        redis_client.ping()
    except Exception as e:
        print(f"Warning: Redis connection failed: {e}")
        print("Running without Redis - concurrent lock disabled")
        redis_client = None
    
    # 注册蓝图
    from app.routes.admin import admin_bp
    from app.routes.redeem import redeem_bp
    
    app.register_blueprint(admin_bp)
    app.register_blueprint(redeem_bp)
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
    
    return app
