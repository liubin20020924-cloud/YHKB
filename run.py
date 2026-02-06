"""
运行文件 - 用于生产环境
"""
from app import create_app

app = create_app()

if __name__ == '__main__':
    print("启动YHKB知识库管理系统...")
    print("访问 http://localhost:5000")
    print("登录页面 http://localhost:5000/auth/login")
    app.run(host='0.0.0.0', port=5000, debug=False)