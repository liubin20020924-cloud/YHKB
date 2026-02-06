"""
认证路由模块
包含登录、登出、用户管理等路由
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from auth.utils import authenticate_user, get_current_user, login_required
from database.db_utils import get_db_connection
from werkzeug.security import generate_password_hash
from datetime import datetime

# 创建认证蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# 登录页面
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    # 如果已经登录，重定向到首页
    if get_current_user():
        return redirect(url_for('views.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            return render_template('login.html',
                                 error="请输入用户名和密码")

        success, result = authenticate_user(username, password)

        if success:
            # 保存用户信息到session
            user_info = result
            session['user_id'] = user_info['id']
            session['username'] = user_info['username']
            session['display_name'] = user_info['display_name']
            session['role'] = user_info['role']
            session['login_time'] = datetime.now().isoformat()

            # 设置session永不过期（浏览器关闭后失效）
            session.permanent = False

            # 获取next参数，如果存在则跳转到指定页面
            next_url = request.form.get('next')
            if next_url:
                return redirect(next_url)

            # 重定向到首页
            return redirect(url_for('views.index'))
        else:
            return render_template('login.html',
                                 error=result,
                                 username=username)

    return render_template('login.html')

# 退出登录
@auth_bp.route('/logout')
def logout():
    """退出登录"""
    session.clear()
    return redirect(url_for('auth.login'))

# 检查登录状态
@auth_bp.route('/check-login')
def check_login():
    """检查登录状态"""
    user = get_current_user()
    if user:
        return jsonify({
            'success': True,
            'user': user
        })
    return jsonify({'success': False})

# 用户管理页面
@auth_bp.route('/users')
@login_required(roles=['admin'])
def user_management():
    """用户管理页面"""
    connection = get_db_connection()
    if connection is None:
        return render_template('user_management.html', 
                             error="数据库连接失败",
                             users=[])
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, username, display_name, role, status, 
                       last_login, created_at, updated_at 
                FROM mgmt_users 
                ORDER BY created_at DESC
            """)
            users = cursor.fetchall()
            
            # 获取登录日志
            cursor.execute("""
                SELECT l.*, u.display_name 
                FROM mgmt_login_logs l
                LEFT JOIN mgmt_users u ON l.user_id = u.id
                ORDER BY l.login_time DESC 
                LIMIT 50
            """)
            login_logs = cursor.fetchall()
            
        return render_template('user_management.html', 
                             users=users, 
                             login_logs=login_logs,
                             current_user=get_current_user())
    except Exception as e:
        print(f"获取用户列表失败: {e}")
        return render_template('user_management.html', 
                             error=f"获取用户列表失败: {str(e)}",
                             users=[])
    finally:
        if connection:
            connection.close()

# 添加用户API
@auth_bp.route('/api/add-user', methods=['POST'])
@login_required(roles=['admin'])
def add_user():
    """添加新用户"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        if not data.get('username'):
            return jsonify({'success': False, 'message': '用户名不能为空'})
        
        if not data.get('password'):
            return jsonify({'success': False, 'message': '密码不能为空'})
        
        connection = get_db_connection()
        if connection is None:
            return jsonify({'success': False, 'message': '数据库连接失败'})
        
        # 检查用户名是否已存在
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM mgmt_users WHERE username = %s", (data['username'],))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': f"用户名 {data['username']} 已存在"})
            
            # 生成密码哈希
            password_hash = generate_password_hash(data['password'])
            
            # 插入新用户
            sql = """
            INSERT INTO mgmt_users (username, password_hash, display_name, role, status, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                data['username'],
                password_hash,
                data.get('display_name', ''),
                data.get('role', 'user'),
                data.get('status', 'active'),
                get_current_user()['username']
            ))
            connection.commit()
            user_id = cursor.lastrowid
        
        connection.close()
        
        return jsonify({
            'success': True,
            'message': '用户添加成功',
            'user_id': user_id
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"添加用户时发生错误: {str(e)}"
        })

# 更新用户API
@auth_bp.route('/api/update-user/<int:user_id>', methods=['PUT'])
@login_required(roles=['admin'])
def update_user(user_id):
    """更新用户信息"""
    try:
        data = request.get_json()
        
        connection = get_db_connection()
        if connection is None:
            return jsonify({'success': False, 'message': '数据库连接失败'})
        
        # 检查用户是否存在
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, username FROM mgmt_users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'success': False, 'message': f"用户 ID {user_id} 不存在"})
            
            # 如果是admin用户，不允许修改角色
            if user['username'] == 'admin' and data.get('role') != 'admin':
                return jsonify({'success': False, 'message': '不能修改管理员admin的角色'})
            
            # 构建更新SQL
            update_fields = []
            params = []
            
            if 'display_name' in data:
                update_fields.append("display_name = %s")
                params.append(data['display_name'])
            
            if 'role' in data:
                update_fields.append("role = %s")
                params.append(data['role'])
            
            if 'status' in data:
                update_fields.append("status = %s")
                params.append(data['status'])
            
            if 'password' in data and data['password']:
                update_fields.append("password_hash = %s")
                params.append(generate_password_hash(data['password']))
            
            if not update_fields:
                return jsonify({'success': False, 'message': '没有提供需要更新的字段'})
            
            # 执行更新
            update_fields.append("updated_at = NOW()")
            sql = f"UPDATE mgmt_users SET {', '.join(update_fields)} WHERE id = %s"
            params.append(user_id)
            
            cursor.execute(sql, params)
            connection.commit()
        
        connection.close()
        
        return jsonify({
            'success': True,
            'message': '用户信息更新成功'
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"更新用户时发生错误: {str(e)}"
        })

# 删除用户API
@auth_bp.route('/api/delete-user/<int:user_id>', methods=['DELETE'])
@login_required(roles=['admin'])
def delete_user(user_id):
    """删除用户"""
    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({'success': False, 'message': '数据库连接失败'})
        
        # 检查用户是否存在
        with connection.cursor() as cursor:
            cursor.execute("SELECT username FROM mgmt_users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'success': False, 'message': f"用户 ID {user_id} 不存在"})
            
            # 不允许删除admin用户
            if user['username'] == 'admin':
                return jsonify({'success': False, 'message': '不能删除管理员admin'})
            
            # 删除用户登录日志
            cursor.execute("DELETE FROM mgmt_login_logs WHERE user_id = %s", (user_id,))
            
            # 删除用户
            cursor.execute("DELETE FROM mgmt_users WHERE id = %s", (user_id,))
            connection.commit()
        
        connection.close()
        
        return jsonify({
            'success': True,
            'message': f"用户 {user['username']} 删除成功"
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"删除用户时发生错误: {str(e)}"
        })

# 解锁用户API
@auth_bp.route('/api/unlock-user/<int:user_id>', methods=['POST'])
@login_required(roles=['admin'])
def unlock_user(user_id):
    """解锁被锁定的用户"""
    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({'success': False, 'message': '数据库连接失败'})
        
        with connection.cursor() as cursor:
            # 检查用户是否存在且被锁定
            cursor.execute("SELECT username, status FROM mgmt_users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'success': False, 'message': f"用户 ID {user_id} 不存在"})
            
            if user['status'] != 'locked':
                return jsonify({'success': False, 'message': f"用户 {user['username']} 未被锁定"})
            
            # 解锁用户并重置登录尝试次数
            cursor.execute("""
                UPDATE mgmt_users 
                SET status = 'active', login_attempts = 0 
                WHERE id = %s
            """, (user_id,))
            connection.commit()
        
        connection.close()
        
        return jsonify({
            'success': True,
            'message': f"用户 {user['username']} 已解锁"
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"解锁用户时发生错误: {str(e)}"
        })

# 获取用户详情API
@auth_bp.route('/api/user/<int:user_id>')
@login_required(roles=['admin'])
def get_user(user_id):
    """获取用户详情"""
    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({'success': False, 'message': '数据库连接失败'})
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, username, display_name, role, status, 
                       last_login, created_at, updated_at 
                FROM mgmt_users 
                WHERE id = %s
            """, (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'success': False, 'message': '用户不存在'})
            
            # 获取用户的登录统计
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_logins,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_logins,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_logins,
                    MAX(login_time) as last_login_time
                FROM mgmt_login_logs 
                WHERE user_id = %s
            """, (user_id,))
            stats = cursor.fetchone()
        
        connection.close()
        
        return jsonify({
            'success': True,
            'user': user,
            'stats': stats or {
                'total_logins': 0,
                'success_logins': 0,
                'failed_logins': 0,
                'last_login_time': None
            }
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"获取用户信息时发生错误: {str(e)}"
        })

# 修改当前用户密码API
@auth_bp.route('/api/change-password', methods=['POST'])
@login_required(roles=['admin', 'user'])
def change_password():
    """修改当前登录用户的密码"""
    try:
        data = request.get_json()
        
        current_user = get_current_user()
        if not current_user:
            return jsonify({'success': False, 'message': '用户未登录'})
        
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        
        if not old_password or not new_password:
            return jsonify({'success': False, 'message': '请输入旧密码和新密码'})
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': '新密码长度不能少于6位'})
        
        connection = get_db_connection()
        if connection is None:
            return jsonify({'success': False, 'message': '数据库连接失败'})
        
        with connection.cursor() as cursor:
            # 验证旧密码
            cursor.execute("SELECT password_hash FROM mgmt_users WHERE id = %s", (current_user['id'],))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'success': False, 'message': '用户不存在'})
            
            from werkzeug.security import check_password_hash
            if not check_password_hash(user['password_hash'], old_password):
                return jsonify({'success': False, 'message': '旧密码错误'})
            
            # 更新密码
            new_password_hash = generate_password_hash(new_password)
            cursor.execute("""
                UPDATE mgmt_users 
                SET password_hash = %s, updated_at = NOW() 
                WHERE id = %s
            """, (new_password_hash, current_user['id']))
            connection.commit()
        
        connection.close()
        
        return jsonify({
            'success': True,
            'message': '密码修改成功'
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"修改密码时发生错误: {str(e)}"
        })

# 重置用户密码API（管理员功能）
@auth_bp.route('/api/reset-password/<int:user_id>', methods=['POST'])
@login_required(roles=['admin'])
def reset_password(user_id):
    """管理员重置用户密码"""
    try:
        data = request.get_json()
        new_password = data.get('new_password')
        
        if not new_password:
            return jsonify({'success': False, 'message': '请输入新密码'})
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': '新密码长度不能少于6位'})
        
        connection = get_db_connection()
        if connection is None:
            return jsonify({'success': False, 'message': '数据库连接失败'})
        
        with connection.cursor() as cursor:
            # 检查用户是否存在
            cursor.execute("SELECT username FROM mgmt_users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'success': False, 'message': '用户不存在'})
            
            # 重置密码
            new_password_hash = generate_password_hash(new_password)
            cursor.execute("""
                UPDATE mgmt_users 
                SET password_hash = %s, updated_at = NOW(), login_attempts = 0 
                WHERE id = %s
            """, (new_password_hash, user_id))
            connection.commit()
        
        connection.close()
        
        return jsonify({
            'success': True,
            'message': f"用户 {user['username']} 密码重置成功"
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"重置密码时发生错误: {str(e)}"
        })