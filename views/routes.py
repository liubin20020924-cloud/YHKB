"""
浏览与检索路由模块
包含首页浏览、搜索功能和Trilium内容集成
"""
import requests
from flask import Blueprint, render_template, request, jsonify, make_response, redirect, url_for, session
from database.db_utils import fetch_all_records, fetch_record_by_id, fetch_records_by_name, get_total_count, fetch_records_with_pagination, fetch_records_by_name_with_pagination
from trilium_helper import get_trilium_helper, format_content_for_display, test_connection as test_trilium_connection
from auth.utils import get_current_user
import config

# 创建视图蓝图
views_bp = Blueprint('views', __name__)

# 主页 - 展示所有数据（支持分页，需要登录）
@views_bp.route('/')
def index():
    """首页 - 需要登录才能访问"""
    # 检查登录状态
    user = get_current_user()
    if not user:
        from flask import session as flask_session
        flask_session.clear()
        return redirect(url_for('auth.login', next=request.url))
    try:
        # 获取分页参数，默认第1页，每页15条
        page = request.args.get('page', 1, type=int)
        per_page = 15

        # 分页查询记录
        records, total_count = fetch_records_with_pagination(page, per_page)

        # 计算分页信息
        total_pages = (total_count + per_page - 1) // per_page  # 向上取整
        showing_start = (page - 1) * per_page + 1
        showing_end = min(page * per_page, total_count)

        print(f"首页加载: 页码={page}, 总记录数={total_count}, 实际查询到={len(records)}, 总页数={total_pages}")

        return render_template('index.html',
                             records=records,
                             total_count=total_count,
                             showing_count=showing_end - showing_start + 1 if records else 0,
                             page=page,
                             per_page=per_page,
                             total_pages=total_pages,
                             showing_start=showing_start,
                             showing_end=showing_end,
                             is_search=False,
                             trilium_base_url=config.TRILIUM_BASE_URL,
                             current_user=user)
    except Exception as e:
        error_msg = f"数据库连接错误: {str(e)}"
        print(f"首页错误: {error_msg}")
        return render_template('index.html',
                             records=[],
                             error=error_msg,
                             total_count=0,
                             showing_count=0,
                             page=1,
                             per_page=15,
                             total_pages=1,
                             is_search=False,
                             current_user=user)

# 搜索接口 - 根据主键搜索
@views_bp.route('/search', methods=['GET'])
def search():
    search_id = request.args.get('id', '').strip()
    page = request.args.get('page', 1, type=int)

    print(f"搜索请求: id={search_id}, page={page}")

    if not search_id:
        print("没有提供搜索ID，重定向到首页")
        return render_template('index.html',
                             records=[],
                             error="请输入搜索ID",
                             total_count=get_total_count(),
                             showing_count=0,
                             page=1,
                             per_page=15,
                             total_pages=1,
                             is_search=True,
                             search_id="")

    try:
        record_id = int(search_id)
        print(f"搜索ID: {record_id}")

        record = fetch_record_by_id(record_id)
        print(f"查询结果: {record}")

        if record:
            return render_template('index.html',
                                 records=[record],
                                 total_count=1,
                                 showing_count=1,
                                 page=page,
                                 per_page=15,
                                 total_pages=1,
                                 search_id=search_id,
                                 is_search=True)
        else:
            error_msg = f"未找到ID为 {search_id} 的记录"
            print(f"搜索失败: {error_msg}")
            return render_template('index.html',
                                 records=[],
                                 error=error_msg,
                                 total_count=get_total_count(),
                                 showing_count=0,
                                 page=1,
                                 per_page=15,
                                 total_pages=1,
                             search_id=search_id,
                             is_search=True)

    except ValueError:
        error_msg = "请输入有效的数字ID"
        print(f"搜索值错误: {error_msg}")
        return render_template('index.html',
                             records=[],
                             error=error_msg,
                             total_count=get_total_count(),
                             showing_count=0,
                             page=1,
                             per_page=15,
                             total_pages=1,
                             search_id=search_id,
                             is_search=True)
    except Exception as e:
        error_msg = f"搜索过程中发生错误: {str(e)}"
        print(f"搜索异常: {error_msg}")
        return render_template('index.html',
                             records=[],
                             error=error_msg,
                             total_count=get_total_count(),
                             showing_count=0,
                             page=1,
                             per_page=15,
                             total_pages=1,
                             search_id=search_id,
                             is_search=True)

# 获取所有数据接口（用于AJAX）
@views_bp.route('/api/all')
def get_all():
    try:
        records = fetch_all_records()
        return jsonify({
            'success': True,
            'records': records,
            'count': len(records)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"数据库错误: {str(e)}"
        })

# 按名称搜索接口
@views_bp.route('/search/name', methods=['POST'])
def search_by_name():
    name = request.form.get('name', '').strip()
    page = request.form.get('page', 1, type=int)
    per_page = request.form.get('per_page', 15, type=int)

    print(f"按名称搜索: {name}, page={page}")

    if not name:
        return jsonify({'success': False, 'message': '请输入知识库名称'})

    try:
        records, total_count = fetch_records_by_name_with_pagination(name, page, per_page)
        total_pages = (total_count + per_page - 1) // per_page
        return jsonify({
            'success': True,
            'records': records,
            'count': len(records),
            'total_count': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"搜索错误: {str(e)}"
        })

# 统计信息接口
@views_bp.route('/api/stats')
def get_stats():
    try:
        count = get_total_count()
        return jsonify({
            'success': True,
            'total_count': count
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"统计信息获取失败: {str(e)}"
        })

# 获取Trilium笔记内容（基于trilium-py重构）
@views_bp.route('/api/trilium/content')
def get_trilium_content():
    """获取Trilium笔记内容"""
    if not config.ENABLE_CONTENT_VIEW:
        return jsonify({
            'success': False,
            'message': '内容查看功能未启用'
        })
    
    note_id = request.args.get('note_id')
    trilium_url = request.args.get('trilium_url')
    kb_number = request.args.get('kb_number')
    
    print(f"Trilium内容请求: note_id={note_id}, trilium_url={trilium_url[:80] if trilium_url else None}..., kb_number={kb_number}")
    
    # 如果提供了KB编号，查找对应的记录获取链接
    if kb_number and not trilium_url:
        try:
            record = fetch_record_by_id(int(kb_number))
            if record and record.get('KB_link'):
                trilium_url = record['KB_link']
                print(f"通过KB编号 {kb_number} 找到链接: {trilium_url[:80]}...")
            else:
                print(f"未找到KB编号 {kb_number} 对应的记录或记录无链接")
        except ValueError:
            print(f"KB编号格式错误: {kb_number}")
            return jsonify({
                'success': False,
                'message': '知识库编号格式不正确'
            })
        except Exception as e:
            print(f"通过KB编号查询记录失败: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'查找知识库记录失败: {str(e)}'
            })
    
    # 验证输入参数
    if not note_id and not trilium_url:
        return jsonify({
            'success': False,
            'message': '需要提供笔记ID或Trilium链接'
        })
    
    try:
        # 获取Trilium帮助器实例
        helper = get_trilium_helper()
        
        # 检查客户端是否可用
        if not helper.is_available():
            error_msg = 'Trilium客户端未正确初始化，请检查服务器配置和令牌'
            print(error_msg)
            return jsonify({
                'success': False,
                'message': error_msg
            })
        
        # 根据参数类型调用不同的获取方式
        if trilium_url:
            print(f"通过URL获取内容: {trilium_url[:80]}...")
            result = helper.get_note_content_by_url(trilium_url)
        else:
            print(f"直接通过笔记ID获取内容: {note_id}")
            # 对于直接提供的note_id，我们使用helper的通用方法
            # 这里假设note_id已经是有效的笔记ID
            result = get_trilium_helper().get_note_content(
                note_id=note_id, 
                trilium_url=None, 
                kb_number=kb_number
            )
        
        print(f"内容获取结果: 成功={result.get('success')}, 消息={result.get('message', '无消息')}")
        
        if result.get('success') and result.get('content') is not None:
            # 格式化内容用于显示
            content = format_content_for_display(
                result.get('content', ''),
                result.get('content_type', 'text/html'),
                base_url=config.TRILIUM_SERVER_URL,
                note_id=result.get('note_id'),
                use_proxy=True  # 启用图片代理
            )
            
            response_data = {
                'success': True,
                'title': result.get('title', '无标题'),
                'content': content,
                'note_id': result.get('note_id'),
                'type': result.get('type', 'text')
            }
            
            # 可选字段：只有存在时才添加
            if result.get('created'):
                response_data['created'] = result.get('created')
            if result.get('modified'):
                response_data['modified'] = result.get('modified')
            
            return jsonify(response_data)
        else:
            # 直接返回错误信息
            error_message = result.get('message', '未知错误')
            print(f"获取内容失败: {error_message}")
            return jsonify({
                'success': False,
                'message': error_message
            })
            
    except Exception as e:
        error_msg = f'获取Trilium内容时发生异常: {str(e)}'
        print(error_msg)
        return jsonify({
            'success': False,
            'message': error_msg
        })

# 图片代理接口 - 解决跨域和认证问题
from trilium_session import get_trilium_session_manager

# 图片代理接口 - 使用会话登录方式
@views_bp.route('/api/image_proxy')
def image_proxy():
    """图片代理，通过Trilium会话直接访问附件"""
    url = request.args.get('url')
    if not url:
        return jsonify({'success': False, 'message': '缺少图片URL参数'}), 400
    
    try:
        print(f"图片代理请求: {url[:100]}...")
        
        # 解析URL
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        
        # 检查是否是Trilium附件URL
        if parsed_url.netloc != config.TRILIUM_SERVER_HOST:
            return jsonify({
                'success': False,
                'message': f'不支持的URL域名: {parsed_url.netloc}'
            }), 400
        
        if not parsed_url.path.startswith('/api/attachments/'):
            return jsonify({
                'success': False, 
                'message': f'不是Trilium附件URL: {parsed_url.path}'
            }), 400
        
        # 提取附件路径
        attachment_path = parsed_url.path.replace('/api/attachments/', '')
        print(f"附件路径: {attachment_path}")
        
        # 获取会话管理器
        session_manager = get_trilium_session_manager()
        
        # 如果配置了登录凭据，尝试登录
        if (hasattr(config, 'TRILIUM_LOGIN_USERNAME') and 
            hasattr(config, 'TRILIUM_LOGIN_PASSWORD') and
            config.TRILIUM_LOGIN_USERNAME and 
            config.TRILIUM_LOGIN_PASSWORD):
            
            # 确保有有效的会话
            if not session_manager.is_session_valid():
                print("会话无效，尝试登录...")
                if not session_manager.login(
                    config.TRILIUM_LOGIN_USERNAME, 
                    config.TRILIUM_LOGIN_PASSWORD
                ):
                    return jsonify({
                        'success': False, 
                        'message': 'Trilium登录失败'
                    }), 401
        else:
            # 如果没有配置登录凭据，创建匿名会话
            if not session_manager.session:
                session_manager.session = requests.Session()
        
        # 使用会话获取附件
        if session_manager.session:
            try:
                response = session_manager.session.get(
                    url,
                    timeout=10,
                    stream=True
                )
                
                if response.status_code == 200:
                    # 创建Flask响应
                    flask_response = make_response(response.content)
                    
                    # 设置正确的Content-Type
                    content_type = response.headers.get('Content-Type', 'image/png')
                    flask_response.headers.set('Content-Type', content_type)
                    
                    # 设置缓存控制和跨域头
                    flask_response.headers.set('Cache-Control', 'public, max-age=86400')
                    flask_response.headers.set('Access-Control-Allow-Origin', '*')
                    
                    print(f"✅ 成功获取图片，大小: {len(response.content)} 字节")
                    return flask_response
                else:
                    print(f"图片请求失败: {response.status_code}")
                    
                    # 如果返回401，可能是会话过期
                    if response.status_code == 401 and hasattr(config, 'TRILIUM_LOGIN_USERNAME'):
                        print("会话可能过期，尝试重新登录...")
                        # 尝试重新登录
                        if session_manager.login(
                            config.TRILIUM_LOGIN_USERNAME, 
                            config.TRILIUM_LOGIN_PASSWORD
                        ):
                            # 重试请求
                            response = session_manager.session.get(url, timeout=10, stream=True)
                            if response.status_code == 200:
                                flask_response = make_response(response.content)
                                content_type = response.headers.get('Content-Type', 'image/png')
                                flask_response.headers.set('Content-Type', content_type)
                                flask_response.headers.set('Cache-Control', 'public, max-age=86400')
                                flask_response.headers.set('Access-Control-Allow-Origin', '*')
                                return flask_response
                    
                    return jsonify({
                        'success': False, 
                        'message': f'图片加载失败: {response.status_code}'
                    }), response.status_code
                    
            except Exception as e:
                print(f"使用会话获取图片失败: {e}")
                return jsonify({
                    'success': False, 
                    'message': f'图片代理错误: {str(e)}'
                }), 500
        else:
            return jsonify({
                'success': False, 
                'message': '无法创建Trilium会话'
            }), 500
            
    except Exception as e:
        print(f"图片代理错误: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'图片代理错误: {str(e)}'
        }), 500


# 搜索Trilium笔记
@views_bp.route('/api/trilium/search')
def search_trilium_notes():
    """搜索Trilium笔记"""
    if not config.ENABLE_CONTENT_VIEW:
        return jsonify({
            'success': False,
            'message': '内容查看功能未启用'
        })
    
    keyword = request.args.get('q', '').strip()
    limit = request.args.get('limit', 30, type=int)
    
    print(f"Trilium笔记搜索: 关键词='{keyword}', 限制={limit}")
    
    if not keyword:
        return jsonify({
            'success': False,
            'message': '请输入搜索关键词'
        })
    
    try:
        helper = get_trilium_helper()
        if not helper.is_available():
            return jsonify({
                'success': False,
                'message': 'Trilium客户端未正确初始化'
            })
        
        # 使用 trilium-py 客户端的搜索功能
        client = helper.client
        search_results = client.search_note(
            search=keyword,
            limit=limit
        )
        
        print(f"搜索返回结果数: {len(search_results.get('results', [])) if search_results else 0}")
        
        if search_results and 'results' in search_results and search_results['results']:
            # 格式化结果
            formatted_results = []
            for note in search_results['results']:
                formatted_results.append({
                    'noteId': note.get('noteId'),
                    'title': note.get('title', '无标题'),
                    'type': note.get('type', 'text'),
                    'dateModified': note.get('dateModified'),
                    'mime': note.get('mime')
                })
            
            return jsonify({
                'success': True,
                'results': formatted_results,
                'count': len(formatted_results),
                'message': f'找到 {len(formatted_results)} 条相关笔记'
            })
        else:
            return jsonify({
                'success': True,
                'results': [],
                'count': 0,
                'message': f'未找到包含"{keyword}"的笔记'
            })
            
    except Exception as e:
        error_msg = f'搜索Trilium笔记失败: {str(e)}'
        print(error_msg)
        return jsonify({
            'success': False,
            'message': error_msg
        })

# 批量获取Trilium内容（用于前端优化）
@views_bp.route('/api/trilium/batch-content', methods=['POST'])
def get_batch_trilium_content():
    """批量获取多个Trilium笔记内容"""
    if not config.ENABLE_CONTENT_VIEW:
        return jsonify({
            'success': False,
            'message': '内容查看功能未启用'
        })
    
    try:
        data = request.get_json()
        note_urls = data.get('urls', [])
        
        if not note_urls:
            return jsonify({
                'success': False,
                'message': '未提供笔记URL列表'
            })
        
        print(f"批量获取内容，数量: {len(note_urls)}")
        
        helper = get_trilium_helper()
        if not helper.is_available():
            return jsonify({
                'success': False,
                'message': 'Trilium客户端未正确初始化'
            })
        
        results = []
        success_count = 0
        fail_count = 0
        
        for url in note_urls:
            try:
                result = helper.get_note_content_by_url(url)
                results.append({
                    'url': url,
                    'success': result.get('success', False),
                    'title': result.get('title', ''),
                    'note_id': result.get('note_id'),
                    'message': result.get('message', '')
                })
                
                if result.get('success'):
                    success_count += 1
                else:
                    fail_count += 1
                    
            except Exception as e:
                results.append({
                    'url': url,
                    'success': False,
                    'title': '',
                    'note_id': None,
                    'message': f'处理失败: {str(e)}'
                })
                fail_count += 1
        
        return jsonify({
            'success': True,
            'results': results,
            'summary': {
                'total': len(note_urls),
                'success': success_count,
                'failed': fail_count
            }
        })
        
    except Exception as e:
        error_msg = f'批量获取内容失败: {str(e)}'
        print(error_msg)
        return jsonify({
            'success': False,
            'message': error_msg
        })