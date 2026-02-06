# 数据库配置
DB_HOST = '10.10.10.254'   # 数据库主机地址
DB_PORT = 3306         # 数据库端口
DB_USER = 'root'  # 数据库用户名
DB_PASSWORD = 'Nutanix/4u123!'  # 数据库密码
DB_NAME = 'YHKB'  # 数据库名

# Flask服务器配置
FLASK_HOST = '0.0.0.0'  # Flask监听地址，0.0.0.0表示监听所有网卡
FLASK_PORT = 5000  # Flask服务端口
FLASK_DEBUG = False  # Flask调试模式

# 登录配置
SECRET_KEY = 'YHKB-MGMT-SECRET-KEY-2024-CHANGE-ME'  # 用于session加密，请在生产环境修改
SESSION_TIMEOUT = 60 * 3  # Session超时时间（秒），1小时

# 默认管理员账号（首次运行时会创建）
DEFAULT_ADMIN_USERNAME = 'admin'
DEFAULT_ADMIN_PASSWORD = 'YHKB@2024'  # 建议首次登录后修改

# 调试配置
DEBUG_MODE = False  # 默认关闭调试模式
DEBUG_ADMIN_ONLY = True  # 调试功能仅管理员可访问
TRILIUM_SERVER_URL = 'http://10.10.10.254:8080'  # Trilium服务器地址
TRILIUM_TOKEN = 'geJWc61h07w7_OSwK2FqHZ4PaV3F8K8iCx/Rus2EaIJn1uyNyrRM6zOk='  # Trilium API令牌（在Trilium设置中生成）

# 内容查看配置
ENABLE_CONTENT_VIEW = True  # 是否启用内容查看功能
CONTENT_CACHE_TIMEOUT = 300  # 内容缓存时间（秒）

# HTML 内容安全配置
ALLOWED_HTML_TAGS = [
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'p', 'br', 'div', 'span',
    'strong', 'b', 'em', 'i', 'u', 's',
    'ul', 'ol', 'li',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'a', 'img',
    'pre', 'code',
    'blockquote', 'hr'
]

ALLOWED_HTML_ATTRIBUTES = {
    '*': ['class', 'style', 'id'],
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'table': ['border', 'cellpadding', 'cellspacing', 'width'],
}

# 图片处理配置
TRILIUM_BASE_URL = 'http://10.10.10.254:8080'  # Trilium 基础URL
ENABLE_IMAGE_PROXY = True  # 是否启用图片代理
TRILIUM_SERVER_HOST = '10.10.10.254:8080'  # Trilium服务器主机地址（用于URL验证）

# 在config.py末尾添加

# Trilium登录配置
TRILIUM_LOGIN_USERNAME = ''  # 修改为您的Trilium用户名
TRILIUM_LOGIN_PASSWORD = 'Nutanix/4u123!'  # 修改为您的Trilium密码

# 注意：如果Trilium使用匿名访问，可以留空
# TRILIUM_LOGIN_USERNAME = ''
# TRILIUM_LOGIN_PASSWORD = ''
# 浏览器优化配置
ENABLE_EDGE_OPTIMIZATION = True  # 启用Edge优化
EDGE_COMPATIBILITY_MODE = True   # Edge兼容模式
CACHE_CONTROL_HEADERS = True     # 启用缓存控制

# 静态文件缓存
STATIC_CACHE_TIME = 3600  # 静态文件缓存1小时

