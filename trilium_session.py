"""
Trilium会话管理器
用于模拟浏览器登录Trilium，获取有效的会话cookie
"""

import requests
from urllib.parse import urljoin
from config import TRILIUM_SERVER_URL
import time

class TriliumSessionManager:
    """管理Trilium登录会话"""
    
    def __init__(self):
        self.server_url = TRILIUM_SERVER_URL.rstrip('/')
        self.session = None
        self.last_login_time = 0
        self.session_timeout = 3600  # 会话超时时间（秒）
        self.username = None
        self.password = None
        
    def login(self, username, password):
        """登录Trilium"""
        try:
            print(f"尝试登录Trilium: {self.server_url}")
            
            # 创建新会话
            self.session = requests.Session()
            
            # 首先访问登录页面获取CSRF token
            login_page_url = f"{self.server_url}/login"
            response = self.session.get(login_page_url, timeout=10)
            
            # 尝试从页面中提取CSRF token
            csrf_token = None
            if '<input type="hidden" name="_csrf"' in response.text:
                # 提取CSRF token
                import re
                csrf_match = re.search(r'name="_csrf" value="([^"]+)"', response.text)
                if csrf_match:
                    csrf_token = csrf_match.group(1)
                    print(f"找到CSRF token: {csrf_token[:10]}...")
            
            # 准备登录数据
            login_data = {
                'username': username,
                'password': password
            }
            
            if csrf_token:
                login_data['_csrf'] = csrf_token
            
            # 提交登录
            login_url = f"{self.server_url}/login"
            response = self.session.post(
                login_url, 
                data=login_data,
                timeout=10,
                allow_redirects=True
            )
            
            # 检查是否登录成功
            if response.status_code == 200:
                # 检查响应中是否包含登录成功的信息
                if 'Login failed' in response.text:
                    print("登录失败：用户名或密码错误")
                    return False
                
                # 检查是否有会话cookie
                if self.session.cookies.get('connect.sid'):
                    self.last_login_time = time.time()
                    self.username = username
                    self.password = password
                    print("✅ Trilium登录成功")
                    return True
                else:
                    print("登录失败：未获取到会话cookie")
                    return False
            else:
                print(f"登录请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"登录过程中发生错误: {e}")
            return False
    
    def is_session_valid(self):
        """检查会话是否有效"""
        if not self.session:
            return False
        
        # 检查会话是否过期
        if time.time() - self.last_login_time > self.session_timeout:
            print("会话已过期")
            return False
        
        # 测试会话是否有效
        try:
            test_url = f"{self.server_url}/"
            response = self.session.get(test_url, timeout=5)
            return response.status_code == 200 and 'Trilium' in response.text
        except:
            return False
    
    def ensure_session(self):
        """确保有有效的会话"""
        if self.is_session_valid():
            return True
        
        # 尝试重新登录
        if self.username and self.password:
            print("会话无效，尝试重新登录...")
            return self.login(self.username, self.password)
        
        return False
    
    def get_attachment(self, attachment_path):
        """获取附件内容"""
        if not self.ensure_session():
            return None
        
        try:
            # 构建附件URL
            if attachment_path.startswith('/'):
                attachment_path = attachment_path[1:]
            
            # 注意：这里使用 /api/attachments/ 路径
            attachment_url = f"{self.server_url}/api/attachments/{attachment_path}"
            
            print(f"获取附件: {attachment_url}")
            
            response = self.session.get(
                attachment_url,
                timeout=10,
                stream=True  # 使用流式传输，避免大文件内存问题
            )
            
            if response.status_code == 200:
                # 读取内容
                content = response.content
                content_type = response.headers.get('Content-Type', 'application/octet-stream')
                
                print(f"✅ 成功获取附件，大小: {len(content)} 字节，类型: {content_type}")
                return content, content_type
            else:
                print(f"获取附件失败: {response.status_code}")
                return None, None
                
        except Exception as e:
            print(f"获取附件过程中发生错误: {e}")
            return None, None
    
    def logout(self):
        """登出"""
        if self.session:
            try:
                logout_url = f"{self.server_url}/logout"
                self.session.get(logout_url, timeout=5)
            except:
                pass
            finally:
                self.session = None
                self.last_login_time = 0
                print("已登出Trilium")


# 全局会话管理器实例
_session_manager = None

def get_trilium_session_manager():
    """获取全局会话管理器实例"""
    global _session_manager
    if _session_manager is None:
        _session_manager = TriliumSessionManager()
    return _session_manager