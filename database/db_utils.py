"""
数据库工具模块
包含数据库连接和通用数据库函数
"""
import pymysql
import config
from werkzeug.security import generate_password_hash, check_password_hash

def get_db_connection():
    """获取数据库连接"""
    try:
        connection = pymysql.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None

def init_user_table():
    """初始化用户表，如果不存在则创建"""
    connection = get_db_connection()
    if connection is None:
        return False
    
    try:
        with connection.cursor() as cursor:
            # 检查用户表是否存在
            cursor.execute("SHOW TABLES LIKE 'mgmt_users'")
            if not cursor.fetchone():
                # 创建用户表
                create_table_sql = """
                CREATE TABLE `mgmt_users` (
                    `id` INT AUTO_INCREMENT PRIMARY KEY,
                    `username` VARCHAR(50) NOT NULL UNIQUE,
                    `password_hash` VARCHAR(255) NOT NULL,
                    `display_name` VARCHAR(100),
                    `role` VARCHAR(20) DEFAULT 'user',
                    `status` VARCHAR(20) DEFAULT 'active',
                    `last_login` TIMESTAMP NULL,
                    `login_attempts` INT DEFAULT 0,
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    `created_by` VARCHAR(50)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
                cursor.execute(create_table_sql)
                
                # 创建默认管理员账号
                password_hash = generate_password_hash(config.DEFAULT_ADMIN_PASSWORD)
                insert_sql = """
                INSERT INTO `mgmt_users` (username, password_hash, display_name, role, created_by)
                VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(insert_sql, (
                    config.DEFAULT_ADMIN_USERNAME,
                    password_hash,
                    '系统管理员',
                    'admin',
                    'system'
                ))
                
                connection.commit()
                print("用户表已创建，默认管理员账号已初始化")
            else:
                print("用户表已存在")
                
        return True
    except Exception as e:
        print(f"初始化用户表失败: {e}")
        return False
    finally:
        if connection:
            connection.close()

def fetch_all_records():
    """获取所有记录"""
    connection = get_db_connection()
    if connection is None:
        return []

    try:
        with connection.cursor() as cursor:
            # 注意表名有连字符，需要用反引号包裹
            sql = "SELECT * FROM `KB-info` ORDER BY KB_Number"
            cursor.execute(sql)
            results = cursor.fetchall()
            return results
    except Exception as e:
        print(f"查询失败: {e}")
        return []
    finally:
        if connection:
            connection.close()

def fetch_records_with_pagination(page=1, per_page=15):
    """分页获取记录"""
    connection = get_db_connection()
    if connection is None:
        return [], 0

    try:
        with connection.cursor() as cursor:
            # 获取总数
            count_sql = "SELECT COUNT(*) as count FROM `KB-info`"
            cursor.execute(count_sql)
            total_count = cursor.fetchone()['count']

            # 计算偏移量
            offset = (page - 1) * per_page

            # 获取当前页数据
            data_sql = "SELECT * FROM `KB-info` ORDER BY KB_Number LIMIT %s OFFSET %s"
            cursor.execute(data_sql, (per_page, offset))
            results = cursor.fetchall()

            return results, total_count
    except Exception as e:
        print(f"分页查询失败: {e}")
        return [], 0
    finally:
        if connection:
            connection.close()

def fetch_record_by_id(record_id):
    """根据ID获取记录"""
    connection = get_db_connection()
    if connection is None:
        return None
    
    try:
        with connection.cursor() as cursor:
            # 使用参数化查询防止SQL注入
            sql = "SELECT * FROM `KB-info` WHERE KB_Number = %s"
            cursor.execute(sql, (record_id,))
            result = cursor.fetchone()
            return result
    except Exception as e:
        print(f"根据ID查询失败: {e}")
        return None
    finally:
        if connection:
            connection.close()

def fetch_records_by_name(name):
    """根据名称模糊搜索"""
    connection = get_db_connection()
    if connection is None:
        return []

    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM `KB-info` WHERE KB_Name LIKE %s ORDER BY KB_Number"
            cursor.execute(sql, (f'%{name}%',))
            results = cursor.fetchall()
            return results
    except Exception as e:
        print(f"按名称搜索失败: {e}")
        return []
    finally:
        if connection:
            connection.close()

def fetch_records_by_name_with_pagination(name, page=1, per_page=15):
    """根据名称模糊搜索（支持分页）"""
    connection = get_db_connection()
    if connection is None:
        return [], 0

    try:
        with connection.cursor() as cursor:
            # 获取总数
            count_sql = "SELECT COUNT(*) as count FROM `KB-info` WHERE KB_Name LIKE %s"
            cursor.execute(count_sql, (f'%{name}%',))
            total_count = cursor.fetchone()['count']

            # 计算偏移量
            offset = (page - 1) * per_page

            # 获取当前页数据
            data_sql = "SELECT * FROM `KB-info` WHERE KB_Name LIKE %s ORDER BY KB_Number LIMIT %s OFFSET %s"
            cursor.execute(data_sql, (f'%{name}%', per_page, offset))
            results = cursor.fetchall()

            return results, total_count
    except Exception as e:
        print(f"按名称分页搜索失败: {e}")
        return [], 0
    finally:
        if connection:
            connection.close()

def get_total_count():
    """获取总记录数"""
    connection = get_db_connection()
    if connection is None:
        return 0
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM `KB-info`")
            result = cursor.fetchone()
            return result['count'] if result else 0
    except Exception as e:
        print(f"获取记录数失败: {e}")
        return 0
    finally:
        if connection:
            connection.close()