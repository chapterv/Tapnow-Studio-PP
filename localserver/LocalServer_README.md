# Tapnow Studio 本地接收器配置

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

## 代理配置（解决 CORS）
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

## 本地缓存与保存节点
Tapnow LocalServer 除了代理，还在后台主动缓存所有通过历史、导出、分享生成的资源。

* **主动缓存逻辑**：每次下载图片/视频时都会写入本地 `save_path`，并自动记录 `hash`，避免重复拉取（即使是在 ComfyUI 生成中）。
* **保存节点联动**：在 Tapnow Studio 中启用“保存节点”，可把作业链的输出推入本地目录；本地服务会为新文件生成可浏览 URL，方便分享/批量导出。
* **缓存优先级**：资源加载顺序为 `本地缓存 -> 代理 -> 直连`，确保 CORS 安全且带宽可控。

## ComfyUI 与 CORS
当 Tapnow Studio 需要访问本地 ComfyUI（`127.0.0.1:8188`）或其他模型服务时，LocalServer 会：

1. 自动添加 `Access-Control-Allow-*` 头，解决浏览器跨域限制。
2. 将请求通过 `/proxy` 中转（可配置 `proxy_allowed_hosts`）。
3. 将生成结果写入本地缓存并返回可直接访问的 `object_url`。

### Quick Test
```bash
curl http://127.0.0.1:9527/ping
```

## 关联参考
* 本地 ComfyUI 配置请看 `localserver/Middleware_README-ComfyUI.md`，其中详细描述模板生成、meta 映射与模型库的引用章节（`model-template-readme.md` 第 4/5/9 章）。
* 模型库设置请参考 `model-template-readme.md` 以及 `docs/api/模型库测试方法.md` 中的 Batch/Sampler/Scheduler 说明。
