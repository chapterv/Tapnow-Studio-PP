# 🎨 Tapnow Studio (v2.5)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![React](https://img.shields.io/badge/Framework-React_18-61DAFB.svg)](https://reactjs.org/)
[![Single File](https://img.shields.io/badge/Build-Single__HTML-orange.svg)]()

**一个基于无限画布的节点式 AI 创意工作站。** 无需安装环境，无需 Python 依赖，**下载即用**的单文件 AI 工作流前端。

---

## 📖 简介 (Introduction)

**Tapnow Studio** 是一个运行在浏览器中的可视化 AI 工作流工具。它采用“节点编辑”的交互方式（类似 ComfyUI），将当前最强大的 AI 模型能力聚合在一个无限缩放的画布上。

它的核心理念是 **"轻量化"** 与 **"多模态协同"**。整个应用被打包在一个独立的 HTML 文件中，利用浏览器原生的能力和 CDN 资源，实现了复杂的 AI 交互逻辑。

<img width="1920" height="960" alt="2e8568e463c6473d89bc5be6ea5e57e8" src="https://github.com/user-attachments/assets/2020616f-204b-4aa7-854d-10e970cf5519" />

## ✨ 核心功能 (Key Features)

### 1. ♾️ 无限画布与节点系统
* **拖拽式连线**：直观地将输入（图片/视频）流转到处理节点。
* **无限缩放**：支持超大画布，利用鼠标滚轮自由缩放和平移。
* **多选与批量操作**：支持框选节点，批量移动或删除。
* **实时预览**：每个节点都具备独立的状态显示、进度条和结果预览。

### 2. 🎞️ 深度视频分析与反推 (Video Intelligence)
这是 Tapnow Studio 的杀手级功能，内置了复杂的视觉处理逻辑：
* **智能抽帧 (Smart Scene Detection)**：内置基于像素差值的场景检测算法 (`detectScenesAndCapture`)，自动识别视频镜头切换并提取关键帧。
* **导演级分镜拆解**：结合 Gemini 3 Pro 等多模态大模型，能够分析视频的**运镜手法**（推拉摇移）、**主体动态**、**光影氛围**。
* **提示词反推 (Reverse Prompting)**：自动将视频关键帧反推为 **Midjourney (英文)** 和 **即梦 (中文)** 的高精度提示词。
* **口播提取**：自动提取视频中的语音内容并生成时间轴脚本。

### 3. 🎨 全面的 AI 绘图支持
* **Midjourney 深度集成**：
    * 支持 Text-to-Image (文生图)。
    * 支持  **Image Prompting** (垫图)。
    * 支持 `--oref` (角色一致性) 和 `--sref` (风格一致性) 的可视化连线配置。
* **即梦 (Jimeng) AI**：
    * 支持即梦 4.5 / 4.1 / 3.1 模型。
    * 支持 **图生图**（自动处理 Base64/JSON 转换）。
    * 智能分辨率适配（Auto/1K/2K/4K）。
* **其他模型**：Flux, DALL-E 3 (GPT-4o Image), Nano Banana，（部分模型还没接-因为价格感觉不是很划算） 等。


### 4. 🎥 AI 视频生成
支持主流视频生成模型的参数配置与任务轮询：
* **Sora**
* **Grok-3 Video**
* **Google Veo**
* **内置其他模型可供自行对接**

### 5. 🛠️ 实用辅助工具
* **图像对比 (Image Compare)**：带有滑动条的 AB 对比节点，方便查看原图与重绘图的差异。
* **批量素材管理**：内置历史记录管理器，支持批量删除、批量重新发送到画布。
* **暗黑/明亮模式**：自适应 UI 主题切换。

---

## 🚀 快速开始 (Quick Start)

### 方式 1：直接运行
1.  下载本仓库中的 `Tapnow Studio-V2.5.html` 文件。
2.  双击使用 Chrome, Edge 或 Safari 浏览器打开。
3.  点击右上角 **API 设置**，配置你的模型 Key 即可开始使用。

### 方式 2：本地开发
如果你想修改代码：
1.  该项目是一个单文件 React 应用，源码直接嵌入在 HTML 的 `<script type="text/babel">` 标签中。
2.  你可以直接使用 VS Code 编辑该 HTML 文件。
3.  依赖库（React, Tailwind, Lucide, Babel）均通过 CDN 加载，无需 `npm install`。

---

## 🔌 即梦 (Jimeng) API 配置指南

由于浏览器安全策略（CORS）及即梦 API 的特殊签名验证，**Tapnow Studio 需要配合后端代理服务使用即梦功能**。

本项目完美适配开源项目 **[jimeng-api](https://github.com/iptag/jimeng-api)**。

### 1. 部署后端服务
你可以选择以下任意一种方式在本地运行服务：

**选项 B：下载可执行文件 (.exe)** 前往 [jimeng-api Releases](https://github.com/iptag/jimeng-api/releases) 下载 Windows/Mac/Linux 版本并运行。

服务启动后，默认地址为 `http://localhost:5100`

### 2. 获取 Session ID

1.  在浏览器访问 [即梦官网 (jimeng.jianying.com)](https://jimeng.jianying.com/) 并登录。
2.  按 `F12` 打开开发者工具，点击 `Application` (应用) 标签页。
3.  在左侧栏找到 `Cookies` ，点击即梦的域名。
4.  复制 `sessionid` 的值。

### 3. 在 Tapnow Studio 中连接

1.  打开 Tapnow Studio 右上角的 **API 设置**。
2.  找到 **Jimeng** 相关的模型配置（或添加新模型）。
3.  **Base URL** 填入： `http://localhost:5100` 。
4.  **API Key** 填入：刚才复制的 `sessionid` 。
5.  *(可选)* 勾选设置底部的“即梦图生图使用本地文件”以获得更好的上传稳定性。

---

## ⚙️ 技术架构 (Technical Details)

Tapnow Studio 展示了现代前端技术在无构建工具（No-Build）环境下的极限能力：

* **Runtime**: 浏览器原生 ES Modules + Babel Standalone 实时编译 JSX。
* **UI Framework**: React 18 (UMD)。
* **Styling**: Tailwind CSS (Script Tag 注入)。
* **State Management**: React Hooks ( `useMemo` , `useCallback` , `useRef` ) 实现高性能画布渲染。
* **Storage**: `localStorage` 实现数据持久化（API Key、历史记录、画布状态）。
* **Network**: 原生 `fetch` API 处理 Server-Sent Events (SSE) 和长轮询。

## 🤝 致谢与声明 (Credits)

* **AI Architecture**: 本项目的核心逻辑、UI 组件及架构设计由 **Gemini** 辅助完成。
* **Jimeng Support**: 即梦接口支持由 **[iptag/jimeng-api](https://github.com/iptag/jimeng-api)** 提供，这是一个非常棒的逆向工程项目。
* **Icons**: 使用 [Lucide](https://lucide.dev/) 图标库。

## ⚠️ 免责声明 (Disclaimer)

本项目仅供学习与技术研究使用。

* 请勿将本项目用于任何非法用途。
* 使用即梦、Midjourney 等服务时，请遵守相应服务商的使用条款。
* 用户需自行管理 API Key，本项目不会上传任何 Key 到云端。

## 📄 开源协议 (License)

[MIT License](LICENSE)
* 请勿将本项目用于任何非法用途。
* 使用即梦、Midjourney 等服务时，请遵守相应服务商的使用条款。
* 用户需自行管理 API Key，本项目不会上传任何 Key 到云端。

## 📄 开源协议 (License)

[MIT License](LICENSE)
