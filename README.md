# 💾 NovaDB

> 给你的 Python 程序装上「数据硬盘」。无需安装数据库，一行 POST，永久保存。

## 亮点

- ✅ **零依赖部署** — 不用装 MySQL、不用建表、不用写 SQL
- ✅ **id + token 凭证对** — 每个 JSON 对象像账号密码：id 公开分享，token 保密修改
- ✅ **公开 / 私有切换** — 一键设为公开，生成链接发给同学直接看
- ✅ **256KB 存储** — 足够存游戏存档、配置、待办，覆盖 95% 教学场景
- ✅ **50 条历史记录** — 每次变更自动存档，支持 Git 风格 diff 对比，一键恢复
- ✅ **智能保存** — 自动去重，顺序变化提示确认，无变化不产生历史
- ✅ **Python SDK** — `from novadb import NovaDB`，三行代码读写数据
- ✅ **在线编辑器** — 语法高亮、实时校验、代码示例即时生成

---

## 快速开始

### Docker

```bash
docker-compose up -d
# 打开 http://localhost:8000/novadb/
```

### 本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# 前端
cd frontend
npm install
npm run dev

# 访问 http://localhost:5173/novadb/
```

---

## 核心概念

```
每个数据对象 = data_id（公开定位） + token（保密修改）

  data_id: a1b2c3d4e5f6g7   ← 可以公开，放 URL
  token:   stu_xxxxxxxx     ← 自己保管，用于修改/删除
  data:    {"score": 99}
```

---

## API 参考

所有接口挂载于 `/novadb/api/`。

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/db` | 创建数据 → 返回 `data_id` + `token` |
| `GET` | `/db/{data_id}` | 读取数据（公开免鉴权，私有需 `?token=xxx`） |
| `PUT` | `/db/{data_id}` | 更新数据（需 `{token, data}`，支持 `force` 参数强制保存顺序变化） |
| `DELETE` | `/db/{data_id}` | 删除数据（需 `{token}`） |
| `GET` | `/db?user_id=xxx` | 列出用户的所有数据对象 |
| `GET` | `/db/{data_id}/history?token=xxx` | 获取历史版本列表 |
| `POST` | `/db/{data_id}/restore` | 恢复某个历史版本 |

### 请求示例

```bash
# 创建数据
curl -X POST http://localhost:8000/novadb/api/db \
  -H "Content-Type: application/json" \
  -d '{"data": {"score": 99}, "private": false}'

# 返回
{ "data_id": "a1b2c3d4e5f6g7", "token": "stu_xxxxxxxx", ... }

# 公开读取
curl http://localhost:8000/novadb/api/db/a1b2c3d4e5f6g7

# 修改（需 token）
curl -X PUT http://localhost:8000/novadb/api/db/a1b2c3d4e5f6g7 \
  -H "Content-Type: application/json" \
  -d '{"token": "stu_xxxxxxxx", "data": {"score": 100}}'
```

### 权限规则

| 操作 | 公开数据 | 私有数据 |
|------|---------|---------|
| 读取 | 无需 token | 需 token |
| 修改 | **需 token** | **需 token** |
| 删除 | **需 token** | **需 token** |

---

## Python SDK

```bash
pip install requests
# 将 novadb/ 目录放到项目中即可
```

```python
from novadb import NovaDB

# 读取公开数据
db = NovaDB("a1b2c3d4e5f6g7")
print(db.get())  # {'score': 99}

# 修改数据（需 token）
db = NovaDB("a1b2c3d4e5f6g7", "stu_xxxxxxxx")
db.set({"score": 100})

# 删除
db.delete()

# 如需连接到非本地服务
import novadb
novadb.BASE_URL = "https://your-server.com/novadb/api"
```

SDK 仅 `get()` / `set()` / `delete()` 三个方法，零学习成本。

---

## 项目结构

```
novadb/
├── backend/
│   ├── main.py              # FastAPI 应用，10 个路由 + 限流
│   ├── database.py           # SQLite 数据层（user_objects + object_history）
│   ├── requirements.txt      # fastapi + uvicorn
│   └── Dockerfile            # 多阶段构建（Node → Python）
├── frontend/                 # Vue 3 + Vite
│   ├── src/
│   │   ├── views/
│   │   │   ├── LandingView.vue   # 首页（项目亮点）
│   │   │   ├── LoginView.vue     # 登录
│   │   │   ├── DataListView.vue  # 数据管理（卡片网格）
│   │   │   └── EditorView.vue    # JSON 编辑器 + 历史 + diff + 代码示例
│   │   ├── api/index.js
│   │   └── router/index.js
│   └── vite.config.js
├── novadb/                  # Python SDK
│   └── __init__.py
└── docker-compose.yml
```

## 可配置常量

```python
# backend/main.py
MAX_DATA_SIZE        = 256 * 1024   # 单个 JSON 上限 256KB
MAX_OBJECTS_PER_USER = 10           # 每用户最多 10 个数据对象
WRITE_RATE_LIMIT     = 5            # 每秒最多写入次数
```

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | FastAPI + SQLite (WAL mode) |
| 前端 | Vue 3 + Vue Router + Vite |
| SDK | Python (requests) |
| 部署 | Docker + docker-compose |
