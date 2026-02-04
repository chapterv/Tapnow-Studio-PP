# Tapnow Middleware 配置说明 (本地 ComfyUI 代理)

## 1. 简介
Tapnow Middleware 是一个轻量级的 Python 本地服务，用于将本地 ComfyUI (`127.0.0.1:8188`) 封装成与 BizyAir 兼容的 API 接口。

**它带来的好处：**
*   **任务队列**: 防止并发请求卡死 ComfyUI，实现请求排队。
*   **黑盒调用**: 前端无需关心复杂的节点图，只需发送 Prompt。
*   **接口统一**: 与云端 BizyAir 使用几乎一致的调用逻辑。

---

## 2. 安装与启动

### 环境要求
*   Python 3.8+
*   依赖库: `pip install websocket-client`

### 启动方式
推荐运行全功能版本：
```bash
python tapnow-server-full.py
```
默认监听端口: **9527**

---

## 2. 本地接收器配置（允许目录 / Proxy）

默认允许的根目录:
- `~/Downloads`
- `D:\TapnowData`

要自定义允许目录，请编辑同目录的 `tapnow-local-config.json`，示例:

```json
{
  "allowed_roots": [
    "C:\\Users\\YourName\\Downloads",
    "D:\\TapnowData",
    "E:\\TapnowData"
  ]
}
```

说明:
- JSON 不支持注释，路径建议使用双反斜杠或正斜杠。
- `save_path` 必须位于 `allowed_roots` 之内，否则服务会拒绝启动。
- 修改后需要重启本地接收器。
- Windows 使用 `allowed_roots` 进行限制，macOS/Linux 默认仅使用 `save_path`。

### 代理配置（解决 CORS）
本地接收器支持 `/proxy` 转发第三方 API 请求，适用于流式响应与上传。

在 `tapnow-local-config.json` 中配置 `proxy_allowed_hosts` 白名单:

```json
{
  "allowed_roots": [
    "C:\\Users\\YourName\\Downloads",
    "D:\\TapnowData"
  ],
  "proxy_allowed_hosts": [
    "api.openai.com",
    "generativelanguage.googleapis.com",
    "ai.comfly.chat",
    "api-inference.modelscope.cn",
    "vibecodingapi.ai",
    "yunwu.ai",
    "muse-ai.oss-cn-hangzhou.aliyuncs.com",
    "googlecdn.datas.systems",
    "*.openai.azure.com"
  ],
  "proxy_timeout": 300
}
```

使用示例:

```javascript
const target = 'https://api.openai.com/v1/chat/completions';
const url = `http://127.0.0.1:9527/proxy?url=${encodeURIComponent(target)}`;
const resp = await fetch(url, {
  method: 'POST',
  headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
  body: JSON.stringify(payload)
});
```

说明:
- `proxy_allowed_hosts` 为空则代理被禁用。
- 如需临时允许任意域名，可设置为 `["*"]`（不建议）。
- `proxy_timeout` 为代理超时秒数，设置为 `0` 表示不超时。

---

## 3. 模板配置 (核心)

Middleware 不会自动扫描 ComfyUI，你需要手动导入工作流并配置参数映射。

所有的模板存放于 `workflows/` 目录下。

### 目录结构
```
localserver/
  tapnow-server-full.py
  workflows/
    ├── sdxl_standard/          <-- App ID (模板名称)
    │   ├── template.json       <-- ComfyUI 导出的 API JSON
    │   └── meta.json           <-- 参数映射配置
    └── flux_dev/               <-- 另一个模板
        ├── template.json
        └── meta.json
```

### 如何创建模板 (template.json)
1. 打开 ComfyUI 网页版。
2. 打开设置 (齿轮) -> 勾选 **Enable Dev mode Options**。
3. 点击 **Save (API Format)** 按钮。
4. 将保存的 json 重命名为 `template.json` 并放入对应文件夹。

### 如何配置映射 (meta.json)
你需要告诉 Middleware，用户的输入 (如 `prompt`) 应该填入哪个节点的哪个字段。

```json
{
  "name": "SDXL 标准文生图",
  "params_map": {
    "prompt": { 
        "node_id": "6",       // 节点 ID (从 template.json 中找)
        "field": "inputs.text" // 要修改的字段路径
    },
    "seed": { 
        "node_id": "3", 
        "field": "inputs.seed" 
    },
    "cfg": {
        "node_id": "3",
        "field": "inputs.cfg"
    }
  }
}
```

---

## 4. API 接口文档

### 4.1 获取可用模板列表
*   **URL**: `GET /comfy/apps`
*   **Response**:
    ```json
    { "apps": ["sdxl_standard", "flux_dev"] }
    ```

### 4.2 提交生成任务
*   **URL**: `POST /comfy/queue`  
*   **兼容**: `POST /w/v1/webapp/task/openapi/create` / `POST /task/openapi/ai-app/run`
*   **Body**:
    ```json
    {
      "app_id": "sdxl_standard",  // 对应文件夹名
      "inputs": {
        "prompt": "a beautiful girl, 8k, best quality",
        "seed": 123456
      }
    }
    ```
*   **Response**:
    ```json
    {
      "requestId": "550e8400-e29b-41d4-a716-446655440000",
      "status": "Queued",
      "code": 20000,
      "message": "Ok"
    }
    ```

### 4.3 查询任务进度
*   **URL**: `GET /comfy/status/{job_id}`  
*   **兼容**: `GET /w/v1/webapp/task/openapi/detail?requestId=...`
*   **Response (处理中)**:
    ```json
    { "status": "processing" }
    ```
*   **Response (成功)**:
    ```json
    {
      "status": "success",
      "result": {
        "images": [
            "http://127.0.0.1:8188/view?filename=ComfyUI_001.png&..."
        ]
      }
    }
    ```

### 4.4 获取输出
* **URL**: `GET /w/v1/webapp/task/openapi/outputs?requestId=...`
* **Response**:
  ```json
  {
    "code": 20000,
    "message": "Ok",
    "data": {
      "outputs": [{ "object_url": "http://127.0.0.1:8188/view?..." }]
    }
  }
  ```
