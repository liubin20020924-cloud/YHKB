"""
认证工具模块
包含用户认证和授权相关函数
"""
from werkzeug.security import check_password_hash
from flask import session, request
from database.db_utils import get_db_connection

def authenticate_user(username, password):
    """验证用户登录"""
    connection = get_db_connection()
    if connection is None:
        return False, "数据库连接失败"
    
    try:
        with connection.cursor() as cursor:
            # 查询用户信息
            sql = """
            SELECT id, username, password_hash, display_name, role, status, login_attempts 
            FROM `mgmt_users` 
            WHERE username = %s AND status = 'active'
            """
            cursor.execute(sql, (username,))
            user = cursor.fetchone()
            
            if not user:
                return False, "用户名或密码错误"
            
            # 检查密码
            if check_password_hash(user['password_hash'], password):
                # 登录成功，更新登录信息
                update_sql = """
                UPDATE `mgmt_users` 
                SET last_login = NOW(), login_attempts = 0 
                WHERE id = %s
                """
                cursor.execute(update_sql, (user['id'],))
                
                # 记录登录日志
                log_sql = """
                INSERT INTO `mgmt_login_logs` (user_id, username, ip_address, user_agent, status)
                VALUES (%s, %s, %s, %s, 'success')
                """
                cursor.execute(log_sql, (
                    user['id'],
                    username,
                    request.remote_addr,
                    request.headers.get('User-Agent')
                ))
                
                connection.commit()
                
                # 返回用户信息
                user_info = {
                    'id': user['id'],
                    'username': user['username'],
                    'display_name': user['display_name'],
                    'role': user['role']
                }
                return True, user_info
            else:
                # 登录失败，增加尝试次数
                update_sql = """
                UPDATE `mgmt_users` 
                SET login_attempts = login_attempts + 1 
                WHERE id = %s
                """
                cursor.execute(update_sql, (user['id'],))
                
                # 记录失败日志
                if user.get('login_attempts', 0) >= 5:
                    # 锁定账户
                    lock_sql = "UPDATE `mgmt_users` SET status = 'locked' WHERE id = %s"
                    cursor.execute(lock_sql, (user['id'],))
                
                log_sql = """
                INSERT INTO `mgmt_login_logs` (user_id, username, ip_address, user_agent, status, failure_reason)
                VALUES (%s, %s, %s, %s, 'failed', '密码错误')
                """
                cursor.execute(log_sql, (
                    user['id'],
                    username,
                    request.remote_addr,
                    request.headers.get('User-Agent')
                ))
                
                connection.commit()
                return False, "用户名或密码错误"
                
    except Exception as e:
        print(f"用户验证失败: {e}")
        return False, f"系统错误: {str(e)}"
    finally:
        if connection:
            connection.close()

def get_current_user():
    """获取当前登录用户信息"""
    if 'user_id' in session and 'username' in session:
        return {
            'id': session['user_id'],
            'username': session['username'],
            'display_name': session.get('display_name'),
            'role': session.get('role')
        }
    return None

def login_required(roles=None):
    """登录验证装饰器"""
    def decorator(f):
        from functools import wraps
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                from flask import redirect, url_for
                return redirect(url_for('auth.login', next=request.url))
            
            if roles and user.get('role') not in roles:
                from flask import render_template
                return render_template('error.html', 
                                     error_message="权限不足，无法访问此页面",
                                     error_code=403), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator