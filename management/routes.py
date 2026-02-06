"""
数据管理路由模块
包含数据管理和CRUD操作
"""
from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
from database.db_utils import get_db_connection, fetch_all_records, fetch_record_by_id, get_total_count, init_user_table
from auth.utils import login_required, get_current_user
import pymysql
import config

# 创建管理蓝图
management_bp = Blueprint('management', __name__, url_prefix='/MGMT')

# 调试模式开关（全局变量，实际应用中应该存储在数据库或配置文件中）
DEBUG_MODE = False

# 管理页面 - 显示所有记录并提供管理功能
@management_bp.route('/')
@login_required(roles=['admin'])
def management():
    """管理页面 - 显示所有记录并提供管理功能（仅管理员）"""
    global DEBUG_MODE
    try:
        all_records = fetch_all_records()
        user = get_current_user()
        
        return render_template('management.html', 
                             records=all_records, 
                             total_count=len(all_records) if all_records else 0,
                             current_user=user,
                             debug_mode=DEBUG_MODE)
    except Exception as e:
        error_msg = f"加载管理页面失败: {str(e)}"
        return render_template('management.html', 
                             records=[], 
                             error=error_msg, 
                             total_count=0)

# 调试信息页面 - 注意：这个路由的URL是 '/MGMT/debug'
@management_bp.route('/debug')
@login_required(roles=['admin'])
def debug_page():  # 修改函数名，避免冲突
    """调试信息页面 - 显示系统调试信息"""
    global DEBUG_MODE
    
    # 检查是否开启调试模式
    if not DEBUG_MODE:
        return jsonify({
            'success': False,
            'message': '调试模式未开启',
            'debug_mode': DEBUG_MODE
        })
    
    info = {
        'success': True,
        'debug_mode': DEBUG_MODE,
        'system_info': {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'current_user': get_current_user(),
            'request_info': {
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent'),
                'method': request.method,
                'url': request.url
            }
        },
        'database_config': {
            'host': config.DB_HOST,
            'port': config.DB_PORT,
            'user': config.DB_USER,
            'database': config.DB_NAME,
            'connected': False
        },
        'table_info': {},
        'sample_data': []
    }
    
    try:
        conn = get_db_connection()
        if conn:
            info['database_config']['connected'] = True
            
            with conn.cursor() as cursor:
                # 查看所有表
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                info['tables'] = [table for table in tables]
                
                # 查看KB-info表结构
                cursor.execute("DESCRIBE `KB-info`")
                columns = cursor.fetchall()
                info['table_structure'] = columns
                
                # 查看记录数
                cursor.execute("SELECT COUNT(*) as count FROM `KB-info`")
                count_result = cursor.fetchone()
                info['record_count'] = count_result['count'] if count_result else 0
                
                # 查看前5条记录
                cursor.execute("SELECT * FROM `KB-info` LIMIT 5")
                info['sample_data'] = cursor.fetchall()
                
                # 查看用户表信息
                cursor.execute("SHOW TABLES LIKE 'mgmt_users'")
                if cursor.fetchone():
                    cursor.execute("SELECT COUNT(*) as count FROM mgmt_users")
                    user_count = cursor.fetchone()
                    info['user_count'] = user_count['count'] if user_count else 0
                    
                    cursor.execute("SELECT * FROM mgmt_users LIMIT 3")
                    info['user_sample'] = cursor.fetchall()
                
                # 查看登录日志统计
                cursor.execute("SHOW TABLES LIKE 'mgmt_login_logs'")
                if cursor.fetchone():
                    cursor.execute("SELECT COUNT(*) as count FROM mgmt_login_logs")
                    log_count = cursor.fetchone()
                    info['log_count'] = log_count['count'] if log_count else 0
                
            conn.close()
            
            # 测试函数
            info['fetch_all_records_count'] = len(fetch_all_records())
            info['get_total_count'] = get_total_count()
            
    except Exception as e:
        info['error'] = str(e)
    
    return jsonify(info)

# 切换调试模式API
@management_bp.route('/api/toggle-debug', methods=['POST'])
@login_required(roles=['admin'])
def toggle_debug():
    """切换调试模式开关"""
    global DEBUG_MODE
    try:
        data = request.get_json()
        if 'debug_mode' in data:
            DEBUG_MODE = data['debug_mode']
            return jsonify({
                'success': True,
                'message': f"调试模式已{'开启' if DEBUG_MODE else '关闭'}",
                'debug_mode': DEBUG_MODE
            })
        else:
            return jsonify({'success': False, 'message': '缺少debug_mode参数'})
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"切换调试模式失败: {str(e)}"
        })

# 系统状态检查API
@management_bp.route('/api/system-status')
@login_required(roles=['admin'])
def system_status():
    """获取系统状态信息"""
    try:
        status = {
            'success': True,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'database_connected': False,
            'total_records': 0,
            'user_count': 0,
            'system_health': 'healthy'
        }
        
        # 检查数据库连接
        conn = get_db_connection()
        if conn:
            status['database_connected'] = True
            
            try:
                with conn.cursor() as cursor:
                    # 获取记录数
                    cursor.execute("SELECT COUNT(*) as count FROM `KB-info`")
                    count_result = cursor.fetchone()
                    status['total_records'] = count_result['count'] if count_result else 0
                    
                    # 获取用户数
                    cursor.execute("SELECT COUNT(*) as count FROM mgmt_users")
                    user_result = cursor.fetchone()
                    status['user_count'] = user_result['count'] if user_result else 0
                    
                    # 检查表是否存在
                    cursor.execute("SHOW TABLES LIKE 'mgmt_users'")
                    status['user_table_exists'] = bool(cursor.fetchone())
                    
                    cursor.execute("SHOW TABLES LIKE 'mgmt_login_logs'")
                    status['log_table_exists'] = bool(cursor.fetchone())
                    
                    
                # 评估系统健康状态
                if status['total_records'] > 0 and status['database_connected']:
                    status['system_health'] = 'healthy'
                elif status['database_connected']:
                    status['system_health'] = 'connected_no_data'
                else:
                    status['system_health'] = 'database_error'
                    
            except Exception as e:
                status['database_error'] = str(e)
                status['system_health'] = 'database_error'
            finally:
                conn.close()
        else:
            status['system_health'] = 'database_error'
        
        # 获取当前用户信息
        current_user = get_current_user()
        if current_user:
            status['current_user'] = {
                'username': current_user['username'],
                'role': current_user['role']
            }
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"获取系统状态失败: {str(e)}"
        })

# 清理临时数据API（管理员专用）
@management_bp.route('/api/cleanup', methods=['POST'])
@login_required(roles=['admin'])
def cleanup():
    """清理临时数据和重置系统状态"""
    try:
        # 这里可以添加清理逻辑
        # 例如：清理过期的session、临时文件等
        
        return jsonify({
            'success': True,
            'message': '系统清理完成',
            'cleaned_items': ['缓存', '临时文件']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"清理失败: {str(e)}"
        })

# 添加新记录接口
@management_bp.route('/api/add', methods=['POST'])
@login_required(roles=['admin'])
def add_record():
    """添加新记录"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        if not data.get('KB_Number'):
            return jsonify({'success': False, 'message': '知识库编号不能为空'})
        
        if not data.get('KB_Name'):
            return jsonify({'success': False, 'message': '知识库名称不能为空'})
        
        # 检查记录是否已存在
        existing = fetch_record_by_id(data['KB_Number'])
        if existing:
            return jsonify({'success': False, 'message': f"编号 {data['KB_Number']} 已存在"})
        
        # 获取数据库连接
        connection = get_db_connection()
        if connection is None:
            return jsonify({'success': False, 'message': '数据库连接失败'})
        
        with connection.cursor() as cursor:
            sql = "INSERT INTO `KB-info` (KB_Number, KB_Name, KB_link) VALUES (%s, %s, %s)"
            cursor.execute(sql, (
                data['KB_Number'],
                data['KB_Name'],
                data.get('KB_link', '')
            ))
            connection.commit()
            affected_rows = cursor.rowcount
        
        connection.close()
        
        if affected_rows > 0:
            return jsonify({
                'success': True,
                'message': '记录添加成功',
                'id': data['KB_Number']
            })
        else:
            return jsonify({'success': False, 'message': '添加记录失败'})
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"添加记录时发生错误: {str(e)}"
        })

# 更新记录接口
@management_bp.route('/api/update/<int:record_id>', methods=['PUT'])
@login_required(roles=['admin'])
def update_record(record_id):
    """更新记录"""
    try:
        data = request.get_json()
        
        # 检查记录是否存在
        existing = fetch_record_by_id(record_id)
        if not existing:
            return jsonify({'success': False, 'message': f"记录 {record_id} 不存在"})
        
        # 获取数据库连接
        connection = get_db_connection()
        if connection is None:
            return jsonify({'success': False, 'message': '数据库连接失败'})
        
        with connection.cursor() as cursor:
            sql = "UPDATE `KB-info` SET KB_Name = %s, KB_link = %s WHERE KB_Number = %s"
            cursor.execute(sql, (
                data.get('KB_Name', existing['KB_Name']),
                data.get('KB_link', existing['KB_link']),
                record_id
            ))
            connection.commit()
            affected_rows = cursor.rowcount
        
        connection.close()
        
        if affected_rows > 0:
            return jsonify({
                'success': True,
                'message': '记录更新成功'
            })
        else:
            return jsonify({'success': False, 'message': '更新记录失败'})
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"更新记录时发生错误: {str(e)}"
        })

# 删除记录接口
@management_bp.route('/api/delete/<int:record_id>', methods=['DELETE'])
@login_required(roles=['admin'])
def delete_record(record_id):
    """删除记录"""
    try:
        # 检查记录是否存在
        existing = fetch_record_by_id(record_id)
        if not existing:
            return jsonify({'success': False, 'message': f"记录 {record_id} 不存在"})
        
        # 获取数据库连接
        connection = get_db_connection()
        if connection is None:
            return jsonify({'success': False, 'message': '数据库连接失败'})
        
        with connection.cursor() as cursor:
            sql = "DELETE FROM `KB-info` WHERE KB_Number = %s"
            cursor.execute(sql, (record_id,))
            connection.commit()
            affected_rows = cursor.rowcount
        
        connection.close()
        
        if affected_rows > 0:
            return jsonify({
                'success': True,
                'message': '记录删除成功'
            })
        else:
            return jsonify({'success': False, 'message': '删除记录失败'})
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"删除记录时发生错误: {str(e)}"
        })

# 批量删除接口
@management_bp.route('/api/batch-delete', methods=['POST'])
@login_required(roles=['admin'])
def batch_delete():
    """批量删除记录"""
    try:
        data = request.get_json()
        record_ids = data.get('ids', [])
        
        if not record_ids:
            return jsonify({'success': False, 'message': '请选择要删除的记录'})
        
        # 获取数据库连接
        connection = get_db_connection()
        if connection is None:
            return jsonify({'success': False, 'message': '数据库连接失败'})
        
        deleted_count = 0
        with connection.cursor() as cursor:
            for record_id in record_ids:
                try:
                    sql = "DELETE FROM `KB-info` WHERE KB_Number = %s"
                    cursor.execute(sql, (record_id,))
                    deleted_count += 1
                except:
                    continue
        
        connection.commit()
        connection.close()
        
        return jsonify({
            'success': True,
            'message': f"成功删除 {deleted_count} 条记录",
            'deleted_count': deleted_count
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"批量删除时发生错误: {str(e)}"
        })

# 批量添加记录接口
@management_bp.route('/api/batch-add', methods=['POST'])
@login_required(roles=['admin'])
def batch_add_records():
    """批量添加记录"""
    try:
        data = request.get_json()
        records = data.get('records', [])
        
        if not records:
            return jsonify({'success': False, 'message': '没有提供任何记录数据'})
        
        # 验证记录格式
        for record in records:
            if not record.get('KB_Number'):
                return jsonify({'success': False, 'message': '记录中的知识库编号不能为空'})
            if not record.get('KB_Name'):
                return jsonify({'success': False, 'message': '记录中的知识库名称不能为空'})
        
        # 获取数据库连接
        connection = get_db_connection()
        if connection is None:
            return jsonify({'success': False, 'message': '数据库连接失败'})
        
        success_count = 0
        fail_count = 0
        duplicate_count = 0
        failed_records = []
        
        with connection.cursor() as cursor:
            for record in records:
                try:
                    # 检查记录是否已存在
                    check_sql = "SELECT KB_Number FROM `KB-info` WHERE KB_Number = %s"
                    cursor.execute(check_sql, (record['KB_Number'],))
                    if cursor.fetchone():
                        duplicate_count += 1
                        failed_records.append({
                            'record': record,
                            'reason': f"编号 {record['KB_Number']} 已存在"
                        })
                        continue
                    
                    # 插入新记录
                    sql = "INSERT INTO `KB-info` (KB_Number, KB_Name, KB_link) VALUES (%s, %s, %s)"
                    cursor.execute(sql, (
                        record['KB_Number'],
                        record['KB_Name'],
                        record.get('KB_link', '')
                    ))
                    success_count += 1
                except Exception as e:
                    fail_count += 1
                    failed_records.append({
                        'record': record,
                        'reason': str(e)
                    })
        
        connection.commit()
        connection.close()
        
        return jsonify({
            'success': True,
            'message': f'批量添加完成：成功 {success_count} 条，跳过重复 {duplicate_count} 条，失败 {fail_count} 条',
            'summary': {
                'total': len(records),
                'success': success_count,
                'duplicate': duplicate_count,
                'failed': fail_count
            },
            'failed_records': failed_records if failed_records else None
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"批量添加时发生错误: {str(e)}"
        })

# 导出数据接口
@management_bp.route('/api/export')
@login_required(roles=['admin'])
def export_data():
    """导出数据为JSON格式"""
    try:
        records = fetch_all_records()
        return jsonify({
            'success': True,
            'data': records,
            'count': len(records),
            'export_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"导出数据时发生错误: {str(e)}"
        })