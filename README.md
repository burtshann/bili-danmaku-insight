# Bili Danmaku Insight

一个面向 Bilibili 视频内容分析的前后端分离项目。输入公开视频链接后，可以统计弹幕高频词、定位弹幕最密集的时间段、导出视频元数据，并在本地按需下载视频。

项目由 React 前端和 Django 后端组成，保留了 Windows 一键启动/停止方式，适合作为 Python Web、数据采集与可视化方向的求职作品。

## 功能

- 弹幕抓取与中文分词，展示 Top 5 高频词
- 柱状图、折线图、散点图三种 ECharts 视图
- 计算连续 3 秒内弹幕最密集的精彩时间段
- 提取标题、UP 主、播放量、点赞、收藏等数据并导出 Excel
- 使用 `yt-dlp` 下载视频，Cookie 为本地可选配置
- 下载等待期间可选启动 Pygame 小游戏
- Windows 一键初始化、启动和停止前后端服务

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 前端 | React 17、Axios、ECharts、Bootstrap、ReactPlayer |
| 后端 | Python、Django 5、django-cors-headers |
| 数据处理 | Requests、BeautifulSoup、jieba、openpyxl |
| 媒体处理 | yt-dlp、Pygame |

## 项目结构

```text
bili-danmaku-insight/
├─ backend/                 # Django API
│  ├─ djangoProject1/       # 配置与路由
│  ├─ myapp/                # 弹幕分析、导出和下载逻辑
│  ├─ cookie/               # 可选 Cookie，本地文件不会提交
│  ├─ download/             # 运行时生成的视频和 Excel
│  └─ manage.py
├─ frontend/                # React 页面与 ECharts 可视化
├─ scripts/                 # Windows 初始化与服务管理脚本
├─ start_project.bat        # 双击启动
└─ stop_project.bat         # 双击停止
```

## 本地运行

环境要求：Python 3.11+、Node.js 18+、npm。视频合并功能还需要系统可用的 FFmpeg。

首次运行，在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

初始化完成后，可以双击 `start_project.bat`，或执行：

```powershell
.\start_project.bat
```

浏览器访问 `http://localhost:3000`。停止前后端服务时运行：

```powershell
.\stop_project.bat
```

也可以分别启动：

```powershell
# 后端
.\backend\.venv\Scripts\python.exe .\backend\manage.py runserver 127.0.0.1:8000

# 前端（另开终端）
cd .\frontend
npm start
```

## 环境变量

`setup.ps1` 会在根目录不存在 `.env` 时从 `.env.example` 创建一份。常用配置如下：

| 变量 | 默认用途 |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django 密钥，部署时必须更换 |
| `DJANGO_DEBUG` | 是否启用调试模式 |
| `DJANGO_ALLOWED_HOSTS` | 允许访问后端的主机列表 |
| `REQUEST_VERIFY_SSL` | 是否校验外部请求的 TLS 证书 |
| `ENABLE_WAITING_GAME` | 下载时是否启动等待小游戏 |
| `REACT_APP_API_BASE_URL` | React 使用的 Django API 地址 |

需要使用登录态下载时，可把 Netscape 格式 Cookie 保存为 `backend/cookie/cookie.txt`。该文件已被 `.gitignore` 排除，请勿提交账号 Cookie。

## API

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `POST` | `/get_high_freq_data/` | 获取弹幕高频词与词频 |
| `POST` | `/get_max_danmaku/` | 获取弹幕峰值时间段 |
| `POST` | `/download_excel/` | 生成并下载视频数据 Excel |
| `POST` | `/download_video/` | 下载视频到本地运行目录 |

请求示例：

```json
{
  "danmaku": "https://www.bilibili.com/video/BV..."
}
```

## 测试与构建

```powershell
.\backend\.venv\Scripts\python.exe .\backend\manage.py test myapp
cd .\frontend
npm run build
```

## 项目亮点

- 用 Django 提供 JSON API，React 负责交互与图表展示，职责边界清晰
- 对网络失败、无效 URL、弹幕 XML 异常和空数据提供统一错误响应
- 使用滑动时间窗口从弹幕时间序列中定位高互动片段
- 敏感配置、Cookie、数据库、下载文件和依赖目录均不进入版本库
- 提供可复现的初始化流程与一键启停入口，降低本地体验成本

## 使用说明

本项目用于学习、作品展示和对公开可访问数据的本地分析。使用者应遵守 Bilibili 服务条款、版权规则及所在地法律法规；请勿用于批量抓取、绕过访问控制或传播未获授权的内容。

前端最初基于 `react-landing-page-template` 改造，其原始 MIT 许可证保留在 `frontend/LICENSE`。

