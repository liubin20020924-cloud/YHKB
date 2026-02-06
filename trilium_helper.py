"""
Trilium 帮助模块 (基于 trilium-py 客户端)
用于与Trilium Notes服务器交互，获取笔记内容。
注意：ETAPI需要的是 #root/ 后面的持久化笔记ID，而不是URL中的 ntxId 参数。
"""
import re
import html
import bleach
from urllib.parse import urljoin, quote_plus
from trilium_py.client import ETAPI
import config
import config

class TriliumHelper:
    """Trilium 帮助类，封装客户端和工具方法"""
    
    def __init__(self):
        """初始化Trilium ETAPI客户端"""
        print("=== TriliumHelper 初始化 ===")
        
        # 调试：检查config中所有Trilium相关的属性
        print("检查config中的Trilium配置:")
        trilium_attrs = [attr for attr in dir(config) if 'TRILIUM' in attr.upper()]
        for attr in trilium_attrs:
            try:
                value = getattr(config, attr)
                # 对于令牌，显示部分字符
                if 'TOKEN' in attr.upper():
                    value = f"{str(value)[:10]}..." if value else "未设置"
                print(f"  config.{attr} = {value}")
            except:
                print(f"  config.{attr} = [无法读取]")
        
        # 尝试获取服务器地址（兼容两种命名）
        self.server_url = None
        if hasattr(config, 'TRILIUM_SERVER_URL'):
            self.server_url = config.TRILIUM_SERVER_URL
            print(f"使用配置: TRILIUM_SERVER_URL = {self.server_url}")
        elif hasattr(config, 'TRILIUM_URL'):
            self.server_url = config.TRILIUM_URL
            print(f"使用配置: TRILIUM_URL = {self.server_url}")
        else:
            error_msg = "config.py中未找到TRILIUM_SERVER_URL或TRILIUM_URL配置"
            print(f"❌ 错误: {error_msg}")
            raise ValueError(error_msg)
        
        # 尝试获取令牌
        self.token = None
        if hasattr(config, 'TRILIUM_TOKEN'):
            self.token = config.TRILIUM_TOKEN
            if self.token:
                token_display = f"{str(self.token)[:10]}..."
                print(f"使用配置: TRILIUM_TOKEN = {token_display}")
            else:
                print("⚠️  警告: TRILIUM_TOKEN 配置为空")
        else:
            error_msg = "config.py中未找到TRILIUM_TOKEN配置"
            print(f"❌ 错误: {error_msg}")
            raise ValueError(error_msg)
        
        # 清理URL
        if self.server_url:
            self.server_url = self.server_url.rstrip('/')
            print(f"清理后服务器地址: {self.server_url}")
        
        # 初始化 trilium-py 客户端
        try:
            print(f"尝试初始化ETAPI客户端: {self.server_url}")
            self.client = ETAPI(self.server_url, self.token)
            print("✅ Trilium ETAPI客户端初始化成功")
        except Exception as e:
            error_msg = f"ETAPI客户端初始化失败: {type(e).__name__}: {e}"
            print(f"❌ {error_msg}")
            raise
    
    def is_available(self):
        """检查客户端是否可用"""
        return self.client is not None
    
    def test_connection(self):
        """测试与Trilium服务器的连接"""
        if not self.is_available():
            return {'success': False, 'connected': False, 'message': '客户端未初始化'}
        
        try:
            print(f"测试连接: {self.server_url}")
            
            # 调用应用信息接口测试连接
            info = self.client.app_info()
            print(f"连接测试响应: {info}")
            
            if info and 'version' in info:
                return {
                    'success': True, 
                    'connected': True, 
                    'message': f"连接成功，服务器版本: {info['version']}",
                    'version': info['version']
                }
            else:
                return {'success': False, 'connected': False, 'message': '连接测试返回异常数据'}
                
        except Exception as e:
            error_msg = str(e)
            print(f"连接测试异常: {error_msg}")
            
            # 尝试提取更友好的错误信息
            if '401' in error_msg:
                return {'success': False, 'connected': False, 'message': '认证失败，请检查ETAPI令牌'}
            elif '404' in error_msg:
                return {'success': False, 'connected': False, 'message': 'API端点不存在，请确认服务器地址和ETAPI是否启用'}
            elif 'Connection refused' in error_msg or '无法访问' in error_msg:
                return {'success': False, 'connected': False, 'message': '无法连接到服务器，请检查地址和端口'}
            elif 'getaddrinfo failed' in error_msg:
                return {'success': False, 'connected': False, 'message': '无法解析服务器地址，请检查URL格式'}
            else:
                return {'success': False, 'connected': False, 'message': f'连接测试失败: {error_msg}'}
    
    def extract_note_id_from_url(self, trilium_url):
        """从Trilium前端URL中提取真实的笔记ID（修正版）

        重要：ETAPI需要的是 #root/ 后面的持久化笔记ID，而不是URL中的 ntxId 参数。

        支持格式:
        1. 直接根笔记: http://服务器地址:8080/#root/NJ2k4edE9aQz
        2. 带ntxId参数: http://服务器地址:8080/#root/NJ2k4edE9aQz?ntxId=xyCGyp
        3. 嵌套笔记: http://服务器地址:8080/#root/qGdjohlw9XGf/NJ2k4edE9aQz?ntxId=xyCGyp
        4. 旧格式（兼容）: http://服务器地址:8080/#root/qGdjohlw9XGf/QgFQxmwJktad?ntxId=tKqABR
        """
        if not trilium_url:
            print("❌ 提取笔记ID: URL为空")
            return None

        print(f"解析Trilium URL: {trilium_url}")

        # 方法1: 优先从 #root/ 路径中提取（这是正确的持久化笔记ID）
        # 示例: #root/NJ2k4edE9aQz 或 #root/qGdjohlw9XGf/NJ2k4edE9aQz
        root_pattern = r'#root/(?:[a-zA-Z0-9]+/)*([a-zA-Z0-9]+)'
        root_match = re.search(root_pattern, trilium_url)

        if root_match:
            note_id = root_match.group(1)
            print(f"✅ 从 #root/ 路径提取到持久化笔记ID: {note_id}")

            # 同时检查是否有ntxId参数，用于对比
            ntxid_match = re.search(r'[?&]ntxId=([a-zA-Z0-9_-]+)', trilium_url)
            if ntxid_match:
                ntx_id = ntxid_match.group(1)
                print(f"   注意: URL中包含 ntxId 参数: {ntx_id} (这是前端会话ID，不是持久化笔记ID)")
                if note_id != ntx_id:
                    print(f"   ⚠️  警告: 路径ID({note_id}) 与 ntxId({ntx_id}) 不一致")
                    print(f"   ℹ️  ETAPI应使用路径ID: {note_id}")
            
            return note_id
        
        # 方法2: 回退到旧的ntxId提取（兼容旧格式，但可能不正确）
        print("⚠️  警告：无法从 #root/ 路径提取ID，尝试回退到ntxId参数")
        ntxid_match = re.search(r'[?&]ntxId=([a-zA-Z0-9_-]+)', trilium_url)
        if ntxid_match:
            note_id = ntxid_match.group(1)
            print(f"⚠️  从ntxId参数提取到ID: {note_id}")
            print(f"   ⚠️  注意: ntxId是前端会话ID，可能不是ETAPI所需的持久化笔记ID")
            print(f"   ℹ️  如果此ID导致404，请在Trilium中获取正确的 #root/NoteId 格式URL")
            return note_id
        
        print("❌ 无法从URL中提取出任何有效的ID")
        print(f"   原始URL: {trilium_url}")
        print(f"   ℹ️  正确格式应为: {config.TRILIUM_BASE_URL}/#root/NoteId 或 {config.TRILIUM_BASE_URL}/#root/NoteId?ntxId=xxx")
        return None
    
    def get_note_content_by_url(self, trilium_url):
        """通过Trilium前端URL获取笔记内容"""
        if not self.is_available():
            return {'success': False, 'message': 'Trilium客户端未初始化'}
        
        # 1. 从URL提取笔记ID（使用修正后的方法）
        note_id = self.extract_note_id_from_url(trilium_url)
        if not note_id:
            return {'success': False, 'message': '无法从提供的URL中提取有效的笔记ID'}
        
        print(f"正在获取笔记内容，ID: {note_id}")
        
        try:
            # 2. 使用 trilium-py 客户端获取笔记内容
            content = self.client.get_note_content(note_id)
            
            # 3. 检查内容是否为错误响应（有时API返回JSON错误而不是抛出异常）
            if isinstance(content, dict) and 'status' in content and content['status'] >= 400:
                error_msg = content.get('message', f"API错误: {content}")
                print(f"❌ API返回错误: {error_msg}")
                return {'success': False, 'message': error_msg}
            
            print(f"✅ 成功获取笔记内容，长度: {len(content) if content else 0} 字符")
            
            # 4. 获取笔记元数据（标题、修改时间等）
            note_info = self.client.get_note(note_id)
            print(f"笔记信息: 标题='{note_info.get('title', '无标题')}', 类型='{note_info.get('type', 'text')}'")
            
            return {
                'success': True,
                'note_id': note_id,
                'title': note_info.get('title', '无标题'),
                'content': content,  # 原始内容，后续可由 format_content_for_display 处理
                'content_type': note_info.get('mime', 'text/html'),
                'created': note_info.get('dateCreated'),
                'modified': note_info.get('utcDateModified'),
                'type': note_info.get('type', 'text')
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ 获取笔记内容失败: {error_msg}")
            
            # 提供更友好的错误信息
            if '404' in error_msg:
                return {
                    'success': False, 
                    'message': f"笔记 (ID: {note_id}) 不存在",
                    'suggestion': '请检查: 1. 笔记ID是否正确 2. ETAPI令牌是否有权限 3. 笔记是否已被删除'
                }
            elif '401' in error_msg or '403' in error_msg:
                return {'success': False, 'message': '权限不足，无法访问该笔记'}
            elif 'Connection' in error_msg or 'network' in error_msg.lower():
                return {'success': False, 'message': '无法连接到Trilium服务器，请检查网络和服务器状态'}
            else:
                return {'success': False, 'message': f'获取内容时发生错误: {error_msg}'}
    
    def get_note_content_by_kb_number(self, kb_number, kb_link=None):
        """通过知识库编号获取笔记内容（兼容原有接口）"""
        # 如果直接提供了Trilium链接，使用它
        if kb_link:
            return self.get_note_content_by_url(kb_link)
        
        # 否则，需要先从数据库查询记录获取链接
        # 此部分逻辑建议在路由层处理
        return {'success': False, 'message': '需要提供Trilium链接或KB编号对应的链接'}


# 以下函数用于保持与原有代码的兼容性
# 全局助手实例
_helper_instance = None

def get_trilium_helper():
    """获取全局TriliumHelper实例（单例模式）"""
    global _helper_instance
    if _helper_instance is None:
        _helper_instance = TriliumHelper()
    return _helper_instance

def test_connection():
    """测试连接（兼容原有接口）"""
    helper = get_trilium_helper()
    return helper.test_connection()

def get_note_content(note_id=None, trilium_url=None, kb_number=None):
    """获取笔记内容（兼容原有接口）"""
    helper = get_trilium_helper()
    
    if not helper.is_available():
        return {'success': False, 'message': 'Trilium客户端未初始化'}
    
    # 根据参数决定调用方式
    if trilium_url:
        return helper.get_note_content_by_url(trilium_url)
    elif note_id:
        # 假设note_id是直接可用的笔记ID
        try:
            content = helper.client.get_note_content(note_id)
            note_info = helper.client.get_note(note_id)
            return {
                'success': True,
                'note_id': note_id,
                'title': note_info.get('title', '无标题'),
                'content': content,
                'content_type': note_info.get('mime', 'text/html'),
                'modified': note_info.get('utcDateModified')
            }
        except Exception as e:
            return {'success': False, 'message': f'获取内容失败: {str(e)}'}
    else:
        return {'success': False, 'message': '需要提供笔记ID或Trilium链接'}

def extract_note_id_from_url(trilium_url):
    """从URL提取笔记ID（兼容函数）"""
    helper = get_trilium_helper()
    return helper.extract_note_id_from_url(trilium_url)

def fix_image_urls(content, base_url, note_id=None, use_proxy=True):
    """修复图片URL，将相对路径转换为绝对路径（Trilium 0.100.0专用）"""
    if not content or not base_url:
        return content
    
    import re
    from urllib.parse import urljoin
    
    print(f"DEBUG: 开始处理图片URL，base_url={base_url}, use_proxy={use_proxy}")
    
    # 确保base_url以/结尾
    if not base_url.endswith('/'):
        base_url = base_url + '/'
    
    def replace_img_src(match):
        img_tag = match.group(0)
        src_match = re.search(r'src="([^"]+)"', img_tag, re.IGNORECASE)
        
        if src_match:
            src = src_match.group(1)
            print(f"DEBUG: 找到图片src={src}")
            
            # 1. 如果已经是完整URL，不做处理
            if src.startswith(('http://', 'https://', 'data:')):
                print(f"DEBUG: 已经是完整URL，跳过处理")
                # 即使已经是完整URL，也通过代理避免CORS问题
                if use_proxy and src.startswith(('http://', 'https://')):
                    proxy_url = f"/api/image_proxy?url={quote_plus(src)}"
                    img_tag = img_tag.replace(f'src="{src}"', f'src="{proxy_url}"')
                return img_tag
            
            # 2. 处理Trilium的API附件路径
            # 格式: api/attachments/{noteId}/image/{filename} 或 api/attachments/{filename}
            full_url = None
            
            if src.startswith('api/attachments/'):
                # 构建完整的附件URL
                full_url = urljoin(base_url, src)
                print(f"DEBUG: 处理附件路径，生成URL: {full_url}")
            else:
                # 3. 处理其他相对路径
                full_url = urljoin(base_url, src)
                print(f"DEBUG: 处理相对路径，生成URL: {full_url}")
            
            # 使用代理访问图片
            if use_proxy and full_url:
                proxy_url = f"/api/image_proxy?url={quote_plus(full_url)}"
                img_tag = img_tag.replace(f'src="{src}"', f'src="{proxy_url}"')
                print(f"DEBUG: 使用代理URL: {proxy_url}")
            elif full_url:
                # 直接使用完整URL
                img_tag = img_tag.replace(f'src="{src}"', f'src="{full_url}"')
            
            # 添加CSS类以便样式控制
            if 'class=' not in img_tag:
                img_tag = img_tag.replace('<img', '<img class="trilium-image"')
            else:
                img_tag = img_tag.replace('class="', 'class="trilium-image ')
            
            # 添加加载失败处理
            img_tag = img_tag.replace('<img', '<img onerror="handleImageError(this)"')
            print(f"DEBUG: 处理后的img标签: {img_tag[:100]}...")
        
        return img_tag
    
    # 使用正则表达式替换所有img标签
    pattern = r'<img\b[^>]*>'
    result = re.sub(pattern, replace_img_src, content, flags=re.IGNORECASE)
    print(f"DEBUG: 图片处理完成")
    return result

def add_content_styles(content):
    """为内容添加基本样式（增强版）"""
    import re
    
    # 1. 为表格添加样式
    def style_table(match):
        table = match.group(0)
        # 检查是否已经有style属性
        if 'style=' not in table:
            table = table.replace('<table', '<table style="border-collapse: collapse; width: 100%; margin: 15px 0; border: 1px solid #dee2e6;"')
        return table
    
    def style_td_th(match):
        tag = match.group(0)
        tag_name = match.group(1)
        if 'style=' not in tag:
            if tag_name.lower() == 'th':
                style = 'border: 1px solid #dee2e6; padding: 12px; background-color: #343a40; color: white; font-weight: bold;'
            else:
                style = 'border: 1px solid #dee2e6; padding: 12px;'
            tag = tag.replace(f'<{tag_name}', f'<{tag_name} style="{style}"')
        return tag
    
    # 2. 为代码块添加黑色背景样式
    def style_pre(match):
        pre = match.group(0)
        # 检查是否已经有style属性
        if 'style=' not in pre:
            style = 'background-color: #2d2d2d; color: #f8f8f2; padding: 15px; border-radius: 5px; overflow-x: auto; font-family: "Consolas", "Monaco", "Courier New", monospace; font-size: 14px; line-height: 1.5; margin: 15px 0; border-left: 4px solid #007bff;'
            pre = pre.replace('<pre', f'<pre style="{style}"')
        return pre
    
    def style_code(match):
        code = match.group(0)
        # 检查是否在pre标签内（如果是，已经有黑色背景了）
        # 如果不是在pre标签内，添加内联代码样式
        if 'style=' not in code:
            style = 'background-color: #f8f9fa; color: #e83e8c; padding: 2px 6px; border-radius: 3px; font-family: "Consolas", "Monaco", "Courier New", monospace; font-size: 0.9em;'
            code = code.replace('<code', f'<code style="{style}"')
        return code
    
    # 3. 为引用块添加样式
    def style_blockquote(match):
        blockquote = match.group(0)
        if 'style=' not in blockquote:
            style = 'border-left: 4px solid #6c757d; padding: 10px 20px; margin: 15px 0; background-color: #f8f9fa; color: #6c757d; font-style: italic;'
            blockquote = blockquote.replace('<blockquote', f'<blockquote style="{style}"')
        return blockquote
    
    # 4. 应用样式
    content = re.sub(r'<table\b[^>]*>', style_table, content, flags=re.IGNORECASE)
    content = re.sub(r'<(t[dh])\b[^>]*>', style_td_th, content, flags=re.IGNORECASE)
    content = re.sub(r'<pre\b[^>]*>', style_pre, content, flags=re.IGNORECASE)
    content = re.sub(r'<code\b[^>]*>', style_code, content, flags=re.IGNORECASE)
    content = re.sub(r'<blockquote\b[^>]*>', style_blockquote, content, flags=re.IGNORECASE)
    
    return content

def format_content_for_display(content, content_type='text/html', base_url=None, note_id=None, use_proxy=True):
    """格式化内容用于显示（改进版本，支持HTML渲染）"""
    if not content:
        return "<div class='empty-content'><p>暂无内容</p></div>"
    
    # 检查是否是错误JSON响应
    if isinstance(content, str) and content.strip().startswith('{') and '"status"' in content:
        try:
            import json
            error_data = json.loads(content)
            if 'status' in error_data and error_data['status'] >= 400:
                error_msg = error_data.get('message', '未知API错误')
                return f"<div class='api-error alert alert-danger'><strong>API错误 {error_data.get('status')}:</strong> {error_msg}</div>"
        except:
            pass
    
    # 正常内容处理
    if content_type == 'text/html' or content_type.startswith('text/'):
        try:
            # 定义允许的HTML标签和属性
            allowed_tags = [
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'p', 'br', 'div', 'span',
                'strong', 'b', 'em', 'i', 'u', 's',
                'ul', 'ol', 'li',
                'table', 'thead', 'tbody', 'tr', 'th', 'td',
                'a', 'img',
                'pre', 'code',
                'blockquote', 'hr'
            ]
            
            allowed_attributes = {
                '*': ['class', 'style', 'id'],
                'a': ['href', 'title', 'target', 'rel'],
                'img': ['src', 'alt', 'title', 'width', 'height'],
                'table': ['border', 'cellpadding', 'cellspacing', 'width'],
            }
            
            # 清理HTML
            cleaned_content = bleach.clean(
                content,
                tags=allowed_tags,
                attributes=allowed_attributes,
                strip=True
            )
            
            # 处理图片路径
            if base_url:
                cleaned_content = fix_image_urls(cleaned_content, base_url, note_id, use_proxy)
            else:
                # 使用config中的默认服务器地址
                if hasattr(config, 'TRILIUM_SERVER_URL'):
                    cleaned_content = fix_image_urls(cleaned_content, config.TRILIUM_SERVER_URL, note_id, use_proxy)
            
            # 添加基本样式
            cleaned_content = add_content_styles(cleaned_content)
            
            return cleaned_content
            
        except Exception as e:
            print(f"HTML处理出错: {e}")
            # 出错时返回原始内容（但已转义）
            escaped = html.escape(content)
            escaped = escaped.replace('\n', '<br>')
            return f"<div class='trilium-html-content'>{escaped}</div>"
    else:
        # 非HTML内容，简单转义处理
        escaped = html.escape(content)
        escaped = escaped.replace('\n', '<br>')
        return f"<pre class='trilium-text-content' style='background-color: #2d2d2d; color: #f8f8f2; padding: 15px; border-radius: 5px;'>{escaped}</pre>"
    
    