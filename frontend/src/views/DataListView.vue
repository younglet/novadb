<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api/index.js'

const router = useRouter()
const objects = ref([])
const loading = ref(true)
const error = ref('')
const copied = ref('')

const showCreate = ref(false)
const creating = ref(false)
const newLabel = ref('')
const newPrivate = ref(true)
const newCredential = ref(null)

onMounted(loadAll)

async function loadAll() {
  loading.value = true; error.value = ''
  try {
    const data = await api.listObjects()
    objects.value = data.objects || []
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function doCreate() {
  creating.value = true
  try {
    const result = await api.createObject(newLabel.value, {}, newPrivate.value)
    showCreate.value = false
    newLabel.value = ''
    newCredential.value = { data_id: result.data_id, token: result.token }
    await loadAll()
  } catch (e) {
    error.value = e.message
  } finally {
    creating.value = false
  }
}

async function doDelete(obj) {
  if (!confirm(`确定删除「${obj.label || obj.data_id}」？`)) return
  try {
    await api.deleteObject(obj.data_id, obj.token)
    await loadAll()
  } catch (e) {
    error.value = e.message
  }
}

function copy(val) {
  navigator.clipboard.writeText(val)
  copied.value = val
  setTimeout(() => { copied.value = '' }, 2000)
}

function copyShareUrl(dataId) {
  const url = `${window.location.origin}/novadb/api/db/${dataId}`
  navigator.clipboard.writeText(url)
  copied.value = 'share_' + dataId
  setTimeout(() => { copied.value = '' }, 2000)
}

function goEditor(dataId, token) {
  router.push({ path: `/editor/${dataId}`, query: { token } })
}

function sizeKB(bytes) {
  return (bytes / 1024).toFixed(1) + ' KB'
}

function dismissCredential() {
  newCredential.value = null
}
</script>

<template>
  <div class="page">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;">
      <h1 style="margin-bottom:0;">我的数据</h1>
      <button class="btn-primary" @click="showCreate = true">＋ 新建</button>
    </div>

    <!-- New credential banner -->
    <div v-if="newCredential" class="msg success" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
      <div>
        ✅ 创建成功，请保存凭证<br/>
        <code style="color:var(--accent);">id: {{ newCredential.data_id }}</code>
        &nbsp;&nbsp;
        <code style="color:var(--orange);">token: {{ newCredential.token }}</code>
      </div>
      <div style="display:flex;gap:6px;">
        <button class="btn-sm" @click="copy(newCredential.token)">{{ copied === newCredential.token ? '✅' : '📋 复制 token' }}</button>
        <button class="btn-sm btn-ghost" @click="dismissCredential">✕</button>
      </div>
    </div>

    <div v-if="error" class="msg error">{{ error }}</div>
    <div v-if="loading" style="text-align:center;padding:60px;color:var(--muted);">加载中…</div>

    <div v-else-if="objects.length === 0" class="empty">
      <div class="icon">📭</div>
      <p>还没有数据，点击「＋ 新建」创建第一个</p>
    </div>

    <div v-else class="token-grid">
      <div v-for="obj in objects" :key="obj.data_id" class="token-card">
        <div class="token-label">{{ obj.label || '未命名' }}</div>

        <div class="token-code-row">
          <span class="key-label">id</span>
          <code style="color:var(--accent);">{{ obj.data_id }}</code>
          <button class="btn-sm copy-btn" @click="copy(obj.data_id)">
            {{ copied === obj.data_id ? '✅' : '📋' }}
          </button>
        </div>

        <div class="token-code-row">
          <span class="key-label">token</span>
          <code style="color:var(--orange);">{{ obj.token }}</code>
          <button class="btn-sm copy-btn" @click="copy(obj.token)">
            {{ copied === obj.token ? '✅' : '📋' }}
          </button>
        </div>

        <div class="token-meta" style="margin-top:6px;">
          <span>{{ obj.private ? '🔒 私有' : '🌐 公开' }}</span>
          <span>📦 {{ sizeKB(obj.size_bytes) }}</span>
          <span v-if="!obj.private" style="cursor:pointer;color:var(--accent);" @click="copyShareUrl(obj.data_id)">
            {{ copied === 'share_' + obj.data_id ? '✅ 已复制' : '🔗 复制分享链接' }}
          </span>
        </div>
        <div class="token-meta">
          <span>🕐 {{ obj.updatetime || '-' }}</span>
        </div>

        <div class="token-actions">
          <button @click="goEditor(obj.data_id, obj.token)">✏️ 编辑</button>
          <button class="btn-danger btn-sm" @click="doDelete(obj)">🗑 删除</button>
        </div>
      </div>
    </div>

    <!-- Create modal -->
    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal">
        <h3>新建数据</h3>
        <div class="field">
          <label>标签（可选）</label>
          <input type="text" v-model="newLabel" @keyup.enter="doCreate" placeholder="游戏存档" autofocus />
        </div>
        <div class="toggle-row" style="border-top:none;margin:0;padding:8px 0;">
          <span>{{ newPrivate ? '🔒 私有' : '🌐 公开' }}</span>
          <label class="switch">
            <input type="checkbox" :checked="!newPrivate" @change="newPrivate = !newPrivate" />
            <span class="slider"></span>
          </label>
        </div>
        <div class="actions">
          <button class="btn-ghost" @click="showCreate = false">取消</button>
          <button class="btn-primary" @click="doCreate" :disabled="creating">
            {{ creating ? '创建中…' : '创建' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
