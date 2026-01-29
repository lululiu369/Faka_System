# Project Nexus - 卡密兑换系统

一个轻量级的卡密兑换系统，用户通过兑换码即可获取账号密码等信息。

## 功能特点

- 🔑 **兑换码机制**: 一码一用，支持有效期设置
- 💳 **卡密管理**: 批量导入账号密码，支持多种格式
- 📁 **分组管理**: 支持多产品分组（如：标准版、高级版）
- 🔒 **并发安全**: Redis 分布式锁，防止一码多用
- 🎨 **现代界面**: 暗色主题，响应式设计

## 快速开始

### 本地开发

1. 安装依赖:
```bash
pip install -r requirements.txt
```

2. 配置环境变量:
```bash
cp .env.example .env
# 编辑 .env 修改管理员密码
```

3. 运行应用:
```bash
python run.py
```

4. 访问:
- 兑换页面: http://localhost:5000/
- 管理后台: http://localhost:5000/admin/

### Docker 部署

1. 启动服务:
```bash
docker-compose up -d
```

2. 访问:
- 兑换页面: http://你的服务器IP:8080/
- 管理后台: http://你的服务器IP:8080/admin/

## 使用说明

### 管理员操作流程

1. 登录后台 → 创建分组（如"Netflix标准账号"）
2. 添加卡密（支持批量粘贴）
3. 生成兑换码
4. 将兑换码发给客户

### 卡密格式

支持以下格式，每行一个：

```
# 格式1: 账号----密码
user@example.com----password123

# 格式2: 账号----密码----其他信息
user@example.com----password123----辅助邮箱: backup@email.com

# 格式3: JSON 格式
{"account":"user@example.com","password":"pass123","email":"backup@email.com","2fa":"ABCD1234"}
```

### 客户操作流程

1. 访问兑换页面
2. 输入兑换码
3. 查看并复制账号信息

## 配置说明

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| SECRET_KEY | Flask 密钥 | dev-secret-key |
| ADMIN_PASSWORD | 管理员密码 | admin123 |
| REDIS_URL | Redis 连接地址 | redis://localhost:6379/0 |
| DATABASE_URL | 数据库连接 | sqlite:///data/nexus.db |

## 技术栈

- **后端**: Flask + SQLAlchemy
- **数据库**: SQLite (轻量) / 可换 MySQL
- **缓存**: Redis (并发锁)
- **部署**: Docker Compose

## 生产部署建议

1. 修改 `SECRET_KEY` 为随机字符串
2. 修改 `ADMIN_PASSWORD` 为强密码
3. 配置 Nginx 反向代理
4. 启用 HTTPS

## License

MIT
