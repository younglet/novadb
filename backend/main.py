"""
NovaDB v3 — 每个 JSON 对象 = id(账号) + token(密码) 一对一配对
"""

import json
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, field_validator

from database import (
    init_db, list_by_user, get_by_id, create, update, delete,
    get_history, get_history_entry, restore_from_history,
)

MAX_DATA_SIZE       = 256 * 1024   # 单个 JSON 上限 256KB
MAX_OBJECTS_PER_USER = 10           # 每用户最多 10 个数据对象
WRITE_RATE_LIMIT     = 5            # 每秒最多写入次数


class RateLimiter:
    def __init__(self, max_req=5, window_sec=1.0):
        self.max = max_req
        self.win = window_sec
        self._b = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        b = self._b[key]
        cut = now - self.win
        while b and b[0] < cut:
            b.pop(0)
        if len(b) >= self.max:
            return False
        b.append(now)
        return True

rl = RateLimiter(WRITE_RATE_LIMIT, 1.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="NovaDB", version="3.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Models ──
class LoginRequest(BaseModel):
    username: str

class CreateRequest(BaseModel):
    label: str = ""
    private: bool = True
    data: dict

    @field_validator("data")
    @classmethod
    def must_be_object(cls, v):
        if not isinstance(v, dict):
            raise ValueError("data 必须是 JSON 对象（{}）")
        return v

class UpdateRequest(BaseModel):
    token: str
    label: str = ""
    private: bool = True
    data: dict

    @field_validator("data")
    @classmethod
    def must_be_object(cls, v):
        if not isinstance(v, dict):
            raise ValueError("data 必须是 JSON 对象（{}）")
        return v

class DeleteRequest(BaseModel):
    token: str


def _require_user(request: Request) -> str:
    uid = request.headers.get("X-User-Id") or request.query_params.get("user_id")
    if not uid:
        raise HTTPException(401, "请先登录")
    return uid

def _check_size(data: dict) -> int:
    raw = json.dumps(data, ensure_ascii=False)
    sz = len(raw.encode("utf-8"))
    if sz > MAX_DATA_SIZE:
        raise HTTPException(413, f"数据过大：{sz} bytes（上限 {MAX_DATA_SIZE} bytes）")
    return sz

def _fmt(row: dict) -> dict:
    return {
        "data_id": row["data_id"],
        "token": row["token"],
        "label": row["label"],
        "private": bool(row["private"]),
        "data": json.loads(row["data"]),
        "updatetime": row["updatetime"],
    }


# ── Auth ──
@app.post("/novadb/api/user/login")
def login(body: LoginRequest):
    uid = body.username.strip().lower()
    if not uid or len(uid) > 64:
        raise HTTPException(400, "用户名需 1-64 个字符")
    return {"user_id": uid}


# ── Data CRUD ──
@app.get("/novadb/api/db")
def list_objects(request: Request):
    """列出当前用户的所有数据对象"""
    uid = _require_user(request)
    objs = list_by_user(uid)
    return {"objects": objs}


@app.post("/novadb/api/db")
def create_object(request: Request, body: CreateRequest):
    """创建一个数据对象，返回 data_id + token（凭证对）"""
    uid = request.headers.get("X-User-Id") or request.query_params.get("user_id") or ""
    if not rl.allow(uid or "anon"):
        raise HTTPException(429, f"写入频率过高")
    # Check object count limit
    if uid:
        existing = list_by_user(uid)
        if len(existing) >= MAX_OBJECTS_PER_USER:
            raise HTTPException(400, f"数据对象已达上限（{MAX_OBJECTS_PER_USER} 个），请删除旧数据后再创建")
    _check_size(body.data)
    data_json = json.dumps(body.data, ensure_ascii=False)
    did, tok = create(uid, body.label.strip(), body.private, data_json)
    row = get_by_id(did)
    return _fmt(row)


@app.get("/novadb/api/db/{data_id}")
def read_object(data_id: str, token: str = Query(None)):
    """读取数据 — 公开直接读，私有需 ?token=xxx"""
    row = get_by_id(data_id.strip())
    if not row:
        raise HTTPException(404, "数据不存在")
    if row["private"] and (not token or token.strip() != row["token"]):
        raise HTTPException(404, "数据不存在或未公开")
    return _fmt(row)


@app.put("/novadb/api/db/{data_id}")
def update_object(data_id: str, body: UpdateRequest):
    """更新数据（需正确的 token）"""
    if not rl.allow(body.token.strip()):
        raise HTTPException(429, f"写入频率过高")
    _check_size(body.data)
    data_json = json.dumps(body.data, ensure_ascii=False)
    ok = update(data_id.strip(), body.token.strip(), body.label.strip(), body.private, data_json)
    if not ok:
        raise HTTPException(404, "data_id 不存在或 token 不匹配")
    row = get_by_id(data_id.strip())
    return _fmt(row)


@app.delete("/novadb/api/db/{data_id}")
def delete_object(data_id: str, body: DeleteRequest):
    """删除数据（需正确的 token）"""
    ok = delete(data_id.strip(), body.token.strip())
    if not ok:
        raise HTTPException(404, "data_id 不存在或 token 不匹配")
    return {"ok": True}


# ── History ─────────────────────────────────────────────────────

class RestoreRequest(BaseModel):
    token: str
    history_id: int


@app.get("/novadb/api/db/{data_id}/history")
def get_object_history(data_id: str, token: str = Query(...)):
    """获取历史版本列表（需 token）"""
    row = get_by_id(data_id.strip())
    if not row or row["token"] != token.strip():
        raise HTTPException(404, "data_id 不存在或 token 不匹配")
    entries = get_history(data_id.strip())
    return {"history": entries}


@app.post("/novadb/api/db/{data_id}/restore")
def restore_object(data_id: str, body: RestoreRequest):
    """恢复某个历史版本"""
    ok = restore_from_history(data_id.strip(), body.token.strip(), body.history_id)
    if not ok:
        raise HTTPException(404, "恢复失败：data_id、token 或历史版本不存在")
    row = get_by_id(data_id.strip())
    return _fmt(row)


# ── Frontend SPA ──
frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")
_index_html = os.path.join(frontend_dir, "index.html")

if os.path.isfile(_index_html):
    @app.get("/novadb")
    async def _redir():
        return RedirectResponse(url="/novadb/")

    @app.get("/novadb/")
    async def _index():
        return FileResponse(_index_html)

    @app.get("/novadb/{path:path}")
    async def _spa(path: str):
        fp = os.path.join(frontend_dir, path)
        if os.path.isfile(fp):
            return FileResponse(fp)
        return FileResponse(_index_html)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
