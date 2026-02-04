#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tapnow Studio 本地接收器
用于接收浏览器发送的文件保存请求，实现本地文件操作

使用方法：
1. 运行此脚本：python tapnow-local-server.py
2. 在 Tapnow Studio 中使用"保存到本地"节点
3. 文件将保存到指定的本地路径

端口：9527（可通过命令行参数修改）
"""

import os
import sys
import json
import base64
import argparse
import threading
import webbrowser
import http.client
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote, parse_qs
from datetime import datetime
from io import BytesIO

# 尝试导入PIL用于图片格式转换
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("[警告] PIL未安装，PNG转JPG功能不可用。安装方法: pip install Pillow")

# 默认配置
DEFAULT_PORT = 9527
DEFAULT_SAVE_PATH = os.path.expanduser("~/Downloads/TapnowStudio")
DEFAULT_ALLOWED_ROOTS = [
    os.path.expanduser("~/Downloads"),
    os.path.abspath(r"D:\TapnowData")
]
DEFAULT_PROXY_ALLOWED_HOSTS = [
    "api.openai.com",
    "generativelanguage.googleapis.com",
    "ai.comfly.chat",
    "api-inference.modelscope.cn",
    "vibecodingapi.ai",
    "yunwu.ai",
    "muse-ai.oss-cn-hangzhou.aliyuncs.com",
    "googlecdn.datas.systems"
]
DEFAULT_PROXY_TIMEOUT = 300
CONFIG_FILENAME = "tapnow-local-config.json"

# 全局配置
config = {
    "port": DEFAULT_PORT,
    "save_path": DEFAULT_SAVE_PATH,
    "image_save_path": "",  # 图片自定义保存路径（空则使用save_path）
    "video_save_path": "",  # 视频自定义保存路径（空则使用save_path）
    "allowed_roots": DEFAULT_ALLOWED_ROOTS,
    "proxy_allowed_hosts": DEFAULT_PROXY_ALLOWED_HOSTS,
    "proxy_timeout": DEFAULT_PROXY_TIMEOUT,
    "auto_create_dir": True,
    "allow_overwrite": False,
    "log_enabled": True,
    "convert_png_to_jpg": True,  # PNG转JPG（高质量）
    "jpg_quality": 95  # JPG质量（1-100）
}

def log(message):
    """日志输出"""
    if config["log_enabled"]:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

def load_config_file():
    """加载本地配置文件（可选）"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILENAME)
    if not os.path.exists(config_path):
        return
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as exc:
        print(f"[警告] 读取配置文件失败: {config_path} ({exc})")
        return
    allowed_roots = data.get("allowed_roots")
    if allowed_roots is not None:
        if isinstance(allowed_roots, list) and all(isinstance(p, str) and p.strip() for p in allowed_roots):
            config["allowed_roots"] = allowed_roots
            log(f"允许目录已更新: {', '.join(allowed_roots)}")
        else:
            print("[警告] 配置文件 allowed_roots 需要是非空字符串数组，已忽略")

    proxy_allowed_hosts = data.get("proxy_allowed_hosts")
    if proxy_allowed_hosts is not None:
        if isinstance(proxy_allowed_hosts, list) and all(isinstance(h, str) for h in proxy_allowed_hosts):
            config["proxy_allowed_hosts"] = proxy_allowed_hosts
            if proxy_allowed_hosts:
                log(f"代理允许域名已更新: {', '.join(proxy_allowed_hosts)}")
            else:
                log("代理允许域名已清空")
        else:
            print("[警告] 配置文件 proxy_allowed_hosts 需要是字符串数组，已忽略")

    proxy_timeout = data.get("proxy_timeout")
    if proxy_timeout is not None:
        try:
            proxy_timeout = int(proxy_timeout)
            if proxy_timeout < 0:
                raise ValueError("timeout must be >= 0")
            config["proxy_timeout"] = proxy_timeout
            log(f"代理超时已更新: {proxy_timeout}s")
        except Exception:
            print("[警告] 配置文件 proxy_timeout 需要是非负整数，已忽略")

def ensure_dir(path):
    """确保目录存在"""
    if not os.path.exists(path):
        os.makedirs(path)
        log(f"创建目录: {path}")

def get_allowed_roots():
    """获取允许的根目录"""
    if sys.platform == 'win32':
        return config.get("allowed_roots", DEFAULT_ALLOWED_ROOTS)
    return [config["save_path"]]

def normalize_rel_path(rel_path):
    """规范化相对路径，防止路径穿越"""
    rel_path = unquote(rel_path or "")
    rel_path = rel_path.replace('\\', '/').lstrip('/')
    if not rel_path:
        return ""
    norm = os.path.normpath(rel_path)
    if norm.startswith("..") or os.path.isabs(norm):
        return None
    return norm.replace('/', os.sep)

def is_path_allowed(path):
    """检查路径是否在允许的根目录内"""
    path_abs = os.path.abspath(os.path.expanduser(path))
    path_norm = os.path.normcase(path_abs)
    for root in get_allowed_roots():
        root_abs = os.path.abspath(os.path.expanduser(root))
        root_norm = os.path.normcase(root_abs)
        try:
            if os.path.commonpath([path_norm, root_norm]) == root_norm:
                return True
        except ValueError:
            continue
    return False

def safe_join(base, rel_path):
    """安全拼接路径，防止穿越"""
    rel_norm = normalize_rel_path(rel_path)
    if rel_norm is None:
        return None
    base_abs = os.path.abspath(base)
    candidate = os.path.abspath(os.path.join(base_abs, rel_norm))
    base_norm = os.path.normcase(base_abs)
    cand_norm = os.path.normcase(candidate)
    try:
        if os.path.commonpath([cand_norm, base_norm]) != base_norm:
            return None
    except ValueError:
        return None
    return candidate

PROXY_SKIP_REQUEST_HEADERS = {
    'host', 'content-length', 'connection', 'proxy-connection', 'keep-alive',
    'transfer-encoding', 'te', 'trailer', 'upgrade', 'proxy-authorization',
    'proxy-authenticate', 'x-proxy-target', 'x-proxy-method'
}
PROXY_SKIP_RESPONSE_HEADERS = {
    'connection', 'proxy-connection', 'keep-alive', 'transfer-encoding', 'te',
    'trailer', 'upgrade', 'proxy-authenticate', 'proxy-authorization',
    'access-control-allow-origin', 'access-control-allow-methods',
    'access-control-allow-headers', 'access-control-expose-headers'
}

def parse_proxy_target(parsed, headers):
    """从请求中解析代理目标URL"""
    target = headers.get('X-Proxy-Target')
    if not target:
        params = parse_qs(parsed.query or '')
        target = params.get('url', [None])[0] or params.get('target', [None])[0]
    if not target:
        return None
    return unquote(target)

def parse_allowed_host_entry(entry):
    """解析允许的域名配置项"""
    entry = entry.strip()
    if not entry:
        return None, None, False
    if entry == '*':
        return '*', None, False
    wildcard = False
    if entry.startswith('*.'):
        wildcard = True
        entry = entry[2:]
    if '://' in entry:
        parsed = urlparse(entry)
    else:
        parsed = urlparse('//' + entry)
    host = parsed.hostname.lower() if parsed.hostname else None
    return host, parsed.port, wildcard

def is_proxy_target_allowed(target_url):
    """检查代理目标是否允许"""
    allowed_hosts = config.get("proxy_allowed_hosts", [])
    if not allowed_hosts:
        return False
    parsed = urlparse(target_url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    for entry in allowed_hosts:
        if entry is None:
            continue
        host_entry, port_entry, wildcard = parse_allowed_host_entry(str(entry))
        if not host_entry:
            continue
        if host_entry == '*':
            return True
        if wildcard:
            if host == host_entry:
                continue
            if host.endswith('.' + host_entry):
                if port_entry is None or port_entry == port:
                    return True
        else:
            if host == host_entry and (port_entry is None or port_entry == port):
                return True
    return False

def iter_proxy_response_chunks(response, chunk_size=8192):
    """按块读取代理响应，支持流式"""
    if response.fp and hasattr(response.fp, 'read1'):
        while True:
            chunk = response.fp.read1(chunk_size)
            if not chunk:
                break
            yield chunk
        return
    while True:
        chunk = response.read(chunk_size)
        if not chunk:
            break
        yield chunk

def get_unique_filename(filepath):
    """获取唯一文件名（避免覆盖）"""
    if not os.path.exists(filepath):
        return filepath
    
    base, ext = os.path.splitext(filepath)
    counter = 1
    while os.path.exists(f"{base}_{counter}{ext}"):
        counter += 1
    return f"{base}_{counter}{ext}"

def convert_png_to_jpg(png_data, quality=95):
    """将PNG数据转换为高质量JPG"""
    if not PIL_AVAILABLE:
        return png_data, False
    
    try:
        img = Image.open(BytesIO(png_data))
        # 如果有透明通道，转换为RGB（白色背景）
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 保存为高质量JPG
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        return output.getvalue(), True
    except Exception as e:
        log(f"PNG转JPG失败: {str(e)}")
        return png_data, False

def is_image_file(filename):
    """判断是否为图片文件"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']

def is_video_file(filename):
    """判断是否为视频文件"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ['.mp4', '.mov', '.webm', '.avi', '.mkv']

class TapnowHandler(BaseHTTPRequestHandler):
    """HTTP请求处理器"""
    
    def log_message(self, format, *args):
        """重写日志方法"""
        if config["log_enabled"]:
            log(f"HTTP: {args[0]}")
    
    def send_cors_headers(self):
        """发送CORS头，允许跨域请求"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD')
        req_headers = self.headers.get('Access-Control-Request-Headers')
        if req_headers:
            self.send_header('Access-Control-Allow-Headers', req_headers)
        else:
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Requested-With, Authorization, X-Proxy-Target')
        self.send_header('Access-Control-Max-Age', '86400')
    
    def send_json_response(self, data, status=200):
        """发送JSON响应"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_cors_headers()
        self.end_headers()
        response = json.dumps(data, ensure_ascii=False)
        self.wfile.write(response.encode('utf-8'))

    def handle_proxy(self, parsed):
        """代理请求"""
        target_url = parse_proxy_target(parsed, self.headers)
        if not target_url:
            self.send_json_response({"success": False, "error": "缺少目标URL"}, 400)
            return
        parsed_target = urlparse(target_url)
        if parsed_target.scheme not in ('http', 'https') or not parsed_target.hostname:
            self.send_json_response({"success": False, "error": "非法目标URL"}, 400)
            return
        if not is_proxy_target_allowed(target_url):
            self.send_json_response({"success": False, "error": "目标域名不在允许列表"}, 403)
            return

        method = self.command
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        forward_headers = {}
        for key, value in self.headers.items():
            lower = key.lower()
            if lower in PROXY_SKIP_REQUEST_HEADERS:
                continue
            if lower in ('origin', 'referer'):
                continue
            forward_headers[key] = value
        if parsed_target.netloc:
            forward_headers['Host'] = parsed_target.netloc

        path = parsed_target.path or '/'
        if parsed_target.query:
            path = f"{path}?{parsed_target.query}"

        port = parsed_target.port or (443 if parsed_target.scheme == 'https' else 80)
        conn_class = http.client.HTTPSConnection if parsed_target.scheme == 'https' else http.client.HTTPConnection
        timeout_value = config.get("proxy_timeout", DEFAULT_PROXY_TIMEOUT)
        timeout_value = None if timeout_value == 0 else timeout_value
        try:
            conn = conn_class(parsed_target.hostname, port, timeout=timeout_value)
            conn.request(method, path, body=body, headers=forward_headers)
            resp = conn.getresponse()
        except Exception as exc:
            log(f"代理请求失败: {exc}")
            self.send_json_response({"success": False, "error": f"代理请求失败: {exc}"}, 502)
            try:
                conn.close()
            except Exception:
                pass
            return

        try:
            self.send_response(resp.status, resp.reason)
            for header, value in resp.getheaders():
                lower = header.lower()
                if lower in PROXY_SKIP_RESPONSE_HEADERS:
                    continue
                self.send_header(header, value)
            self.send_cors_headers()
            self.end_headers()

            if method == 'HEAD':
                return

            for chunk in iter_proxy_response_chunks(resp):
                self.wfile.write(chunk)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            resp.close()
            conn.close()

    def do_OPTIONS(self):
        """处理预检请求"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """处理GET请求"""
        parsed = urlparse(self.path)

        if parsed.path in ('/proxy', '/proxy/'):
            self.handle_proxy(parsed)
            return

        if parsed.path == '/ping' or parsed.path == '/status':
            # 健康检查/状态接口
            self.send_json_response({
                "status": "running",
                "version": "1.1.0",
                "save_path": config["save_path"],
                "image_save_path": config["image_save_path"] or config["save_path"],
                "video_save_path": config["video_save_path"] or config["save_path"],
                "image_save_path_raw": config["image_save_path"],
                "video_save_path_raw": config["video_save_path"],
                "port": config["port"],
                "pil_available": PIL_AVAILABLE,
                "convert_png_to_jpg": config["convert_png_to_jpg"]
            })
        
        elif parsed.path == '/config':
            # 获取配置
            self.send_json_response({
                "save_path": config["save_path"],
                "image_save_path": config["image_save_path"] or config["save_path"],
                "video_save_path": config["video_save_path"] or config["save_path"],
                "image_save_path_raw": config["image_save_path"],
                "video_save_path_raw": config["video_save_path"],
                "auto_create_dir": config["auto_create_dir"],
                "allow_overwrite": config["allow_overwrite"],
                "convert_png_to_jpg": config["convert_png_to_jpg"],
                "jpg_quality": config["jpg_quality"],
                "proxy_allowed_hosts": config.get("proxy_allowed_hosts", []),
                "proxy_timeout": config.get("proxy_timeout", DEFAULT_PROXY_TIMEOUT),
                "pil_available": PIL_AVAILABLE
            })
        
        elif parsed.path == '/browse':
            # 打开保存目录
            save_path = config["save_path"]
            if os.path.exists(save_path):
                if sys.platform == 'win32':
                    os.startfile(save_path)
                elif sys.platform == 'darwin':
                    os.system(f'open "{save_path}"')
                else:
                    os.system(f'xdg-open "{save_path}"')
                self.send_json_response({"success": True, "message": "已打开目录"})
            else:
                self.send_json_response({"success": False, "message": "目录不存在"}, 404)

        elif parsed.path == '/pick-path':
            # 打开系统目录选择器，返回绝对路径
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                try:
                    root.attributes('-topmost', True)
                except Exception:
                    pass
                path = filedialog.askdirectory()
                root.destroy()
                if path:
                    self.send_json_response({"success": True, "path": path})
                else:
                    self.send_json_response({"success": False, "message": "用户取消选择"})
            except Exception as exc:
                self.send_json_response({"success": False, "message": "无法打开目录选择器", "error": str(exc)}, 500)
        
        elif parsed.path == '/list-files':
            # 列出本地保存的所有文件（用于导入时匹配本地文件）
            save_path = config["save_path"]
            if not os.path.exists(save_path):
                self.send_json_response({"success": True, "files": []})
                return
            
            files = []
            for root, dirs, filenames in os.walk(save_path):
                for filename in filenames:
                    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mov', '.webm')):
                        filepath = os.path.join(root, filename)
                        rel_path = os.path.relpath(filepath, save_path)
                        # 返回文件信息，包括可访问的本地URL
                        files.append({
                            "filename": filename,
                            "path": filepath.replace('\\', '/'),
                            "rel_path": rel_path.replace('\\', '/'),
                            "size": os.path.getsize(filepath),
                            "mtime": os.path.getmtime(filepath)
                        })
            
            self.send_json_response({"success": True, "files": files, "base_path": save_path.replace('\\', '/')})
        
        elif parsed.path.startswith('/file/'):
            # 提供本地文件访问（用于在浏览器中显示本地图片/视频）
            try:
                # 从路径中提取文件相对路径
                rel_path = parsed.path[6:]  # 去掉 '/file/' 前缀
                rel_path = normalize_rel_path(rel_path)
                if not rel_path:
                    self.send_json_response({"error": "非法路径"}, 400)
                    return
                
                # 尝试多个可能的路径：save_path, video_save_path, image_save_path
                filepath = None
                possible_paths = [
                    os.path.join(config["save_path"], rel_path),
                ]
                # 如果设置了视频保存路径，也尝试在那里查找
                if config["video_save_path"]:
                    possible_paths.append(os.path.join(config["video_save_path"], rel_path))
                # 如果设置了图片保存路径，也尝试在那里查找
                if config["image_save_path"]:
                    possible_paths.append(os.path.join(config["image_save_path"], rel_path))
                
                for path in possible_paths:
                    if os.path.exists(path):
                        filepath = path
                        break
                
                if not filepath:
                    self.send_json_response({"error": "文件不存在"}, 404)
                    return
                
                # 确定MIME类型
                ext = os.path.splitext(filepath)[1].lower()
                mime_types = {
                    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                    '.png': 'image/png', '.gif': 'image/gif',
                    '.webp': 'image/webp', '.mp4': 'video/mp4',
                    '.mov': 'video/quicktime', '.webm': 'video/webm'
                }
                mime_type = mime_types.get(ext, 'application/octet-stream')
                
                # 读取并发送文件
                with open(filepath, 'rb') as f:
                    file_data = f.read()
                
                self.send_response(200)
                self.send_header('Content-Type', mime_type)
                self.send_header('Content-Length', len(file_data))
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(file_data)
            except Exception as e:
                log(f"读取文件失败: {str(e)}")
                self.send_json_response({"error": str(e)}, 500)
        
        else:
            self.send_json_response({"error": "未知接口"}, 404)
    
    def do_HEAD(self):
        """处理HEAD请求 - 用于检查文件是否存在"""
        parsed = urlparse(self.path)

        if parsed.path in ('/proxy', '/proxy/'):
            self.handle_proxy(parsed)
            return

        if parsed.path.startswith('/file/'):
            try:
                # 从路径中提取文件相对路径
                rel_path = parsed.path[6:]  # 去掉 '/file/' 前缀
                rel_path = normalize_rel_path(rel_path)
                if not rel_path:
                    self.send_response(400)
                    self.send_cors_headers()
                    self.end_headers()
                    return
                
                # 尝试多个可能的路径
                filepath = None
                possible_paths = [
                    os.path.join(config["save_path"], rel_path),
                ]
                if config["video_save_path"]:
                    possible_paths.append(os.path.join(config["video_save_path"], rel_path))
                if config["image_save_path"]:
                    possible_paths.append(os.path.join(config["image_save_path"], rel_path))
                
                for path in possible_paths:
                    if os.path.exists(path):
                        filepath = path
                        break
                
                if not filepath:
                    self.send_response(404)
                    self.send_cors_headers()
                    self.end_headers()
                    return
                
                # 获取文件大小和MIME类型
                file_size = os.path.getsize(filepath)
                ext = os.path.splitext(filepath)[1].lower()
                mime_types = {
                    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                    '.png': 'image/png', '.gif': 'image/gif',
                    '.webp': 'image/webp', '.mp4': 'video/mp4',
                    '.mov': 'video/quicktime', '.webm': 'video/webm'
                }
                mime_type = mime_types.get(ext, 'application/octet-stream')
                
                self.send_response(200)
                self.send_header('Content-Type', mime_type)
                self.send_header('Content-Length', file_size)
                self.send_cors_headers()
                self.end_headers()
            except Exception as e:
                self.send_response(500)
                self.send_cors_headers()
                self.end_headers()
        else:
            self.send_response(404)
            self.send_cors_headers()
            self.end_headers()
    
    def do_POST(self):
        """处理POST请求"""
        parsed = urlparse(self.path)

        if parsed.path in ('/proxy', '/proxy/'):
            self.handle_proxy(parsed)
            return

        # 读取请求体
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            self.send_json_response({"success": False, "error": "无效的JSON数据"}, 400)
            return
        
        if parsed.path == '/save':
            # 保存文件
            self.handle_save(data)
        
        elif parsed.path == '/save-batch':
            # 批量保存文件
            self.handle_batch_save(data)
        
        elif parsed.path == '/config':
            # 更新配置
            self.handle_update_config(data)
        
        elif parsed.path == '/save-thumbnail':
            # 保存缩略图（用于历史记录和角色库缓存）
            self.handle_save_thumbnail(data)
        
        elif parsed.path == '/save-cache':
            # 保存缓存文件（用于角色库等）
            self.handle_save_cache(data)
        
        elif parsed.path == '/delete-file':
            # 删除本地文件
            self.handle_delete_file(data)
        
        elif parsed.path == '/delete-batch':
            # 批量删除本地文件
            log(f"[删除] 收到批量删除请求: {data}")
            self.handle_delete_batch(data)
        
        else:
            self.send_json_response({"error": "未知接口"}, 404)

    def do_PUT(self):
        """处理PUT请求（代理）"""
        parsed = urlparse(self.path)
        if parsed.path in ('/proxy', '/proxy/'):
            self.handle_proxy(parsed)
            return
        self.send_json_response({"error": "未知接口"}, 404)

    def do_PATCH(self):
        """处理PATCH请求（代理）"""
        parsed = urlparse(self.path)
        if parsed.path in ('/proxy', '/proxy/'):
            self.handle_proxy(parsed)
            return
        self.send_json_response({"error": "未知接口"}, 404)

    def do_DELETE(self):
        """处理DELETE请求（代理）"""
        parsed = urlparse(self.path)
        if parsed.path in ('/proxy', '/proxy/'):
            self.handle_proxy(parsed)
            return
        self.send_json_response({"error": "未知接口"}, 404)
    
    def handle_save(self, data):
        """处理单个文件保存"""
        try:
            # 获取参数
            filename = data.get('filename', '')
            content = data.get('content', '')  # base64编码的内容
            url = data.get('url', '')  # 或者直接传URL
            subfolder = data.get('subfolder', '')  # 子文件夹
            custom_path = data.get('path', '')  # 自定义完整路径
            
            if not filename and not custom_path:
                self.send_json_response({"success": False, "error": "缺少文件名"}, 400)
                return
            
            # 确定保存路径
            if custom_path:
                # 使用自定义完整路径
                custom_path = os.path.expanduser(custom_path)
                if not os.path.isabs(custom_path):
                    custom_path = safe_join(config["save_path"], custom_path)
                    if not custom_path:
                        self.send_json_response({"success": False, "error": "非法路径"}, 400)
                        return
                else:
                    custom_path = os.path.abspath(custom_path)
                if not is_path_allowed(custom_path):
                    self.send_json_response({"success": False, "error": "不允许保存到该路径"}, 403)
                    return
                save_dir = os.path.dirname(custom_path)
                filepath = custom_path
            else:
                # 使用默认路径 + 子文件夹
                if subfolder:
                    save_dir = safe_join(config["save_path"], subfolder)
                    if not save_dir:
                        self.send_json_response({"success": False, "error": "非法子目录"}, 400)
                        return
                else:
                    save_dir = config["save_path"]
                filepath = os.path.join(save_dir, filename)
            
            # 确保目录存在
            if config["auto_create_dir"]:
                ensure_dir(save_dir)
            elif not os.path.exists(save_dir):
                self.send_json_response({"success": False, "error": f"目录不存在: {save_dir}"}, 400)
                return
            
            # 处理文件名冲突
            if not config["allow_overwrite"]:
                filepath = get_unique_filename(filepath)
            
            # 获取文件内容
            if content:
                # base64解码
                if ',' in content:
                    # 处理 data URL 格式
                    content = content.split(',', 1)[1]
                file_data = base64.b64decode(content)
            elif url:
                # 从URL下载（这里简化处理，实际可能需要更复杂的逻辑）
                import urllib.request
                with urllib.request.urlopen(url) as response:
                    file_data = response.read()
            else:
                self.send_json_response({"success": False, "error": "缺少文件内容"}, 400)
                return
            
            # 写入文件
            with open(filepath, 'wb') as f:
                f.write(file_data)
            
            log(f"文件已保存: {filepath} ({len(file_data)} bytes)")
            
            self.send_json_response({
                "success": True,
                "message": "文件保存成功",
                "path": filepath,
                "size": len(file_data)
            })
            
        except Exception as e:
            log(f"保存失败: {str(e)}")
            self.send_json_response({"success": False, "error": str(e)}, 500)
    
    def handle_batch_save(self, data):
        """处理批量文件保存"""
        try:
            files = data.get('files', [])
            subfolder = data.get('subfolder', '')
            
            if not files:
                self.send_json_response({"success": False, "error": "没有要保存的文件"}, 400)
                return
            
            results = []
            ensured_dirs = set()
            
            for file_info in files:
                try:
                    filename = file_info.get('filename', f'file_{len(results)}.png')
                    content = file_info.get('content', '')
                    file_type = file_info.get('type', '')
                    base_dir = config["save_path"]
                    if file_type == 'video' and config.get("video_save_path"):
                        base_dir = config["video_save_path"]
                    elif file_type == 'image' and config.get("image_save_path"):
                        base_dir = config["image_save_path"]
                    if subfolder:
                        save_dir = safe_join(base_dir, subfolder)
                        if not save_dir:
                            self.send_json_response({"success": False, "error": "非法子目录"}, 400)
                            return
                    else:
                        save_dir = base_dir
                    if config["auto_create_dir"] and save_dir not in ensured_dirs:
                        ensure_dir(save_dir)
                        ensured_dirs.add(save_dir)
                    
                    filepath = os.path.join(save_dir, filename)
                    if not config["allow_overwrite"]:
                        filepath = get_unique_filename(filepath)
                    
                    if content:
                        if ',' in content:
                            content = content.split(',', 1)[1]
                        file_data = base64.b64decode(content)
                        
                        with open(filepath, 'wb') as f:
                            f.write(file_data)
                        
                        results.append({
                            "filename": filename,
                            "path": filepath,
                            "success": True,
                            "size": len(file_data)
                        })
                        log(f"批量保存: {filepath}")
                    else:
                        results.append({
                            "filename": filename,
                            "success": False,
                            "error": "缺少内容"
                        })
                except Exception as e:
                    results.append({
                        "filename": file_info.get('filename', 'unknown'),
                        "success": False,
                        "error": str(e)
                    })
            
            success_count = sum(1 for r in results if r.get('success'))
            self.send_json_response({
                "success": True,
                "message": f"已保存 {success_count}/{len(files)} 个文件",
                "results": results
            })
            
        except Exception as e:
            log(f"批量保存失败: {str(e)}")
            self.send_json_response({"success": False, "error": str(e)}, 500)
    
    def handle_update_config(self, data):
        """更新配置"""
        try:
            if 'save_path' in data:
                new_path = data['save_path']
                if new_path:
                    new_path = os.path.expanduser(new_path)
                    if not os.path.isabs(new_path):
                        new_path = os.path.abspath(os.path.join(config["save_path"], new_path))
                    if not is_path_allowed(new_path):
                        self.send_json_response({"success": False, "error": "不允许设置该路径"}, 403)
                        return
                    config["save_path"] = new_path
                    log(f"保存路径已更新: {config['save_path']}")
            
            if 'image_save_path' in data:
                new_path = data['image_save_path']
                config["image_save_path"] = os.path.expanduser(new_path) if new_path else ""
                log(f"图片保存路径已更新: {config['image_save_path'] or '(使用默认路径)'}")
            
            if 'video_save_path' in data:
                new_path = data['video_save_path']
                config["video_save_path"] = os.path.expanduser(new_path) if new_path else ""
                log(f"视频保存路径已更新: {config['video_save_path'] or '(使用默认路径)'}")
            
            if 'auto_create_dir' in data:
                config["auto_create_dir"] = bool(data['auto_create_dir'])
            
            if 'allow_overwrite' in data:
                config["allow_overwrite"] = bool(data['allow_overwrite'])
            
            if 'convert_png_to_jpg' in data:
                config["convert_png_to_jpg"] = bool(data['convert_png_to_jpg'])
                log(f"PNG转JPG: {'开启' if config['convert_png_to_jpg'] else '关闭'}")
            
            if 'jpg_quality' in data:
                config["jpg_quality"] = max(1, min(100, int(data['jpg_quality'])))
                log(f"JPG质量: {config['jpg_quality']}")
            
            self.send_json_response({
                "success": True,
                "message": "配置已更新",
                "config": {
                    "save_path": config["save_path"],
                    "image_save_path": config["image_save_path"] or config["save_path"],
                    "video_save_path": config["video_save_path"] or config["save_path"],
                    "image_save_path_raw": config["image_save_path"],
                    "video_save_path_raw": config["video_save_path"],
                    "auto_create_dir": config["auto_create_dir"],
                    "allow_overwrite": config["allow_overwrite"],
                    "convert_png_to_jpg": config["convert_png_to_jpg"],
                    "jpg_quality": config["jpg_quality"]
                }
            })
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)}, 500)
    
    def handle_save_thumbnail(self, data):
        """保存缩略图（用于历史记录性能优化）"""
        try:
            item_id = data.get('id', '')
            content = data.get('content', '')  # base64编码的缩略图
            category = data.get('category', 'history')  # history 或 characters
            
            if not item_id or not content:
                self.send_json_response({"success": False, "error": "缺少ID或内容"}, 400)
                return
            
            # 缩略图保存在 .tapnow_cache 子目录
            cache_dir = os.path.join(config["save_path"], '.tapnow_cache', category)
            ensure_dir(cache_dir)
            
            # 文件名使用 item_id
            filename = f"{item_id}.jpg"
            filepath = os.path.join(cache_dir, filename)
            
            # 解码并保存
            if ',' in content:
                content = content.split(',', 1)[1]
            file_data = base64.b64decode(content)
            
            with open(filepath, 'wb') as f:
                f.write(file_data)
            
            # 返回可访问的URL
            rel_path = f".tapnow_cache/{category}/{filename}"
            local_url = f"http://127.0.0.1:{config['port']}/file/{rel_path}"
            
            log(f"缩略图已保存: {filepath}")
            self.send_json_response({
                "success": True,
                "path": filepath,
                "url": local_url,
                "rel_path": rel_path
            })
        except Exception as e:
            log(f"保存缩略图失败: {str(e)}")
            self.send_json_response({"success": False, "error": str(e)}, 500)
    
    def handle_save_cache(self, data):
        """保存缓存文件（用于角色库等原图缓存）"""
        try:
            item_id = data.get('id', '')
            content = data.get('content', '')  # base64编码的图片
            category = data.get('category', 'characters')
            filename_ext = data.get('ext', '.jpg')
            file_type = data.get('type', 'image')  # image 或 video
            custom_path = data.get('custom_path', '')  # 用户自定义路径
            
            if not item_id or not content:
                self.send_json_response({"success": False, "error": "缺少ID或内容"}, 400)
                return
            
            # 确定保存目录
            base_root = config["save_path"]
            if custom_path:
                # 使用用户自定义路径
                cache_dir = os.path.expanduser(custom_path)
                if not os.path.isabs(cache_dir):
                    cache_dir = safe_join(config["save_path"], cache_dir)
                    if not cache_dir:
                        self.send_json_response({"success": False, "error": "非法路径"}, 400)
                        return
                else:
                    cache_dir = os.path.abspath(cache_dir)
                if not is_path_allowed(cache_dir):
                    self.send_json_response({"success": False, "error": "不允许保存到该路径"}, 403)
                    return
                cache_dir_abs = os.path.abspath(cache_dir)
                for candidate in [config.get("image_save_path", ""), config.get("video_save_path", ""), config["save_path"]]:
                    if not candidate:
                        continue
                    candidate_abs = os.path.abspath(candidate)
                    try:
                        if os.path.commonpath([cache_dir_abs, candidate_abs]) == candidate_abs:
                            base_root = candidate
                            break
                    except ValueError:
                        continue
            elif file_type == 'video' and config["video_save_path"]:
                # 视频使用视频保存路径
                base_root = config["video_save_path"]
                cache_dir = os.path.join(base_root, category)
            elif file_type == 'image' and config["image_save_path"]:
                # 图片使用图片保存路径
                base_root = config["image_save_path"]
                cache_dir = os.path.join(base_root, category)
            else:
                # 默认使用 .tapnow_cache 子目录
                base_root = config["save_path"]
                cache_dir = os.path.join(base_root, '.tapnow_cache', category)
            
            ensure_dir(cache_dir)
            
            # 解码文件数据
            if ',' in content:
                content = content.split(',', 1)[1]
            file_data = base64.b64decode(content)
            
            # PNG转JPG（仅对图片且开启了转换）
            converted = False
            if file_type == 'image' and config["convert_png_to_jpg"] and filename_ext.lower() == '.png':
                file_data, converted = convert_png_to_jpg(file_data, config["jpg_quality"])
                if converted:
                    filename_ext = '.jpg'
                    log(f"PNG已转换为JPG: {item_id}")
            
            filename = f"{item_id}{filename_ext}"
            filepath = os.path.join(cache_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(file_data)
            
            # 返回可访问的URL
            # 处理跨磁盘的情况（Windows上不同盘符无法使用relpath）
            try:
                rel_path = os.path.relpath(filepath, base_root).replace('\\', '/')
            except ValueError:
                # 跨磁盘时使用相对于cache_dir的路径
                rel_path = os.path.relpath(filepath, cache_dir).replace('\\', '/')
                # 添加category前缀
                if base_root == config["save_path"]:
                    rel_path = f".tapnow_cache/{category}/{rel_path}"
                else:
                    rel_path = f"{category}/{rel_path}"
            if rel_path.startswith('..'):
                rel_path = os.path.relpath(filepath, cache_dir).replace('\\', '/')
                if base_root == config["save_path"]:
                    rel_path = f".tapnow_cache/{category}/{rel_path}"
                else:
                    rel_path = f"{category}/{rel_path}"
            local_url = f"http://127.0.0.1:{config['port']}/file/{rel_path}"
            
            log(f"缓存文件已保存: {filepath} ({len(file_data)} bytes)")
            self.send_json_response({
                "success": True,
                "path": filepath,
                "url": local_url,
                "rel_path": rel_path,
                "converted": converted,
                "size": len(file_data)
            })
        except Exception as e:
            log(f"保存缓存失败: {str(e)}")
            self.send_json_response({"success": False, "error": str(e)}, 500)
    
    def handle_delete_file(self, data):
        """删除单个本地文件"""
        try:
            filepath = data.get('path', '')
            url = data.get('url', '')  # 也可以通过URL来定位文件
            
            # 如果提供的是URL，尝试从URL中提取文件路径
            if not filepath and url:
                if url.startswith(f"http://127.0.0.1:{config['port']}/file/"):
                    rel_path = url.replace(f"http://127.0.0.1:{config['port']}/file/", '')
                    rel_path = normalize_rel_path(rel_path)
                    if not rel_path:
                        self.send_json_response({"success": False, "error": "非法路径"}, 400)
                        return
                    rel_path_os = rel_path
                    # 尝试多个可能的路径
                    possible_paths = [
                        os.path.join(config["save_path"], rel_path_os),
                    ]
                    if config["video_save_path"]:
                        possible_paths.append(os.path.join(config["video_save_path"], rel_path_os))
                    if config["image_save_path"]:
                        possible_paths.append(os.path.join(config["image_save_path"], rel_path_os))
                    
                    for path in possible_paths:
                        if os.path.exists(path):
                            filepath = path
                            break
                    else:
                        filepath = possible_paths[0] if possible_paths else ''
            
            if not filepath:
                self.send_json_response({"success": False, "error": "缺少文件路径"}, 400)
                return
            
            # 安全检查：确保文件在允许的目录内
            filepath = os.path.abspath(filepath)
            save_path = os.path.abspath(config["save_path"])
            image_path = os.path.abspath(config["image_save_path"]) if config["image_save_path"] else None
            video_path = os.path.abspath(config["video_save_path"]) if config["video_save_path"] else None
            
            allowed = filepath.startswith(save_path)
            if image_path and filepath.startswith(image_path):
                allowed = True
            if video_path and filepath.startswith(video_path):
                allowed = True
            
            if not allowed:
                self.send_json_response({"success": False, "error": "不允许删除该路径的文件"}, 403)
                return
            
            if not os.path.exists(filepath):
                self.send_json_response({"success": False, "error": "文件不存在"}, 404)
                return
            
            # 删除文件
            os.remove(filepath)
            log(f"文件已删除: {filepath}")
            
            self.send_json_response({
                "success": True,
                "message": "文件已删除",
                "path": filepath
            })
        except Exception as e:
            log(f"删除文件失败: {str(e)}")
            self.send_json_response({"success": False, "error": str(e)}, 500)
    
    def handle_delete_batch(self, data):
        """批量删除本地文件"""
        try:
            files = data.get('files', [])  # 文件路径列表或URL列表
            
            if not files:
                self.send_json_response({"success": False, "error": "没有要删除的文件"}, 400)
                return
            
            results = []
            # 所有可能的基础目录
            base_dirs = [config["save_path"]]
            if config["video_save_path"]:
                base_dirs.append(config["video_save_path"])
            if config["image_save_path"]:
                base_dirs.append(config["image_save_path"])
            
            log(f"[删除] 基础目录: {base_dirs}")
            
            for file_info in files:
                try:
                    # 支持字符串路径或对象格式
                    filepath = ''
                    url = ''
                    rel_path = ''
                    if isinstance(file_info, str):
                        filepath = file_info
                    else:
                        filepath = file_info.get('path') or ''
                        url = file_info.get('url') or ''
                    
                    log(f"[删除] 收到请求: path={filepath}, url={url}")
                    
                    # 查找文件 - 优先使用绝对路径
                    found_path = None
                    
                    # 1. 如果filepath是绝对路径，直接检查
                    if filepath and os.path.isabs(filepath):
                        log(f"[删除] 检查绝对路径: {filepath}")
                        if os.path.exists(filepath):
                            found_path = filepath
                            log(f"[删除] 找到文件（绝对路径）: {found_path}")
                    
                    # 2. 从URL中提取相对路径
                    if not found_path and url and '/file/' in url:
                        rel_path = url.split('/file/')[-1]
                        rel_path = normalize_rel_path(rel_path)
                        if not rel_path:
                            log(f"[删除] 非法路径")
                            rel_path = ''
                        else:
                            log(f"[删除] 从URL提取相对路径: {rel_path}")
                            rel_path_os = rel_path
                            for base_dir in base_dirs:
                                check_path = os.path.join(base_dir, rel_path_os)
                                log(f"[删除] 检查路径: {check_path}, 存在: {os.path.exists(check_path)}")
                                if os.path.exists(check_path):
                                    found_path = check_path
                                    log(f"[删除] 找到文件: {found_path}")
                                    break
                    
                    # 3. 如果filepath是相对路径
                    if not found_path and filepath and not os.path.isabs(filepath):
                        rel_path_os = filepath.replace('/', os.sep)
                        for base_dir in base_dirs:
                            check_path = os.path.join(base_dir, rel_path_os)
                            log(f"[删除] 检查路径: {check_path}")
                            if os.path.exists(check_path):
                                found_path = check_path
                                log(f"[删除] 找到文件: {found_path}")
                                break
                    
                    if not found_path:
                        log(f"[删除] 文件未找到")
                        results.append({"path": rel_path or filepath, "success": False, "error": "文件不存在"})
                        continue
                    
                    # 安全检查：只允许删除配置目录下的文件，或者是图片/视频文件
                    abs_path = os.path.abspath(found_path)
                    allowed = any(abs_path.startswith(os.path.abspath(d)) for d in base_dirs)
                    
                    # 如果不在基础目录中，检查是否是允许的媒体文件类型
                    if not allowed:
                        ext = os.path.splitext(abs_path)[1].lower()
                        allowed_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mov', '.webm'}
                        if ext in allowed_exts:
                            # 允许删除媒体文件，但记录日志
                            log(f"[删除] 允许删除媒体文件（不在基础目录）: {abs_path}")
                            allowed = True
                    
                    if not allowed:
                        log(f"[删除] 安全检查失败，不允许删除: {abs_path}")
                        results.append({"path": found_path, "success": False, "error": "不允许删除"})
                        continue
                    
                    os.remove(found_path)
                    log(f"[删除] 成功删除: {found_path}")
                    results.append({"path": found_path, "success": True})
                    
                except Exception as e:
                    log(f"[删除] 出错: {str(e)}")
                    results.append({
                        "path": file_info if isinstance(file_info, str) else file_info.get('path', 'unknown'),
                        "success": False,
                        "error": str(e)
                    })
            
            success_count = sum(1 for r in results if r.get('success'))
            self.send_json_response({
                "success": True,
                "message": f"已删除 {success_count}/{len(files)} 个文件",
                "results": results
            })
        except Exception as e:
            log(f"批量删除失败: {str(e)}")
            self.send_json_response({"success": False, "error": str(e)}, 500)

def run_server(port, save_path):
    """启动服务器"""
    config["port"] = port
    config["save_path"] = os.path.abspath(os.path.expanduser(save_path))
    if not is_path_allowed(config["save_path"]):
        print(f"保存路径不允许: {config['save_path']}")
        print("允许目录:")
        for root in get_allowed_roots():
            print(f"  - {root}")
        return
    
    # 确保保存目录存在
    ensure_dir(config["save_path"])
    
    server_address = ('127.0.0.1', port)
    httpd = ThreadingHTTPServer(server_address, TapnowHandler)
    
    print("=" * 50)
    print("  Tapnow Studio 本地接收器")
    print("=" * 50)
    print(f"  服务地址: http://127.0.0.1:{port}")
    print(f"  保存路径: {config['save_path']}")
    print("-" * 50)
    print("  API 接口:")
    print(f"    GET  /ping          - 健康检查")
    print(f"    GET  /status        - 服务状态")
    print(f"    GET  /config        - 获取配置")
    print(f"    GET  /browse        - 打开保存目录")
    print(f"    GET  /list-files    - 列出本地文件")
    print(f"    GET  /file/<path>   - 访问本地文件")
    print(f"    POST /save          - 保存单个文件")
    print(f"    POST /save-batch    - 批量保存文件")
    print(f"    POST /save-thumbnail- 保存缩略图")
    print(f"    POST /save-cache    - 保存缓存文件")
    print(f"    POST /delete-file   - 删除单个文件")
    print(f"    POST /delete-batch  - 批量删除文件")
    print(f"    POST /config        - 更新配置")
    print(f"    ANY  /proxy         - 代理请求")
    print("-" * 50)
    print("  按 Ctrl+C 停止服务")
    print("=" * 50)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
        httpd.shutdown()

def main():
    parser = argparse.ArgumentParser(description='Tapnow Studio 本地接收器')
    parser.add_argument('-p', '--port', type=int, default=DEFAULT_PORT,
                        help=f'监听端口 (默认: {DEFAULT_PORT})')
    parser.add_argument('-d', '--dir', type=str, default=DEFAULT_SAVE_PATH,
                        help=f'保存目录 (默认: {DEFAULT_SAVE_PATH})')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='静默模式，减少日志输出')
    
    args = parser.parse_args()
    
    if args.quiet:
        config["log_enabled"] = False

    load_config_file()
    
    run_server(args.port, args.dir)

if __name__ == '__main__':
    main()
