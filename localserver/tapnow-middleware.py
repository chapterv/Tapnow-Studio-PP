#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tapnow Studio 本地服务 (增强版)
功能：
1. 文件/代理服务 (原功能)
2. ComfyUI 中间件服务 (新增)：
   - 任务队列与并发控制
   - 模板管理与参数填充
   - WebSocket 状态监听

对应前端 BizyAir 模式配置：
Provider: local-middleware
URL: http://127.0.0.1:9527
WebAppID: 本地模板文件夹名称 (如 "sdxl_standard")
"""

import os
import sys
import json
import time
import uuid
import base64
import queue
import threading
import websocket # 需要 pip install websocket-client
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote, parse_qs
from datetime import datetime

# --- 配置部分 ---
PORT = 9527
COMFY_URL = "http://127.0.0.1:8188"
COMFY_WS_URL = "ws://127.0.0.1:8188/ws"
WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), "workflows")
SAVE_PATH = os.path.expanduser("~/Downloads/TapnowStudio")

# --- 全局状态 ---
JOB_QUEUE = queue.Queue()
JOB_STATUS = {} # {job_id: {status: 'queued'|'processing'|'success'|'failed', result: ...}}
STATUS_LOCK = threading.Lock()
CLIENT_ID = str(uuid.uuid4())

# --- 辅助函数 ---
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

# --- ComfyUI 核心逻辑 ---

def load_template(app_id):
    """加载模板和元数据"""
    template_path = os.path.join(WORKFLOWS_DIR, app_id, "template.json")
    meta_path = os.path.join(WORKFLOWS_DIR, app_id, "meta.json")
    
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"模板不存在: {app_id}")
        
    with open(template_path, 'r', encoding='utf-8') as f:
        workflow = json.load(f)
        
    params_map = {}
    if os.path.exists(meta_path):
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
            params_map = meta.get('params_map', {})
            
    return workflow, params_map

def apply_inputs(workflow, params_map, user_inputs):
    """将用户输入填入模板"""
    # 简单的参数映射逻辑
    # user_inputs: {"prompt": "cat", "seed": 123}
    # params_map: {"prompt": {"node_id": "6", "field": "inputs.text"}}
    
    for key, val in user_inputs.items():
        if key in params_map:
            mapping = params_map[key]
            node_id = mapping.get('node_id')
            field_path = mapping.get('field', '').split('.') # ['inputs', 'text']
            
            if node_id in workflow:
                target = workflow[node_id]
                # 递归查找字段
                for part in field_path[:-1]:
                    target = target.get(part, {})
                # 设置值
                target[field_path[-1]] = val
        else:
            # 尝试直接匹配 "84:CLIPTextEncode.text" 这种 BizyAir 格式
            if ":" in key and "." in key:
                 node_part, field_part = key.split(":", 1)
                 # 寻找 node_id (比如 "84")
                 # 注意：BizyAir 的 ID 可能和本地不一致，这里仅作为演示兼容性
                 # 实际建议只使用 params_map 映射
                 pass
    return workflow

def send_to_comfy(workflow):
    """发送任务到 ComfyUI"""
    prompt_payload = {
        "client_id": CLIENT_ID,
        "prompt": workflow
    }
    data = json.dumps(prompt_payload).encode('utf-8')
    req = urllib.request.Request(f"{COMFY_URL}/prompt", data=data)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

ws_messages = {} # {prompt_id: [msgs...]}

def worker_loop():
    """后台 Worker: 串行执行任务"""
    log("Worker 线程启动，等待任务...")
    
    # 建立 WS 连接监听进度
    def on_message(ws, message):
        msg = json.loads(message)
        # log(f"WS Recv: {msg['type']}")
        if msg['type'] == 'executed':
            pid = msg['data']['prompt_id']
            # 将结果暂存，主循环会去取
            if pid not in ws_messages: ws_messages[pid] = []
            ws_messages[pid].append(msg)

    # 简化的 WS 连接 (实际需处理断线重连)
    try:
        ws = websocket.WebSocketApp(f"{COMFY_WS_URL}?clientId={CLIENT_ID}",
                                  on_message=on_message)
        wst = threading.Thread(target=ws.run_forever, daemon=True)
        wst.start()
    except Exception as e:
        log(f"无法连接 ComfyUI WS: {e}")

    while True:
        job = JOB_QUEUE.get()
        job_id = job['id']
        
        with STATUS_LOCK:
            JOB_STATUS[job_id]['status'] = 'processing'
            
        try:
            log(f"开始处理任务: {job_id} (App: {job['app_id']})")
            
            # 1. 准备模板
            wf, pmap = load_template(job['app_id'])
            wf = apply_inputs(wf, pmap, job['inputs'])
            
            # 2. 提交
            resp = send_to_comfy(wf)
            prompt_id = resp['prompt_id']
            log(f"ComfyUI 任务已提交: {prompt_id}")
            
            # 3. 阻塞等待 WS 结果 (简单轮询 ws_messages)
            # 实际生产中应用 Event 事件通知
            timeout = 300
            start_t = time.time()
            final_images = []
            
            while time.time() - start_t < timeout:
                if prompt_id in ws_messages:
                    msgs = ws_messages[prompt_id]
                    for m in msgs:
                        # 解析 output images
                        # 格式: {"node": "9", "output": {"images": [{"filename":...}]}}
                        outputs = m['data'].get('output', {}).get('images', [])
                        for img in outputs:
                            # 构造 URL
                            img_url = f"{COMFY_URL}/view?filename={img['filename']}&type={img['type']}&subfolder={img['subfolder']}"
                            final_images.append(img_url)
                    
                    if final_images:
                        break # 已拿到图片（假设只有一张）
                        
                time.sleep(0.5)
            
            if final_images:
                with STATUS_LOCK:
                    JOB_STATUS[job_id]['status'] = 'success'
                    JOB_STATUS[job_id]['result'] = {'images': final_images}
                log(f"任务成功: {final_images}")
            else:
                raise TimeoutError("等待 ComfyUI 结果超时")
                
        except Exception as e:
            log(f"任务失败: {e}")
            with STATUS_LOCK:
                JOB_STATUS[job_id]['status'] = 'failed'
                JOB_STATUS[job_id]['error'] = str(e)
        finally:
            JOB_QUEUE.task_done()

# --- HTTP Handler ---

class EnhancedHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

    def send_json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path.startswith('/comfy/status/'):
            # 轮询状态
            job_id = parsed.path.split('/')[-1]
            with STATUS_LOCK:
                status = JOB_STATUS.get(job_id)
            if status:
                self.send_json(status)
            else:
                self.send_json({"error": "Job not found"}, 404)
                
        elif parsed.path == '/comfy/apps':
            # 获取支持的模板列表
            apps = []
            if os.path.exists(WORKFLOWS_DIR):
                for d in os.listdir(WORKFLOWS_DIR):
                    apps.append(d)
            self.send_json({"apps": apps})
            
        else:
            self.send_json({"status": "running", "mode": "middleware"}, 200)

    def do_POST(self):
        parsed = urlparse(self.path)
        
        if parsed.path == '/comfy/queue':
            # 提交任务
            length = int(self.headers['content-length'])
            body = json.loads(self.rfile.read(length))
            
            job_id = str(uuid.uuid4())
            job = {
                "id": job_id,
                "app_id": body.get('app_id') or body.get('web_app_id'), # 兼容 BizyAir 参数名
                "inputs": body.get('inputs', {}),
                "status": "queued",
                "created_at": time.time()
            }
            
            with STATUS_LOCK:
                JOB_STATUS[job_id] = job
            
            JOB_QUEUE.put(job)
            log(f"收到新任务: {job_id}")
            
            # 立即返回，类似 BizyAir 的 202 Accepted
            self.send_json({"job_id": job_id, "status": "queued"}, 200)
            
        else:
            self.send_json({"error": "Not Found"}, 404)

if __name__ == '__main__':
    ensure_dir(WORKFLOWS_DIR)
    
    # 启动 Worker
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    
    server = HTTPServer(('0.0.0.0', PORT), EnhancedHandler)
    log(f"Tapnow Middleware Running on port {PORT}")
    log(f"Workflows Dir: {WORKFLOWS_DIR}")
    server.serve_forever()
