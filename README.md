# 配置说明

本系统支持通过修改 `config.py` 文件来适应不同的服务器环境。

## 核心配置项

### 数据库配置
```python
DB_HOST = '10.10.10.254'   # 数据库主机地址
DB_PORT = 3306                  # 数据库端口
DB_USER = 'root'               # 数据库用户名
DB_PASSWORD = 'Nutanix/4u123!'   # 数据库密码
DB_NAME = 'YHKB'               # 数据库名
```

### Flask服务器配置
```python
FLASK_HOST = '0.0.0.0'  # 监听地址，0.0.0.0表示所有网卡
FLASK_PORT = 5000           # 服务端口
FLASK_DEBUG = False          # 调试模式（生产环境建议False）
```

### Trilium服务器配置
```python
TRILIUM_SERVER_URL = 'http://10.10.10.254:8080'  # Trilium服务器完整URL
TRILIUM_BASE_URL = 'http://10.10.10.254:8080'    # Trilium基础URL
TRILIUM_SERVER_HOST = '10.10.10.254:8080'       # Trilium主机地址（用于验证）
TRILIUM_TOKEN = 'geJWc61h07w7_OSwK2FqHZ4PaV3F8K8iCx/Rus2EaIJn1uyNyrRM6zOk='  # API令牌
```

### Trilium登录配置
```python
TRILIUM_LOGIN_USERNAME = ''       # Trilium用户名（如果需要登录）
TRILIUM_LOGIN_PASSWORD = 'Nutanix/4u123!'  # Trilium密码
```

### 安全配置
```python
SECRET_KEY = 'YHKB-MGMT-SECRET-KEY-2024-CHANGE-ME'  # Session加密密钥（生产环境必须修改）
SESSION_TIMEOUT = 180                                   # Session超时时间（秒）
```

### 功能开关
```python
ENABLE_CONTENT_VIEW = True    # 是否启用内容查看功能
ENABLE_IMAGE_PROXY = True    # 是否启用图片代理
DEBUG_MODE = False          # 调试模式
```

## 部署时需要修改的配置

### 1. 更改数据库服务器
将 `DB_HOST` 修改为实际的MySQL服务器地址

### 2. 更改Flask服务端口
如果5000端口被占用，修改 `FLASK_PORT` 为其他端口

### 3. 更改Trilium服务器地址
将 `TRILIUM_SERVER_URL`、`TRILIUM_BASE_URL`、`TRILIUM_SERVER_HOST` 修改为实际的Trilium服务器地址

### 4. 修改安全密钥
生产环境必须修改 `SECRET_KEY` 为一个随机字符串，建议使用命令生成：
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. 修改默认管理员密码
首次运行后，建议立即修改 `DEFAULT_ADMIN_PASSWORD` 或登录后修改密码

## 不同服务器环境的配置示例

### 开发环境（localhost）
```python
DB_HOST = 'localhost'
TRILIUM_SERVER_URL = 'http://localhost:8080'
TRILIUM_BASE_URL = 'http://localhost:8080'
TRILIUM_SERVER_HOST = 'localhost:8080'
FLASK_DEBUG = True
```

### 测试环境
```python
DB_HOST = '192.168.1.100'
TRILIUM_SERVER_URL = 'http://192.168.1.100:8080'
TRILIUM_BASE_URL = 'http://192.168.1.100:8080'
TRILIUM_SERVER_HOST = '192.168.1.100:8080'
FLASK_DEBUG = True
```

### 生产环境
```python
DB_HOST = 'your-database-server.com'
TRILIUM_SERVER_URL = 'http://your-trilium-server.com:8080'
TRILIUM_BASE_URL = 'http://your-trilium-server.com:8080'
TRILIUM_SERVER_HOST = 'your-trilium-server.com:8080'
FLASK_DEBUG = False
SECRET_KEY = '生成的随机密钥'
```

## 注意事项

1. **修改配置后需要重启服务**
2. **数据库密码和Trilium密码请妥善保管**
3. **生产环境务必修改SECRET_KEY**
4. **TRILIUM_TOKEN在Trilium设置中生成，路径：设置 -> 高级 -> API令牌**
5. **启用图片代理功能需要在Trilium服务器可访问的情况下使用**

## 常见问题

### Q: 修改配置后不生效？
A: 需要重启Flask服务

### Q: 数据库连接失败？
A: 检查数据库地址、端口、用户名、密码是否正确

### Q: Trilium内容无法查看？
A: 检查TRILIUM_SERVER_URL、TRILIUM_TOKEN是否正确

### Q: 如何获取TRILIUM_TOKEN？
A: 在Trilium中：设置 -> 高级 -> API令牌 -> 生成新令牌
