# Tapnow-Studio-PP

本项目是基于原始 Tapnow Studio 的深度定制与增强版本，旨在提供更稳定、更安全、更高效的 AI 绘图与视频创作体验。

自接手以来，本项目在 AI (Google Gemini) 的协助下，从 V2.6 至今已历经 **100+ 次** 内部快速迭代与 **5 个** 重大里程碑版本的彻底重构，目前已进化为功能完备的多模态工作流平台。

## 🌟 核心工作内容 (Highlights)
相比于原始项目，我们在以下方面进行了重大改进：
*   **工程化重构**: 将原始单 HTML 架构利用 Vite + React 进行现代化重构，提升了 10 倍以上的加载速度。
*   **黑名单与容错机制**: 实现了多 API Key 智能轮换，自动拉黑积分耗尽（1006）或失效的 Key，确保大规模生成任务不中断。
*   **智能分镜系统 (Smart Storyboard)**: 开发了完整的可视化分镜编辑器，支持批量生成、首尾帧控制、多图参考及实时预览。
*   **性能专项优化**: 针对超大规模节点图和数千条历史记录进行了渲染优化，支持“极致”性能模式。
*   **数据持久化**: 彻底解决了 Blob URL 失效问题，所有资产自动同步至本地存储，支持 ZIP 批量导出。

---

## 📅 版本历史与选择

请根据您的需求选择使用最合适的版本：

### 🚀 最新稳定版 (Latest Sync)
*   **文件名**: `Tapnow Studio-V3.7.31.html`
*   **版本号**: **v3.7.31** (2026-01-10)
*   **主要更新**: 
    *   ✅ **修复锁定镜头批量生成**: 解决了锁定镜头仍被加入批量队列的问题。
    *   ✅ **预览回填修复** (V3.7.30): 彻底解决分镜生成后预览图无法自动显示的顽疾。
    *   ✅ **全量同步**: 此版本标志着本地开发环境与 [GitHub 仓库](https://github.com/chapterv/Tapnow-Studio-PP) 保持同步。

### 📁 关键里程碑版本 (Milestones)
| 版本 | 标题 | 核心特性 |
|------|------|----------|
| **V3.7.20** | **Provider 重构** | 统一了即梦 (Jimeng) 全系列模型的 Provider 配置架构。 |
| **V3.6.0** | **智能分镜重构** | 引入了双渠道架构和全新的分镜编辑器 UI。 |
| **V3.5.20** | **性能飞跃** | 专项体积优化与渲染效率提升。 |
| **V3.4.26** | **V3.4 最终版** | V3.4 系列逻辑的最稳定闭环。 |

### 🔍 详细更新日志
想要查看所有细微改动、Bug 修复及技术底层的变迁，请参阅：
👉 [**详细版本更新纪录 (Changelog.md)**](./changelog.md)

## ❤️ 特别鸣谢 (Special Thanks)
在此特别感谢原作者 **[zhengxinlan1995-code](https://github.com/zhengxinlan1995-code)**。正是得益于原项目优秀的灵感、扎实的架构基础以及无私的开源精神，才有了今日这个功能更强大的定制版本。向原作者的探索精神致敬！

> **以下信息来自原作者仓库，包含了项目的设计理念与基础功能说明。**

<br>
<br>

# ======================================================
# 🎨 Tapnow Studio (Original Project)
# ======================================================

<br>

[![AI-Native](https://img.shields.io/badge/Code-AI_Generated-f9a8d4.svg)](https://deepmind.google/technologies/gemini/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Single File](https://img.shields.io/badge/Build-Single__HTML-orange.svg)]()

> 🤖 **AI-Native Project 声明**
>
> 本项目是一个**AI 原生 (AI-Native)** 的实验性开源作品。
>
> **绝大部分核心代码、架构设计、UI 布局以及逻辑实现均在大模型 (Google Gemini) 的深度辅助下完成。** > 这是一个探索 **"AI 结对编程"** 极限的产物——展示了如何仅通过自然语言交互，在一个**单文件 (Single HTML)** 中构建出包含节点编辑器、多模态 API 调用、视频分析算法等复杂功能的现代化应用。

<br>

## 📖 简介 (Introduction)


**Tapnow Studio** 是一个运行在浏览器中的可视化 AI 工作流工具。它采用“节点编辑”的交互方式（类似 ComfyUI），将当前最强大的 AI 模型能力聚合在一个无限缩放的画布上。

它的核心理念是 **"轻量化"** 与 **"多模态协同"**。整个应用被打包在一个独立的 HTML 文件中，利用浏览器原生的能力和 CDN 资源，实现了复杂的 AI 交互逻辑。

<img width="1920" height="960" alt="2e8568e463c6473d89bc5be6ea5e57e8" src="https://github.com/user-attachments/assets/2020616f-204b-4aa7-854d-10e970cf5519" />

<br>
<br>

## ✨ 核心功能 (Key Features)

<br>

### 1. ♾️ 无限画布与节点系统
* **拖拽式连线**：直观地将输入（图片/视频）流转到处理节点。
* **无限缩放**：支持超大画布，利用鼠标滚轮自由缩放和平移。
* **多选与批量操作**：支持框选节点，批量移动或删除。
* **实时预览**：每个节点都具备独立的状态显示、进度条和结果预览。

<br>

### 2. 🎞️ 深度视频分析与反推 (Video Intelligence)
这是 Tapnow Studio 的杀手级功能，内置了复杂的视觉处理逻辑：
* **智能抽帧 (Smart Scene Detection)**：内置基于像素差值的场景检测算法 (`detectScenesAndCapture`)，自动识别视频镜头切换并提取关键帧。
* **导演级分镜拆解**：结合 Gemini 3 Pro 等多模态大模型，能够分析视频的**运镜手法**（推拉摇移）、**主体动态**、**光影氛围**。
* **提示词反推 (Reverse Prompting)**：自动将视频关键帧反推为 **Midjourney (英文)** 和 **即梦 (中文)** 的高精度提示词。
* **口播提取**：自动提取视频中的语音内容并生成时间轴脚本。

<br>

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

<br>

### 4. 🎥 AI 视频生成
支持主流视频生成模型的参数配置与任务轮询：
* **Sora**
* **Grok-3 Video**
* **Google Veo**
* **内置其他模型可供自行对接**

<br>

### 5. 🛠️ 实用辅助工具
* **图像对比 (Image Compare)**：带有滑动条合作的 AB 对比节点，方便查看原图与重绘图的差异。
* **批量素材管理**：内置历史记录管理器，支持批量删除、批量重新发送到画布。
* **暗黑/明亮模式**：自适应 UI 主题切换。

<br>

## 🚀 如何运行 (How to Run)

<br>

本项目保持了标志性的 **Single-file（单文件）** 架构，无需安装 Node.js 或 Python 环境。

<br>

1.  下载本仓库中的 `Tapnow Studio-V2.5-1.html` 文件。
2.  **双击**直接使用 Chrome / Edge 浏览器打开。
3.  点击右上角 **API 设置** 配置您的模型 Key 即可开始创作。

<br>

## 🚀 快速开始 (Quick Start)

<br>

### 方式 1：直接运行
1.  下载本仓库中的 `Tapnow Studio-V2.5.html` 文件。
2.  双击使用 Chrome, Edge 或 Safari 浏览器打开。
3.  点击右上角 **API 设置**，配置你的模型 Key 即可开始使用。

<br>

### 方式 2：本地开发
如果你想修改代码：
1.  该项目是一个单文件 React 应用，源码直接嵌入在 HTML 的 `<script type="text/babel">` 标签中。
2.  你可以直接使用 VS Code 编辑该 HTML 文件。
3.  依赖库（React, Tailwind, Lucide, Babel）均通过 CDN 加载，无需 `npm install`。

<br>

## 🔌 即梦 (Jimeng) API 配置指南

<br>

由于浏览器安全策略（CORS）及即梦 API 的特殊签名验证，**Tapnow Studio 需要配合后端代理服务使用即梦功能**。

本项目完美适配开源项目 **[jimeng-api](https://github.com/iptag/jimeng-api)**。

<br>

### 1. 部署后端服务
你可以选择以下任意一种方式在本地运行服务：

**选项 A：下载可执行文件 (.exe)** 前往 [jimeng-api Releases](https://github.com/iptag/jimeng-api/releases) 下载 Windows/Mac/Linux 版本并运行。

**选项 B：下载已配置好的.压缩包 (.7z)** JimengAPI_Release_V9_Green.7z（win版） JimengAPI_For_Mac_Users（mac版）

服务启动后，默认地址为 `http://localhost:5100`

<br>

### 2. 获取 Session ID

1.  在浏览器访问 [即梦官网 (jimeng.jianying.com)](https://jimeng.jianying.com/) 并登录。
2.  按 `F12` 打开开发者工具，点击 `Application` (应用) 标签页。
3.  在左侧栏找到 `Cookies` ，点击即梦的域名。
4.  复制 `sessionid` 的值。

<br>

### 3. 在 Tapnow Studio 中连接

1.  打开 Tapnow Studio 右上角的 **API 设置**。
2.  找到 **Jimeng** 相关的模型配置（或添加新模型）。
3.  **Base URL** 填入： `http://localhost:5100` 。
4.  **API Key** 填入：刚才复制的 `sessionid` 。
5.  *(可选)* 勾选设置底部的“即梦图生图使用本地文件”以获得更好的上传稳定性。

<br>

## ⚙️ 技术架构 (Technical Details)

<br>

Tapnow Studio 展示了现代前端技术在无构建工具（No-Build）环境下的极限能力：

* **Runtime**: 浏览器原生 ES Modules + Babel Standalone 实时编译 JSX。
* **UI Framework**: React 18 (UMD)。
* **Styling**: Tailwind CSS (Script Tag 注入)。
* **State Management**: React Hooks ( `useMemo` , `useCallback` , `useRef` ) 实现高性能画布渲染。
* **Storage**: `localStorage` 实现数据持久化（API Key、历史记录、画布状态）。
* **Network**: 原生 `fetch` API 处理 Server-Sent Events (SSE) 和长轮询。

<br>

## 🚀 Tapnow Studio V2.6-1 更新日志-（2025-12-21）

<br>

## ✨ 新增功能

<br>

### 1. 本地缓存服务器 (Local Cache Server)
**功能描述**：
支持连接本地服务器以接管资源管理，大幅提升加载速度并节省带宽。
* **连接配置**：默认支持连接 `http://127.0.0.1:9527`，提供可视化连接状态面板。
* **智能缓存**：
    * 自动缓存角色库图片及历史记录中的媒体文件。
    * 内置去重机制，智能检测已存在文件，避免重复下载。
* **加载加速**：资源加载时优先调用本地缓存 URL，实现秒级预览。

<br>

### 2. 保存到本地节点 (Local Save Node)
**功能描述**：
新增 `local-save` 节点，打通工作流与本地文件系统的存储通道。
* **自动保存**：开启后自动将上游图片/视频存入本地，支持批量处理与自动去重。
* **格式转换**：自动将 PNG 转换为高质量 JPG 格式，优化存储空间。
* **自定义配置**：支持设置保存子文件夹路径，实时反馈服务器连接状态。
* **操作模式**：支持全自动流式保存与手动触发保存。

<br>

### 3. 小说输入与 AI 分析
**功能描述**：
引入小说创作辅助工具链，实现从文本到视觉要素的自动提取。
* **小说输入节点 (`novel-input`)**：
    * 支持最大 **10,000字** 文本输入，配备实时字数统计。
    * 一键生成分析下游节点。
* **提取角色和场景节点 (`extract-characters-scenes`)**：
    * **角色提取**：自动解析姓名、身份、外貌描述、年龄、性别等元数据。
    * **场景提取**：智能识别场景名称与环境描述。
    * **可视化**：分类展示提取结果，支持多模型选择与实时进度显示。

<br>

### 4. 工作流管理升级
**功能描述**：
增强了工作流的便携性与复用性。
* **局部导出**：支持仅保存当前选中的节点和连接为工作流文件（V2.6 版本）。
* **流式处理**：采用 Blob 转 Base64 及流式写入技术，轻松处理大型工作流导出。
* **智能导入**：
    * 支持 JSON 格式导入并追加到当前画布。
    * 导入时智能匹配本地库文件，优先复用本地资源而非 Base64 数据。

<br>

### 5. 性能模式系统 (Performance Mode)
**功能描述**：
针对历史记录列表引入分级性能策略，解决长列表卡顿问题。
* **三种模式**：
    * **极速模式**：生成 80px 缩略图 (JPEG 质量 0.3)，极致流畅。
    * **普通模式**：生成 150px 缩略图 (JPEG 质量 0.6)，平衡清晰度与性能。
    * **关闭**：显示原图。
* **批量处理**：支持 Midjourney 多图缩略图生成，采用分批处理（每次 5 个）避免阻塞主线程。

<br>

### 6. 渲染引擎深度调优
**功能描述**：
从底层 CSS 到交互逻辑的全方位优化。
* **交互节流**：
    * 画布拖动采用微型节流 (~10ms) 与 `requestAnimationFrame`。
    * 优化多节点拖动的批量更新机制，减少重绘次数。
* **GPU 加速与降级**：
    * 节点容器启用 `transform: translateZ(0)` 硬件加速。
    * 高性能模式下自动禁用阴影、模糊与过渡动画。
    * 交互过程中动态降级渲染质量，视口外媒体自动卸载。
* **文本与线条**：优化全局字体抗锯齿渲染及连接线几何精度。

<br>

### 7. 缓存机制增强
* **计算结果缓存**：优化连接输入（图片/视频）的计算缓存，减少重复运算。
* **缩略图 Map**：构建内存级 Map 索引缓存缩略图 URL，防止重复生成。
* **加载优先级策略**：
    1. 本地缓存文件 (Local Cache)
    2. 性能模式缩略图 (Thumbnail)
    3. 原始网络 URL (Original)

<br>

## ⚡ 历史更新及功能日志

<br>

> **❤️ 欢迎各路大佬协助更新**

[ 历史更新日志.md](https://github.com/zhengxinlan1995-code/Tapnow-Studio--/blob/1df915525f515f10b57805895e3a20f95c13c985/%E5%8E%86%E5%8F%B2%E6%9B%B4%E6%96%B0%E6%97%A5%E5%BF%97.md)

<br>

## 🤝 致谢与声明 (Credits)

* **AI Architecture**: 本项目的核心逻辑、UI 组件及架构设计由 **Gemini** 辅助完成。
* **Jimeng Support**: 即梦接口支持由 **[iptag/jimeng-api](https://github.com/iptag/jimeng-api)** 提供，这是一个非常棒的逆向工程项目。
* **Icons**: 使用 [Lucide](https://lucide.dev/) 图标库。

<br>

## ⚠️ 免责声明 (Disclaimer)

<br>

本项目仅供学习与技术研究使用。

* 请勿将本项目用于任何非法用途。
* 使用即梦、Midjourney 等服务时，请遵守相应服务商的使用条款。
* 用户需自行管理 API Key，本项目不会上传任何 Key 到云端。

## 📄 许可证 (License)

<br>

本项目采用 **GNU General Public License v3.0 (GPLv3)** 开源协议。

这意味着：
* ✅ 你可以免费使用、复制、修改和分发本项目。
* ✅ 你可以将本项目用于商业用途。
* ⚠️ **但是**，如果你修改了本项目并发布（分发），你**必须**开源你的修改代码，并同样使用 GPLv3 协议。
* 🚫 你**不能**将本项目闭源后作为商业软件出售。
