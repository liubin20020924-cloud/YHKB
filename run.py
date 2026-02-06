"""
运行文件 - 用于生产环境
"""
from app import create_app
import config

app = create_app()

if __name__ == '__main__':
    print("启动YHKB知识库管理系统...")
    print(f"访问 http://{config.FLASK_HOST}:{config.FLASK_PORT}")
    print(f"登录页面 http://{config.FLASK_HOST}:{config.FLASK_PORT}/auth/login")
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.FLASK_DEBUG)