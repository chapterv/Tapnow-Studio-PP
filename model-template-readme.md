# 模型库配置与测试说明书（统一版）

> 本文合并了 `model-template-readme.md` 与 `docs/api/模型库测试方法.md`，作为唯一权威说明。
> 覆盖：模型库配置、请求模板、异步任务、BizyAir、本地 ComfyUI、测试流程。

---

## 1. 基础概念

- **Provider**：供应商（如 BizyAir / ModelScope / SiliconFlow / Local ComfyUI）。
- **模型 ID（系统调用）**：真实调用字段（`model` / `modelId` / `web_app_id`）。
- **显示名**：仅 UI 展示用名称。
- **接口类型**：OpenAI / Gemini / ModelScope。
- **模型类型**：Chat / Image / ChatImage / Video。

> ChatImage：可在 Chat 面板与 Image 生成中双向使用。

---

## 2. 自定义参数 & input 规则

### 2.1 自定义参数
- 模型库条目可添加 **自定义参数**，用于模板变量替换。
- 变量格式：`{{paramName}}`，可带类型：`{{paramName:number}}`。

### 2.2 input 输入框规则
- **参数名或参数值**包含 `input / 输入` 会自动变成前端输入框。
- 例：`steps_input`、`modelscopeImageCount_input`。

### 2.3 多图输入变量
- `{{imageUrl1}} / {{imageUrl2}} / {{imageUrl3}} / {{imageUrl4}}`
- `{{imageUrls.0}} / {{imageUrls.1}}`（数组索引）

> BizyAir 示例：
> `"431:LoadImage.image": "{{imageUrl1}}"`

---

## 3. 请求模板（Request Template）

### 3.1 常用变量
- `{{modelName}}` 模型 ID
- `{{prompt}}`
- `{{ratio}}`
- `{{size}}` / `{{resolution}}`
- `{{seed}}`
- `{{imageUrl}} / {{imageUrls}}`
- `{{imageBlob}} / {{imageDataUrl}}`（multipart/raw）

### 3.2 BizyAir 应用（AI App）示例
```json
{
  "web_app_id": {{bizyairWebAppId:number}},
  "suppress_preview_output": false,
  "input_values": {
    "45:JjkText.text": "{{prompt}}",
    "4:KSampler.steps": {{bizyairSteps:number}},
    "36:EmptySD3LatentImage.width": {{bizyairWidth:number}},
    "36:EmptySD3LatentImage.height": {{bizyairHeight:number}}
  }
}
```

### 3.3 BizyAir 工作流（Workflow）示例
```json
{
  "web_app_id": {{bizyairWebAppId:number}},
  "suppress_preview_output": false,
  "input_values": {
    "431:LoadImage.image": "{{imageUrl1}}",
    "430:LoadImage.image": "{{imageUrl2}}",
    "587:BizyAir_NanoBananaPro.prompt": "{{prompt}}",
    "587:BizyAir_NanoBananaPro.aspect_ratio": "{{ratio}}",
    "587:BizyAir_NanoBananaPro.resolution": "{{size}}"
  }
}
```

---

## 4. 本地 ComfyUI（Local Middleware）配置

### 4.1 workflow 准备
1. ComfyUI 导出 API JSON（DevMode → Export API）。
2. 新建目录：`localserver/workflows/<app_id>/`
3. 将 JSON 重命名为 `template.json` 放入目录。
4. 执行：`prepare_workflow_templates.bat` 自动生成 `meta.json`（路径：`localserver/workflows/`）。

> `app_id = 目录名 = 模型库里的模型ID`。
> 脚本会自动生成常用参数映射（prompt/seed/steps/width/height/batch/sampler/scheduler），
> 并保留完整的 `nodeId.input` 映射，便于后续精细调整。

### 4.2 Provider 配置
- Base URL：`http://127.0.0.1:9527`
- API KEY：空
- 接口类型：OpenAI

### 4.3 模型库请求模板（推荐）
> 结论：**你传的是“参数名”，Comfy 只认“节点输入名”**。  
> 所以 `batch_input=4` 如果没有正确映射，会被 Comfy 当作无效字段，最终仍使用默认值。

**方式 A：模板里直接写节点字段（不改 meta.json，最稳）**
```json
{
  "web_app_id": "{{modelName}}",
  "input_values": {
    "44:KSampler.seed": {{seed:number}},
    "44:KSampler.steps": {{steps:number}},
    "44:KSampler.sampler_name": "{{sampler}}",
    "44:KSampler.scheduler": "{{scheduler}}",
    "41:EmptySD3LatentImage.width": {{width:number}},
    "41:EmptySD3LatentImage.height": {{height:number}},
    "41:EmptySD3LatentImage.batch_size": {{batch:number}}
  }
}
```

**方式 B：通过 meta.json 映射（推荐）**
```json
{
  "params_map": {
    "seed":      { "node_id": "44", "field": "inputs.seed" },
    "steps":     { "node_id": "44", "field": "inputs.steps" },
    "sampler":   { "node_id": "44", "field": "inputs.sampler_name" },
    "scheduler": { "node_id": "44", "field": "inputs.scheduler" },
    "width":     { "node_id": "41", "field": "inputs.width" },
    "height":    { "node_id": "41", "field": "inputs.height" },
    "batch":     { "node_id": "41", "field": "inputs.batch_size" }
  }
}
```

模板可简化为：
```json
{
  "web_app_id": "{{modelName}}",
  "input_values": {
    "seed": {{seed:number}},
    "steps": {{steps:number}},
    "sampler": "{{sampler}}",
    "scheduler": "{{scheduler}}",
    "width": {{width:number}},
    "height": {{height:number}},
    "batch": {{batch:number}}
  }
}
```

**如何找 node id**  
在 `template.json` 里搜索：
```
"class_type": "KSampler"
"class_type": "EmptySD3LatentImage" 或 "EmptyLatentImage"
```
对应对象的 key 就是 `node_id`。

> 说明：系统会优先使用 `meta.json` 映射；若缺失，会用通用键名兜底。  
> 若希望 UI 出现可输入框，请在模型库「自定义参数」里添加对应参数，
> 且参数名包含 `input`（如 `seed_input` / `steps_input` / `sampler_input` / `batch_input`）。  
> **注意**：`_input` 只是 UI 输入提示，不等于 Comfy 节点输入名。

### 4.4 批量与调度参数（Batch/Sampler/Scheduler）
模型库若需暴露更多 ComfyUI 控制能力，可用 **方式 A（直接写节点字段）** 或 **方式 B（meta.json 映射）**。

**方式 A（直接写节点字段）**
```json
{
  "input_values": {
    "41:EmptySD3LatentImage.batch_size": {{batch:number}},
    "44:KSampler.sampler_name": "{{sampler}}",
    "44:KSampler.scheduler": "{{scheduler}}"
  }
}
```

**方式 B（meta.json）**
```json
{
  "params_map": {
    "batch": { "node_id": "41", "field": "inputs.batch_size" },
    "sampler": { "node_id": "44", "field": "inputs.sampler_name" },
    "scheduler": { "node_id": "44", "field": "inputs.scheduler" }
  }
}
```

* `batch`：映射到 `batch_size` 或 `sampler.batch_size`。
* `sampler`：常见 `euler / euler_a / dpmpp_2m / dpmpp_2m_sde`。
* `scheduler`：常见 `normal / karras / exponential`。

**提示**：在模型库自定义参数中增加 `batch_input`、`sampler_input`、`scheduler_input`，即可在 UI 显示输入框，方便用户实时调整。

---

## 5. 异步任务（Async Config）

### 5.1 基础流程
- create → 返回 requestId
- detail → 查询状态
- outputs → 返回结果

### 5.2 通用字段说明
- `requestIdPaths`：从 create 响应提取 requestId
- `statusRequest`：状态查询请求模板
- `statusPath`：状态字段路径
- `successValues / failureValues`
- `outputsRequest`：结果查询请求模板
- `outputsPath / outputsUrlField`

### 5.3 直接可贴的通用配置（本地 ComfyUI / BizyAir）
```json
{
  "enabled": true,
  "detail": "/w/v1/webapp/task/openapi/detail",
  "outputs": "/w/v1/webapp/task/openapi/outputs",
  "requestIdPaths": ["requestId", "request_id", "taskId"],
  "statusPath": "data.status",
  "successValues": ["Success"],
  "failureValues": ["Failed", "Canceled"],
  "outputsPath": "data.outputs",
  "outputsUrlField": "object_url",
  "pollIntervalMs": 1500,
  "timeoutMs": 120000
}
```

> 说明：
> - requestId 必须是完整 UUID。
> - detail/outputs 可简写成字符串，系统会自动补 `?requestId={{requestId}}`。
> - prompt_id 也可当 requestId 查询（已兼容）。

---

## 6. BizyAir 模型库配置与测试

### 6.1 Provider
- BaseURL：`https://api.bizyair.cn`
- Key：BizyAir API Key

### 6.2 模型库条目
- 类型：Image
- 请求模板：
  - endpoint：`/w/v1/webapp/task/openapi/create`
  - method：POST
  - bodyType：raw
  - headers：
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer {{provider.key}}",
  "X-Bizyair-Task-Async": "enable"
}
```

### 6.3 运行验证
1. 点击生成 → 观察返回 requestId。
2. detail 查询：
   `GET /w/v1/webapp/task/openapi/detail?requestId=...`
3. outputs 查询：
   `GET /w/v1/webapp/task/openapi/outputs?requestId=...`

---

## 7. 通用测试流程（所有 Provider）

1. 设置 → 模型库
2. 打开请求模板 → 查看 Request Preview
3. 生成一次 → 检查网络与控制台
4. 若失败：
   - 复制 request preview + 服务端报错
   - 验证变量是否为空（特别是 number 类型）

---

## 8. 常见问题排查

- **400: input type invalid**
  - 参数为空（null/空字符串）会导致 Comfy 验证失败。
  - 确保 input_values 有值，或删除该字段以使用 workflow 默认值。

---

## 9. 参数调节指南（Seed / Sampler / Scheduler / Batch）

### 9.1 种子随机（Seed）
**推荐做法：**
1) 在模型库中保留 `seed` 输入（如 `seed_input`）。  
2) **要随机**时：  
   - 可不传 `seed`（留空），让 workflow 使用自身默认值；  
   - 或传一个新的正整数（最稳）；  
   - 本地中间件支持 `seed = -1` → 自动随机。  
3) **要固定**时：填一个具体整数。  

> ComfyUI 的 KSampler 默认 seed 最小值是 0，`-1` 在原生 ComfyUI 并非标准随机值。  
> **只有本地中间件才会将 `-1` 转成随机**，因此推荐在本地通过中间件调用。  
> 若 workflow 默认 seed 是固定的（如 0），且你希望每次随机：  
> - 加 `RandomSeed` 节点并映射；  
> - 或在 ComfyUI 中改 seed 默认逻辑后重新导出 `template.json`。

### 9.2 采样器 / 调度器切换
在 ComfyUI 中对应输入一般是：
- `sampler_name`
- `scheduler`

做法（任一方式）：
1) **meta.json 映射**：  
   - `sampler` → 对应节点的 `inputs.sampler_name`  
   - `scheduler` → 对应节点的 `inputs.scheduler`
2) **直接在 input_values 写 NodeID**：  
   ```json
   {
     "44:KSampler.sampler_name": "{{sampler}}",
     "44:KSampler.scheduler": "{{scheduler}}"
   }
   ```

### 9.3 批量数量（Batch）
ComfyUI 常见节点字段：`batch_size`

做法：
- 在 `input_values` 加：
  ```json
  { "41:EmptySD3LatentImage.batch_size": {{batch:number}} }
  ```
- 或通过 `meta.json` 把 `batch` 映射到 `inputs.batch_size`。

> 如果你的 workflow 使用的是其他节点（如 EmptyLatentImage/SDXL），请以实际节点 ID 为准。
> 若输出仍只有 1 张图，确认输出节点使用 **SaveImage**（PreviewImage 可能只返回第一张）。

- **outputs/detail 404**
  - requestId 不完整（UUID 被截断）。
  - 使用 create 返回的完整 requestId。

- **直接排查 /outputs 响应**
  - 通过 curl 验证：
    ```bash
    curl "http://127.0.0.1:9527/w/v1/webapp/task/openapi/outputs?requestId=<id>"
    ```
  - 返回结构通常包含：
    ```json
    {
      "data": {
        "outputs": [{ "object_url": "http://127.0.0.1:8188/view?..." }],
        "images": ["http://127.0.0.1:8188/view?..."]
      },
      "outputs": [{ "object_url": "http://127.0.0.1:8188/view?..." }]
    }
    ```

- **图像缓存 404**
  - 原始图片 URL 已失效或被清理。
  - 本地缓存会跳过保存，不影响生成结果。

---

## 9. 参考
- `docs/api/bizyair_implementation_plan.md`
- `docs/api/local_comfyui_test_guide.md`
- `docs/api/local comfyui codex improve.md`
- `docs/improve/multi_image_concurrency_plan.md`
