# 企业知识与流程协同平台

一个面向企业 IT 支持场景的小型演示项目：员工提问后，系统检索内部知识文档、给出带来源的回答；遇到需要人工处理的问题，先生成待确认操作，审批后再创建工单。

## 做到了什么

- 通过 LangGraph 串起检索、回答和操作预览流程；本地 Markdown 文档使用 TF-IDF 检索。
- 知识文档可新增、重建索引；回答保留来源，便于核对。
- 工单操作先预览，再由人工批准或拒绝；查询、操作和工单记录落库。
- Vue 3 页面展示问答、知识库、待办操作和统计数据；Redis 可用时缓存普通问答，不可用时仍可运行。

默认回答以检索结果和规则模板为主；配置 `LLM_API_KEY` 后可以调用兼容接口生成回答，但这条可选路径不依赖模型也能运行。这里的 LangGraph 用来编排流程，不应把项目描述为自主 Agent。

## 本地运行

需要 Python 3.11+、Node.js 和 pnpm。默认使用 SQLite，无需先安装 MySQL 或 Redis。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8001
```

另开一个终端启动前端：

```powershell
cd frontend
pnpm install
pnpm dev
```

打开 `http://127.0.0.1:5173`；接口文档在 `http://127.0.0.1:8001/docs`。如要改用 MySQL 或配置模型，在项目根目录的 `.env` 设置相应变量（可参考 `.env.example`）；Redis 可用 `REDIS_URL` 指定。不要提交 `.env`。

## 验证与边界

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

这是本地演示项目，没有实现生产环境所需的账号权限、审计策略和模型安全控制。涉及工单的操作保留人工确认，是为了避免“问一句就自动执行”的风险。

