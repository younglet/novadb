const BASE = '/novadb/api'

function headers() {
  const h = { 'Content-Type': 'application/json' }
  const uid = localStorage.getItem('novadb_user_id')
  if (uid) h['X-User-Id'] = uid
  return h
}

async function request(method, path, body) {
  const opts = { method, headers: headers() }
  if (body) opts.body = JSON.stringify(body)
  const res = await fetch(`${BASE}${path}`, opts)
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || '请求失败')
  return data
}

export const api = {
  login(username) {
    return request('POST', '/user/login', { username })
  },

  // Data objects
  listObjects() {
    return request('GET', '/db')
  },
  createObject(label, data, isPrivate) {
    return request('POST', '/db', { label, private: isPrivate, data })
  },
  readObject(dataId, token) {
    const q = token ? `?token=${encodeURIComponent(token)}` : ''
    return fetch(`${BASE}/db/${dataId}${q}`).then(r => r.json().then(d => {
      if (!r.ok) throw new Error(d.detail || '读取失败')
      return d
    }))
  },
  updateObject(dataId, token, label, data, isPrivate) {
    return request('PUT', `/db/${dataId}`, { token, label, private: isPrivate, data })
  },
  deleteObject(dataId, token) {
    return request('DELETE', `/db/${dataId}`, { token })
  },

  // History
  getHistory(dataId, token) {
    return request('GET', `/db/${dataId}/history?token=${encodeURIComponent(token)}`)
  },
  restoreVersion(dataId, token, historyId) {
    return request('POST', `/db/${dataId}/restore`, { token, history_id: historyId })
  },
}

export function getUserId() {
  return localStorage.getItem('novadb_user_id') || ''
}

export function setUserId(uid) {
  localStorage.setItem('novadb_user_id', uid)
}
