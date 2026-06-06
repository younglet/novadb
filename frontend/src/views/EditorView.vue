<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api/index.js'

const route = useRoute()
const router = useRouter()
const dataId = computed(() => route.params.dataId)
const queryToken = computed(() => route.query.token || '')

const token = ref('')
const label = ref('')
const EMPTY = `{
  
}`
const code = ref(EMPTY)
const isPrivate = ref(true)

async function togglePrivate() {
  isPrivate.value = !isPrivate.value
  if (!token.value) return
  try {
    const p = JSON.parse(code.value)
    await api.updateObject(dataId.value, token.value, label.value, p, isPrivate.value)
    showToast(isPrivate.value ? '已设为私有' : '已设为公开', 'success')
  } catch (e) { showToast(e.message, 'error'); isPrivate.value = !isPrivate.value }
}
const updatetime = ref('')
const loading = ref(false)
const saving = ref(false)
const msg = ref(null)
const jsonError = ref('')

// Toast notification
const toast = ref(null)
let toastTimer = null
function showToast(text, type) {
  clearTimeout(toastTimer)
  toast.value = { text, type }
  toastTimer = setTimeout(() => { toast.value = null }, 2500)
}

// Order-only modal
const showOrderModal = ref(false)
const orderBefore = ref('')
const orderAfter = ref('')

// Track stored data for comparison
const storedData = ref(null)

const MAX_SIZE = 256 * 1024
const codeTab = ref('novadb')
const copiedBlock = ref('')

const apiBase = computed(() => window.location.origin + '/novadb/api')

// ── Tabs ──
const activeTab = ref('editor')
const history = ref([])
const historyLoading = ref(false)
const restoring = ref(false)
const showDeleteConfirm = ref(false)

// Tooltip
const tipEntry = ref(null)
const tipData = ref(null)
const tipStyle = ref({})

// Detail view
const detailEntry = ref(null)
const detailData = ref(null)
const currentData = ref(null)
const showDetail = ref(false)
const diffLines = ref([])

// Restore confirm
const confirmEntry = ref(null)
const showConfirm = ref(false)

// ── Code example blocks ──
const readBlockPy = computed(() => isPrivate.value ?
  `import requests\n\nBASE = "${apiBase.value}"\nDATA_ID = "${dataId.value}"\nTOKEN = "${token.value || 'YOUR_TOKEN'}"\n\n# 该项目为私有，读取必须携带 token\nresp = requests.get(f"{BASE}/db/{DATA_ID}?token={TOKEN}")\ndata = resp.json()["data"]\nprint(data)` :
  `import requests\n\nBASE = "${apiBase.value}"\nDATA_ID = "${dataId.value}"\n\n# 该项目为公开，无需 token 即可读取\nresp = requests.get(f"{BASE}/db/{DATA_ID}")\ndata = resp.json()["data"]\nprint(data)`
)

const readBlockJs = computed(() => isPrivate.value ?
  `const BASE = "${apiBase.value}";\nconst DATA_ID = "${dataId.value}";\nconst TOKEN = "${token.value || 'YOUR_TOKEN'}";\n\n// 该项目为私有，读取必须携带 token\nconst resp = await fetch(\`\${BASE}/db/\${DATA_ID}?token=\${TOKEN}\`);\nconst json = await resp.json();\nconsole.log(json.data);` :
  `const BASE = "${apiBase.value}";\nconst DATA_ID = "${dataId.value}";\n\n// 该项目为公开，无需 token 即可读取\nconst resp = await fetch(\`\${BASE}/db/\${DATA_ID}\`);\nconst json = await resp.json();\nconsole.log(json.data);`
)

const updateBlockPy = computed(() =>
  `import requests\n\nBASE = "${apiBase.value}"\nDATA_ID = "${dataId.value}"\nTOKEN = "${token.value || 'YOUR_TOKEN'}"\n\n# 修改数据必须携带 token（无论公开/私有）\nrequests.put(f"{BASE}/db/{DATA_ID}", json={\n    "token": TOKEN,\n    "data": {"key": "new_value"}\n})`
)

const updateBlockJs = computed(() =>
  `const BASE = "${apiBase.value}";\nconst DATA_ID = "${dataId.value}";\nconst TOKEN = "${token.value || 'YOUR_TOKEN'}";\n\n// 修改数据必须携带 token（无论公开/私有）\nawait fetch(\`\${BASE}/db/\${DATA_ID}\`, {\n  method: "PUT",\n  headers: {"Content-Type": "application/json"},\n  body: JSON.stringify({\n    token: TOKEN,\n    data: {key: "new_value"}\n  })\n});`
)

const deleteBlockPy = computed(() =>
  `import requests\n\nBASE = "${apiBase.value}"\nDATA_ID = "${dataId.value}"\nTOKEN = "${token.value || 'YOUR_TOKEN'}"\n\n# 删除数据必须携带 token（无论公开/私有，不可恢复！）\nrequests.delete(f"{BASE}/db/{DATA_ID}", json={"token": TOKEN})`
)

const deleteBlockJs = computed(() =>
  `const BASE = "${apiBase.value}";\nconst DATA_ID = "${dataId.value}";\nconst TOKEN = "${token.value || 'YOUR_TOKEN'}";\n\n// 删除数据必须携带 token（无论公开/私有，不可恢复！）\nawait fetch(\`\${BASE}/db/\${DATA_ID}\`, {\n  method: "DELETE",\n  headers: {"Content-Type": "application/json"},\n  body: JSON.stringify({token: TOKEN})\n});`
)

// ── novadb SDK blocks ──
const sdkReadBlock = computed(() => isPrivate.value ?
  `from novadb import NovaDB\n\n# 该项目为私有，必须传入 token 才能读取\ndb = NovaDB("${dataId.value}", "${token.value || 'YOUR_TOKEN'}")\ndata = db.get()\nprint(data)` :
  `from novadb import NovaDB\n\n# 该项目为公开，无需 token 即可读取\ndb = NovaDB("${dataId.value}")\ndata = db.get()\nprint(data)`
)

const sdkUpdateBlock = computed(() =>
  `from novadb import NovaDB\n\n# 修改数据必须传入 token（无论公开/私有）\ndb = NovaDB("${dataId.value}", "${token.value || 'YOUR_TOKEN'}")\ndb.set({"key": "new_value"})`
)

const sdkDeleteBlock = computed(() =>
  `from novadb import NovaDB\n\n# 删除数据必须传入 token（无论公开/私有）\ndb = NovaDB("${dataId.value}", "${token.value || 'YOUR_TOKEN'}")\ndb.delete()`
)

function copyBlock(label, text) {
  navigator.clipboard.writeText(text)
  copiedBlock.value = label
  setTimeout(() => { copiedBlock.value = '' }, 2000)
}

// ── Editor logic ──
const sizeBytes = computed(() => new TextEncoder().encode(code.value).length)
const sizeKB = computed(() => (sizeBytes.value / 1024).toFixed(1) + ' KB')
const oversize = computed(() => sizeBytes.value > MAX_SIZE)

const editorClass = computed(() => {
  if (jsonError.value) return 'invalid'
  if (code.value.trim() && code.value !== '{}') return 'valid'
  return ''
})

const barStyle = computed(() => {
  const pct = Math.min(100, (sizeBytes.value / MAX_SIZE) * 100)
  let c = 'var(--green)'
  if (pct > 90) c = 'var(--red)'
  else if (pct > 70) c = 'var(--orange)'
  return { width: pct + '%', background: c }
})

const shareUrl = computed(() => `${window.location.origin}/novadb/api/db/${dataId.value}`)
const copiedShare = ref(false)
function copyShare() {
  navigator.clipboard.writeText(shareUrl.value)
  copiedShare.value = true
  setTimeout(() => { copiedShare.value = false }, 2000)
}

onMounted(loadData)

function validate() {
  jsonError.value = ''
  if (!code.value.trim()) { code.value = EMPTY; return }
  try {
    const p = JSON.parse(code.value)
    if (typeof p !== 'object' || p === null || Array.isArray(p))
      jsonError.value = 'data 必须是 JSON 对象（{}）'
  } catch (e) {
    jsonError.value = 'JSON 格式错误：' + e.message
  }
}

function prettyPrint() {
  try { const p = JSON.parse(code.value); code.value = JSON.stringify(p, null, 2); jsonError.value = '' }
  catch (e) { jsonError.value = '无法格式化' }
}

function clearData() { code.value = EMPTY; jsonError.value = ''; msg.value = null }

async function loadData() {
  loading.value = true; msg.value = null
  token.value = queryToken.value
  try {
    let data
    try { data = await api.readObject(dataId.value) } catch (_) {
      if (token.value) { data = await api.readObject(dataId.value, token.value) }
      else {
        const all = await api.listObjects()
        const found = (all.objects || []).find(o => o.data_id === dataId.value)
        if (found) { token.value = found.token; data = await api.readObject(dataId.value, found.token) }
      }
    }
    if (!data) throw new Error('无法读取数据')
    token.value = data.token
    label.value = data.label || ''
    const raw1 = JSON.stringify(data.data, null, 2)
    code.value = raw1 === '{}' ? EMPTY : raw1
    storedData.value = code.value
    isPrivate.value = data.private
    updatetime.value = data.updatetime
    validate()
  } catch (e) { msg.value = { type: 'error', text: e.message } }
  finally { loading.value = false }
}

async function saveData() {
  // Auto-format first
  try {
    const p = JSON.parse(code.value)
    code.value = JSON.stringify(p, null, 2)
    jsonError.value = ''
  } catch (_) {}
  validate()
  if (jsonError.value || oversize.value) return
  if (!token.value) { showToast('缺少 token', 'error'); return }
  saving.value = true; msg.value = null
  try {
    const p = JSON.parse(code.value)
    const data = await api.updateObject(dataId.value, token.value, label.value, p, isPrivate.value)
    updatetime.value = data.updatetime
    storedData.value = code.value
    if (data.order_only) {
      orderBefore.value = JSON.stringify(data.data, null, 2) === '{}' ? '{\n  \n}' : JSON.stringify(data.data, null, 2)
      orderAfter.value = code.value
      showOrderModal.value = true
    } else if (data.changed) {
      showToast('保存成功', 'success')
    } else {
      showToast('无变化', 'info')
    }
  } catch (e) { showToast(e.message, 'error') }
  finally { saving.value = false }
}

async function forceSave() {
  showOrderModal.value = false
  saving.value = true
  try {
    const p = JSON.parse(code.value)
    const data = await api.updateObject(dataId.value, token.value, label.value, p, isPrivate.value, true)
    updatetime.value = data.updatetime
    storedData.value = code.value
    showToast('保存成功', 'success')
  } catch (e) { showToast(e.message, 'error') }
  finally { saving.value = false }
}

function cancelOrderModal() {
  showOrderModal.value = false
}

// ── History ──
async function loadHistory() {
  if (!token.value) return
  historyLoading.value = true
  try {
    const data = await api.getHistory(dataId.value, token.value)
    history.value = data.history || []
  } catch (e) { msg.value = { type: 'error', text: e.message } }
  finally { historyLoading.value = false }
}

function switchTab(tab) {
  activeTab.value = tab
  msg.value = null
  if (tab === 'history') loadHistory()
}

function formatHistoryData(raw) {
  try {
    const parsed = JSON.parse(raw)
    const formatted = JSON.stringify(parsed, null, 2)
    return formatted === '{}' ? '{\n  \n}' : formatted
  } catch {
    return raw
  }
}

function showTip(entry, event) {
  const formatted = formatHistoryData(entry.data)
  const lines = formatted.split('\n')
  const preview = lines.slice(0, 10)
  tipData.value = preview.join('\n') + (lines.length > 10 ? '\n…' : '')
  tipEntry.value = entry.id
  moveTip(event)
}

function moveTip(event) {
  const gap = 12
  const maxW = 300
  const maxH = 200
  let left = event.clientX + gap
  let top = event.clientY + gap
  if (left + maxW > window.innerWidth - gap) left = event.clientX - maxW - gap
  if (top + maxH > window.innerHeight - gap) top = event.clientY - maxH - gap
  if (left < gap) left = gap
  if (top < gap) top = gap
  tipStyle.value = { left: left + 'px', top: top + 'px' }
}

function hideTip() {
  tipEntry.value = null
  tipData.value = null
}

function openDetail(entry) {
  detailData.value = formatHistoryData(entry.data)
  try {
    const parsed = JSON.parse(code.value)
    const formatted = JSON.stringify(parsed, null, 2)
    currentData.value = formatted === '{}' ? '{\n  \n}' : formatted
  } catch {
    currentData.value = code.value
  }
  detailEntry.value = entry
  computeDiff()
  showDetail.value = true
  hideTip()
}

// ── Simple LCS line diff ──
function computeDiff() {
  const oldLines = detailData.value.split('\n')
  const newLines = currentData.value.split('\n')
  const result = []

  // LCS table
  const m = oldLines.length, n = newLines.length
  const dp = Array.from({ length: m + 1 }, () => new Uint16Array(n + 1))
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (oldLines[i - 1] === newLines[j - 1]) dp[i][j] = dp[i - 1][j - 1] + 1
      else dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1])
    }
  }

  // Backtrack
  let i = m, j = n
  const ops = []
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && oldLines[i - 1] === newLines[j - 1]) {
      ops.unshift({ type: 'same', old: oldLines[i - 1], new: newLines[j - 1] })
      i--; j--
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      ops.unshift({ type: 'add', old: null, new: newLines[j - 1] })
      j--
    } else {
      ops.unshift({ type: 'del', old: oldLines[i - 1], new: null })
      i--
    }
  }

  // Merge consecutive same lines into chunks for readability
  for (const op of ops) {
    const last = result[result.length - 1]
    if (op.type === 'same' && last && last.type === 'same') {
      last.lines.push(op.old)
    } else if (op.type === 'same') {
      result.push({ type: 'same', lines: [op.old] })
    } else if (op.type === 'add') {
      result.push({ type: 'add', line: op.new })
    } else {
      result.push({ type: 'del', line: op.old })
    }
  }
  diffLines.value = result
}

function closeDetail() {
  showDetail.value = false
  detailEntry.value = null
  detailData.value = null
}

function promptRestore() {
  confirmEntry.value = detailEntry.value
  showConfirm.value = true
  showDetail.value = false
}

async function doRestore() {
  const entry = confirmEntry.value
  showConfirm.value = false
  if (!entry) return
  restoring.value = true
  try {
    const data = await api.restoreVersion(dataId.value, token.value, entry.id)
    const raw2 = JSON.stringify(data.data, null, 2)
    code.value = raw2 === '{}' ? EMPTY : raw2
    storedData.value = code.value
    label.value = data.label || ''
    isPrivate.value = data.private
    updatetime.value = data.updatetime
    validate()
    activeTab.value = 'editor'
    showToast('恢复成功', 'success')
  } catch (e) { msg.value = { type: 'error', text: e.message } }
  finally { restoring.value = false; confirmEntry.value = null }
}

function cancelRestore() {
  showConfirm.value = false
  confirmEntry.value = null
}

function fmtSize(bytes) { return (bytes / 1024).toFixed(1) + ' KB' }

function promptDelete() {
  showDeleteConfirm.value = true
}
async function confirmDelete() {
  showDeleteConfirm.value = false
  try {
    await api.deleteObject(dataId.value, token.value)
    router.push('/data')
  } catch (e) { showToast(e.message, 'error') }
}
function cancelDeleteConfirm() {
  showDeleteConfirm.value = false
}
</script>

<template>
  <div class="page">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
      <router-link to="/data" class="btn-sm btn-ghost">← 返回</router-link>
      <h1 style="font-size:1.2rem;margin-bottom:0;">编辑器</h1>
    </div>

    <!-- Tabs -->
    <div class="code-tabs" style="margin-bottom:16px;">
      <button :class="{ active: activeTab === 'editor' }" @click="switchTab('editor')">✏️ 编辑</button>
      <button :class="{ active: activeTab === 'history' }" @click="switchTab('history')">
        🕐 历史（{{ history.length || '…' }}）
      </button>
      <button :class="{ active: activeTab === 'code' }" @click="switchTab('code')">📋 调用示例</button>
    </div>

    <!-- ── Editor tab ── -->
    <template v-if="activeTab === 'editor'">
      <div v-if="loading" style="text-align:center;padding:60px;color:var(--muted);">加载中…</div>
      <div v-else class="card">
        <div class="field">
          <label>标签</label>
          <input type="text" v-model="label" placeholder="输入标签" />
        </div>

        <div class="editor-wrap">
          <textarea v-model="code" :class="editorClass" spellcheck="false" @input="validate" placeholder='{"key": "value"}'></textarea>
        </div>
        <div v-if="jsonError" class="error-text">❌ {{ jsonError }}</div>

        <!-- Size bar below editor -->
        <div style="display:flex;align-items:center;justify-content:space-between;margin-top:8px;">
          <span v-if="updatetime" style="font-size:.75rem;color:var(--muted);">🕐 {{ updatetime }}</span>
          <span v-else></span>
          <div class="size-bar">
            <span>{{ sizeKB }} / 256 KB</span>
            <div class="track"><div class="fill" :style="barStyle"></div></div>
          </div>
        </div>

        <!-- Actions: tools left, save right -->
        <div class="actions" style="margin-top:6px;justify-content:space-between;">
          <div style="display:flex;gap:10px;">
            <button @click="prettyPrint">🧹 格式化</button>
            <button @click="clearData">🗑 清空</button>
            <button @click="loadData" :disabled="loading">↺ 恢复</button>
            <button class="btn-danger btn-sm" @click="promptDelete">🗑 删除</button>
          </div>
          <button class="btn-primary" @click="saveData" :disabled="saving || !!jsonError || oversize || !token">
            💾 {{ saving ? '保存中…' : '保存' }}
          </button>
        </div>

        <div class="toggle-row">
          <span>{{ isPrivate ? '🔒 私有' : '🌐 公开' }}</span>
          <label class="switch">
            <input type="checkbox" :checked="!isPrivate" @change="togglePrivate" />
            <span class="slider"></span>
          </label>
        </div>

        <div v-if="!isPrivate" style="margin-bottom:12px;">
          <span style="font-size:.78rem;color:var(--muted);">分享链接</span>
          <div style="display:flex;align-items:center;gap:8px;margin-top:4px;">
            <div class="share-link" style="flex:1;">{{ shareUrl }}</div>
            <button class="btn-sm" @click="copyShare" style="flex-shrink:0;">{{ copiedShare ? '✅' : '📋' }}</button>
          </div>
        </div>

        <div v-if="oversize" class="msg error" style="margin-top:12px;">⚠️ 数据过大（{{ sizeKB }}），上限 256 KB</div>
      </div>

      <!-- Toast -->
      <Teleport to="body">
        <div v-if="toast" :class="['toast', 'toast-' + toast.type]">{{ toast.text }}</div>
      </Teleport>

      <!-- Delete confirm modal -->
      <Teleport to="body">
        <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="cancelDeleteConfirm">
          <div class="modal">
            <h3>⚠️ 确认删除</h3>
            <p style="color:var(--muted);font-size:.88rem;line-height:1.6;">确定要删除「{{ label || dataId }}」吗？此操作不可恢复。</p>
            <div class="actions" style="margin-top:14px;">
              <button class="btn-ghost" @click="cancelDeleteConfirm">取消</button>
              <button class="btn-danger" @click="confirmDelete">确认删除</button>
            </div>
          </div>
        </div>
      </Teleport>

      <!-- Order-only modal -->
      <Teleport to="body">
        <div v-if="showOrderModal" class="modal-overlay" @click.self="cancelOrderModal">
          <div class="modal" style="max-width:700px;">
            <h3>⚠️ 仅发现字段顺序变化，是否存储？</h3>
            <div style="display:flex;gap:12px;margin-top:14px;">
              <div style="flex:1;">
                <div style="font-size:.74rem;color:var(--muted);margin-bottom:4px;">当前存储</div>
                <pre style="margin:0;max-height:260px;overflow:auto;font-size:.72rem;"><code>{{ orderBefore }}</code></pre>
              </div>
              <div style="flex:1;">
                <div style="font-size:.74rem;color:var(--accent);margin-bottom:4px;">新顺序</div>
                <pre style="margin:0;max-height:260px;overflow:auto;font-size:.72rem;"><code>{{ orderAfter }}</code></pre>
              </div>
            </div>
            <div class="actions" style="margin-top:14px;">
              <button class="btn-ghost" @click="cancelOrderModal">取消</button>
              <button class="btn-primary" @click="forceSave" :disabled="saving">存储新顺序</button>
            </div>
          </div>
        </div>
      </Teleport>
    </template>

    <!-- ── History tab ── -->
    <template v-if="activeTab === 'history'">
      <div class="card" style="position:relative;">
        <h2>🕐 变更记录（最近 50 条）</h2>
        <div v-if="historyLoading" style="text-align:center;padding:40px;color:var(--muted);">加载中…</div>
        <div v-else-if="history.length === 0" style="text-align:center;padding:40px;color:var(--muted);">暂无历史记录</div>
        <div v-else style="position:relative;">
          <div
            v-for="entry in history"
            :key="entry.id"
            class="history-row"
            @mouseenter="showTip(entry, $event)"
            @mousemove="moveTip"
            @mouseleave="hideTip"
            @click="openDetail(entry)"
          >
            <div class="history-info">
              <div class="history-time">🕐 {{ entry.changed_at }}</div>
              <div class="history-meta">
                {{ entry.label || '无标签' }} &nbsp;·&nbsp;
                {{ entry.private ? '🔒' : '🌐' }} &nbsp;·&nbsp;
                {{ fmtSize(entry.size_bytes) }}
              </div>
            </div>
            <span style="font-size:.72rem;color:var(--muted);">点击查看详情 ›</span>
          </div>
        </div>
        <div v-if="msg" :class="['msg', msg.type]" style="margin-top:12px;">{{ msg.text }}</div>

        <!-- Tooltip -->
        <Teleport to="body">
          <div
            v-if="tipEntry && tipData"
            class="history-tip"
            :style="tipStyle"
            @mouseenter="() => {}"
            @mouseleave="hideTip"
          >
            <pre><code>{{ tipData }}</code></pre>
          </div>
        </Teleport>
      </div>

      <!-- Detail modal with diff -->
      <Teleport to="body">
        <div v-if="showDetail" class="modal-overlay" @click.self="closeDetail">
          <div class="modal" style="max-width:780px;max-height:85vh;display:flex;flex-direction:column;">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
              <h3 style="margin:0;">📋 版本对比</h3>
              <button class="btn-sm btn-ghost" @click="closeDetail">✕</button>
            </div>
            <div style="display:flex;gap:12px;margin-bottom:10px;font-size:.76rem;color:var(--muted);">
              <span>🕐 历史：{{ detailEntry?.changed_at }}</span>
              <span>📦 {{ detailEntry ? fmtSize(detailEntry.size_bytes) : '' }}</span>
              <span style="margin-left:auto;color:var(--accent);">🆕 当前编辑器内容</span>
            </div>

            <!-- Diff legend -->
            <div style="display:flex;gap:16px;margin-bottom:8px;font-size:.72rem;">
              <span style="color:#f85149;">− 历史版本（删除）</span>
              <span style="color:#3fb950;">+ 当前版本（新增）</span>
            </div>

            <!-- Diff view (unified) -->
            <div class="diff-view">
              <div v-if="diffLines.length === 0" style="padding:20px;text-align:center;color:var(--muted);">
                两版本完全一致
              </div>
              <div
                v-for="(chunk, ci) in diffLines"
                :key="ci"
              >
                <template v-if="chunk.type === 'same'">
                  <div
                    v-for="(line, li) in chunk.lines"
                    :key="li"
                    class="diff-line diff-same"
                  >
                    <span class="diff-sign">&nbsp;</span>
                    <span class="diff-text">{{ line }}</span>
                  </div>
                </template>
                <div v-else-if="chunk.type === 'del'" class="diff-line diff-del">
                  <span class="diff-sign">-</span>
                  <span class="diff-text">{{ chunk.line }}</span>
                </div>
                <div v-else class="diff-line diff-add">
                  <span class="diff-sign">+</span>
                  <span class="diff-text">{{ chunk.line }}</span>
                </div>
              </div>
            </div>

            <div class="actions" style="margin-top:14px;">
              <button class="btn-ghost" @click="closeDetail">关闭</button>
              <button class="btn-primary" @click="promptRestore">↩ 恢复为此版本</button>
            </div>
          </div>
        </div>
      </Teleport>

      <!-- Restore confirm modal -->
      <Teleport to="body">
        <div v-if="showConfirm" class="modal-overlay" @click.self="cancelRestore">
          <div class="modal">
            <h3>⚠️ 确认恢复</h3>
            <p style="color:var(--muted);font-size:.88rem;line-height:1.6;margin-bottom:12px;">
              确定要恢复到此版本吗？当前编辑器中的修改将丢失。
            </p>
            <div v-if="confirmEntry" style="font-size:.82rem;color:var(--muted);">
              <div>🕐 {{ confirmEntry.changed_at }}</div>
              <div>📦 {{ fmtSize(confirmEntry.size_bytes) }}</div>
            </div>
            <div class="actions">
              <button class="btn-ghost" @click="cancelRestore">取消</button>
              <button class="btn-primary" @click="doRestore" :disabled="restoring">
                {{ restoring ? '恢复中…' : '确认恢复' }}
              </button>
            </div>
          </div>
        </div>
      </Teleport>
    </template>

    <!-- ── Code examples tab ── -->
    <template v-if="activeTab === 'code'">
      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
          <h2 style="margin-bottom:0;">📋 调用示例</h2>
          <div class="code-tabs" style="margin-bottom:0;">
            <button :class="{ active: codeTab === 'novadb' }" @click="codeTab = 'novadb'">novadb 模块</button>
            <button :class="{ active: codeTab === 'python' }" @click="codeTab = 'python'">Python</button>
            <button :class="{ active: codeTab === 'js' }" @click="codeTab = 'js'">JavaScript</button>
          </div>
        </div>

        <!-- SDK tab -->
        <template v-if="codeTab === 'novadb'">
          <div style="background:rgba(14,165,233,0.06);border:1px solid rgba(14,165,233,0.2);border-radius:8px;padding:10px 14px;margin-bottom:16px;font-size:.8rem;color:var(--muted);">
            📥 <a href="/novadb/novadb.py" style="color:var(--accent);text-decoration:underline;">下载 novadb.py</a> 放到你的项目目录即可使用。
          </div>
          <div class="code-section">
            <div class="code-section-header">
              <span>📖 读取数据</span>
              <button class="btn-sm" @click="copyBlock('sdk-read', sdkReadBlock)">
                {{ copiedBlock === 'sdk-read' ? '✅' : '📋 复制' }}
              </button>
            </div>
            <pre><code>{{ sdkReadBlock }}</code></pre>
          </div>
          <div class="code-section">
            <div class="code-section-header">
              <span>✏️ 更新数据</span>
              <button class="btn-sm" @click="copyBlock('sdk-update', sdkUpdateBlock)">
                {{ copiedBlock === 'sdk-update' ? '✅' : '📋 复制' }}
              </button>
            </div>
            <pre><code>{{ sdkUpdateBlock }}</code></pre>
          </div>
          <div class="code-section">
            <div class="code-section-header">
              <span>🗑 删除数据</span>
              <button class="btn-sm" @click="copyBlock('sdk-delete', sdkDeleteBlock)">
                {{ copiedBlock === 'sdk-delete' ? '✅' : '📋 复制' }}
              </button>
            </div>
            <pre><code>{{ sdkDeleteBlock }}</code></pre>
          </div>
        </template>

        <!-- Python / JS tabs -->
        <template v-else>
          <div class="code-section">
            <div class="code-section-header">
              <span>📖 读取数据</span>
              <button class="btn-sm" @click="copyBlock('read', codeTab === 'python' ? readBlockPy : readBlockJs)">
                {{ copiedBlock === 'read' ? '✅' : '📋 复制' }}
              </button>
            </div>
            <pre><code>{{ codeTab === 'python' ? readBlockPy : readBlockJs }}</code></pre>
          </div>
          <div class="code-section">
            <div class="code-section-header">
              <span>✏️ 更新数据</span>
              <button class="btn-sm" @click="copyBlock('update', codeTab === 'python' ? updateBlockPy : updateBlockJs)">
                {{ copiedBlock === 'update' ? '✅' : '📋 复制' }}
              </button>
            </div>
            <pre><code>{{ codeTab === 'python' ? updateBlockPy : updateBlockJs }}</code></pre>
          </div>
          <div class="code-section">
            <div class="code-section-header">
              <span>🗑 删除数据</span>
              <button class="btn-sm" @click="copyBlock('delete', codeTab === 'python' ? deleteBlockPy : deleteBlockJs)">
                {{ copiedBlock === 'delete' ? '✅' : '📋 复制' }}
              </button>
            </div>
            <pre><code>{{ codeTab === 'python' ? deleteBlockPy : deleteBlockJs }}</code></pre>
          </div>
        </template>
      </div>
    </template>
  </div>
</template>
