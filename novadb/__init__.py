"""
NovaDB Python Client — 极简 JSON 数据库 SDK

    from novadb import NovaDB

    # 新建数据
    db = NovaDB()
    db.set({"score": 99}, label="游戏存档")
    print(db.data_id, db.token)  # 保存凭证！

    # 读取数据
    db2 = NovaDB("a1b2c3d4e5f6g7")
    print(db2.get())

    # 修改数据
    db3 = NovaDB("a1b2c3d4e5f6g7", "stu_xxxxxxxx")
    db3.set({"score": 100})

    # 删除
    db3.delete()
"""

import requests

BASE_URL = "http://localhost:8000/novadb/api"


class NovaDB:
    def __init__(self, data_id=None, token=None, *,
                 base_url="http://localhost:8000/novadb/api"):
        self.data_id = data_id
        self.token = token
        self.base_url = base_url.rstrip("/")

    def get(self):
        """读取数据。公开数据无需 token，私有数据需在构造时传入 token。"""
        url = f"{self.base_url}/db/{self.data_id}"
        if self.token:
            url += f"?token={self.token}"
        resp = requests.get(url)
        resp.raise_for_status()
        body = resp.json()
        self.token = body.get("token") or self.token
        return body["data"]

    def set(self, data, *, label=None, private=None):
        """写入或更新数据。若 data_id 不存在则自动创建。"""
        if not isinstance(data, dict):
            raise TypeError("data 必须是 dict（JSON 对象）")

        if self.data_id is None:
            # 创建新对象 — 需指定 private
            payload = {"data": data}
            if label is not None:
                payload["label"] = label
            payload["private"] = True if private is None else private
            resp = requests.post(f"{self.base_url}/db", json=payload)
        else:
            if not self.token:
                raise ValueError("更新数据需要 token：NovaDB(data_id, token)")
            payload = {"token": self.token, "data": data}
            if label is not None:
                payload["label"] = label
            if private is not None:
                payload["private"] = private
            resp = requests.put(f"{self.base_url}/db/{self.data_id}", json=payload)

        resp.raise_for_status()
        body = resp.json()
        self.data_id = body["data_id"]
        self.token = body["token"]
        return body["data"]

    def delete(self):
        """删除数据（需要 token）。"""
        if not self.data_id or not self.token:
            raise ValueError("删除需要 data_id 和 token")
        resp = requests.delete(
            f"{self.base_url}/db/{self.data_id}",
            json={"token": self.token},
        )
        resp.raise_for_status()
        self.data_id = None
        self.token = None
        return True
