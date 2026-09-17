# ChatQT

一个基于 PySide6 的桌面 GPT 客户端，对接任意 OpenAI 兼容的 `/v1` 接口（默认 `https://rkapi.com/v1`，已用 `gpt-5.6-sol` / `gpt-5.6-terra` / `gpt-6-astra` 等模型验证流式与图片输入）。

白色主题、全部直角边框、Markdown 渲染、图片上传、会话本地持久化与自动命名。设计规范见 [DESIGN.md](DESIGN.md)。

## 功能

- **对话**：流式输出（可关闭）、停止生成、重新生成、复制 / 删除单条消息、多轮上下文、Token 用量统计
- **图片**：点击按钮 / `Ctrl+U` 选择、直接粘贴剪贴板图片、拖拽文件到输入框；自动缩放到 1600px 内并以 PNG 存入数据目录，随消息一起发送给视觉模型
- **Markdown**：标题、列表、表格、引用、分隔线、链接、行内代码、带语言标签与语法高亮的代码块
- **会话管理**：启动时自动加载全部会话；搜索（`Ctrl+K`）、置顶、重命名（双击标题或右键）、导出 Markdown、删除（同时删除关联图片）；首轮回复后自动生成会话名
- **接口设置**（左下角）：Base URL、API Key、模型（可从 `/models` 拉取）、系统提示词、temperature / max tokens、流式 / 自动命名 / 回车发送开关、测试连接
- **数据文件夹**（左下角）：查看统计、在文件管理器中打开、更换目录（可选迁移已有会话和图片）

## 运行

需要 Python 3.10+。

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py                     # 或 python -m chatqt
```

首次启动若未配置 API Key，会自动弹出「接口设置」。也可以通过环境变量 `CHATQT_API_KEY` 预置。

Linux 无显示环境下的冒烟测试（会真实请求接口）：

```bash
CHATQT_API_KEY=sk-... xvfb-run -a python scripts/smoke.py
```

## 下载 / 打包 exe

- **直接下载**：每次推送到 `main` 后，GitHub Actions 的 [Build](../../actions/workflows/build.yml) 工作流会在 Artifacts 里产出 `ChatQT-windows-x64`（单文件 exe，免安装）。推送 `v*` 标签（如 `git tag v0.1.0 && git push origin v0.1.0`）会自动创建 Release 并附上 exe。
- **本地打包**：

  ```bash
  pip install pyinstaller
  pyinstaller --noconfirm --clean chatqt.spec    # 产物在 dist/ChatQT.exe（Linux/macOS 为 dist/ChatQT）
  ```

  图标由 `scripts/make_icon.py` 生成到 `chatqt/assets/icon.{png,ico}`。exe 未做代码签名，Windows SmartScreen 首次运行可能提示「更多信息 → 仍要运行」。

## 快捷键

| 快捷键 | 作用 |
|---|---|
| `Enter` / `Shift+Enter` | 发送 / 换行（可在设置里改为 `Ctrl+Enter` 发送） |
| `Ctrl+N` | 新对话 |
| `Ctrl+K` | 搜索会话 |
| `Ctrl+U` | 添加图片 |
| `Ctrl+L` | 聚焦输入框 |
| `Ctrl+,` | 接口设置 |
| `Ctrl+Shift+E` | 导出当前会话为 Markdown |
| `Esc` | 停止生成 |
| `Delete` | 删除侧栏中选中的会话 |

## 数据存放

- 设置文件：`~/.config/chatqt/settings.json`（Windows 为 `%APPDATA%\chatqt\settings.json`），包含 API Key，请勿提交到仓库
- 数据目录（默认 `~/.local/share/chatqt`，可在「数据文件夹」中更换）：
  - `conversations/<id>.json` — 每个会话一个文件
  - `images/<id>.png` — 上传的图片

## 项目结构

```
chatqt/
  app.py              启动、字体加载、调色板与样式
  config.py           默认值与 Settings 持久化
  storage.py          Conversation / Message 模型与 Store
  api.py              OpenAI 兼容请求、流式 / 标题 / 模型列表线程
  markdown_render.py  Markdown → Qt 富文本
  theme.py            设计令牌与 QSS
  icons.py            内置线性 SVG 图标
  widgets.py          消息、输入框、附件、侧栏行等组件
  dialogs.py          接口设置、数据文件夹对话框
  main_window.py      主窗口与交互逻辑
scripts/smoke.py      端到端冒烟测试（Xvfb）
scripts/make_icon.py  生成应用图标
chatqt.spec           PyInstaller 打包配置
.github/workflows/build.yml  Lint + Windows exe 构建 / 发布
```
