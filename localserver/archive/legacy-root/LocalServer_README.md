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
