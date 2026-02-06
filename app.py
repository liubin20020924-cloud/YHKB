"""
主应用文件
"""
from flask import Flask, request
import config
import os
from database.db_utils import init_user_table
from auth.routes import auth_bp
from views.routes import views_bp
from management.routes import management_bp

def create_app():
    """创建Flask应用"""
    # 获取当前文件所在目录的绝对路径
    base_dir = os.path.abspath(os.path.dirname(__file__))
    template_dir = os.path.join(base_dir, 'templates')
    
    app = Flask(__name__, template_folder=template_dir)
    app.secret_key = config.SECRET_KEY
    
    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(management_bp)
    
    # 添加favicon路由以避免404错误
    @app.route('/favicon.ico')
    def favicon():
        """返回一个空的favicon避免404错误"""
        from flask import Response
        return Response('', mimetype='image/x-icon')
    
    # 首页重定向（如果需要）
    @app.route('/MGMT')
    def redirect_to_management():
        """重定向到管理页面 - 使用不同的端点名"""
        from flask import redirect, url_for
        return redirect(url_for('management.management'))
    
    # 初始化应用
    with app.app_context():
        print("初始化用户表...")
        init_user_table()
    
    # 添加Edge浏览器优化中间件
    @app.after_request
    def apply_caching(response):
        """为响应添加缓存控制和Edge优化头"""
        # 为静态资源添加缓存头
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=3600'
            response.headers['Expires'] = '3600'
        
        # Edge特定优化头
        user_agent = request.headers.get('User-Agent', '')
        if 'Edge' in user_agent or 'Trident' in user_agent:
            # 添加Edge兼容性头
            response.headers['X-UA-Compatible'] = 'IE=edge,chrome=1'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            
            # 禁用缓存以解决渲染问题（开发阶段）
            if config.DEBUG_MODE:
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
        
        return response
    
    return app

if __name__ == '__main__':
    app = create_app()

    # 生产环境应禁用debug模式
    app.run(debug=config.DEBUG_MODE, host=config.FLASK_HOST, port=config.FLASK_PORT)