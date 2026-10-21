# DataPilot Studio

面向短视频平台运营场景的Text2SQL项目，包含 Vue 前端、FastAPI + LangGraph 后端、41 张 CSV 数据表、字段级 Schema 索引、测试脚本和当前评测报告。

## 环境要求

- Python 3.11
- Node.js 20.19 或更高版本
- 兼容 OpenAI 接口的大模型、Embedding 和 Rerank 服务

## 安装

以下命令均从解压后的项目根目录执行。

后端（Windows PowerShell）：

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

后端（macOS / Linux）：

```bash
cd backend
python3.11 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

编辑 `backend/.env`，填写 `LLM_API_KEY`。默认模型配置为 `qwen3.7-plus`、`text-embedding-v4` 和 `qwen3-rerank`。

前端：

```powershell
cd frontend
npm install
```

## 启动

分别打开两个终端。

后端（Windows）：

```powershell
cd backend
.\.venv\Scripts\python.exe run.py
```

后端（macOS / Linux）：

```bash
cd backend
./.venv/bin/python run.py
```

前端：

```powershell
cd frontend
npm run dev
```

访问 `http://127.0.0.1:5173`，API 文档位于 `http://127.0.0.1:8000/docs`。

## 测试

在 `backend` 目录执行：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
.\.venv\Scripts\python.exe scripts\validate_short_video_ops.py
```

评测命令与指标说明见 `backend/evaluation/README.md`。现有评测结果位于 `backend/evaluation/results`。

## 测试账号

- 管理员：`admin` / `admin123`
- 用户增长运营：`growth` / `growth123`
- 渠道投放运营：`channel` / `channel123`
- 内容运营：`content` / `content123`
