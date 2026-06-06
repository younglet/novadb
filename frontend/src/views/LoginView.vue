<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api, setUserId, getUserId } from '../api/index.js'

const router = useRouter()
const username = ref('')
const loading = ref(false)
const error = ref('')

onMounted(() => {
  if (getUserId()) router.replace('/data')
})

async function login() {
  const name = username.value.trim().toLowerCase()
  if (!name || name.length > 64) { error.value = '用户名需 1-64 个字符'; return }
  loading.value = true; error.value = ''
  try {
    const data = await api.login(name)
    setUserId(data.user_id)
    router.push('/data')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page" style="max-width:440px;padding-top:80px;">
    <router-link to="/" style="display:block;margin-bottom:24px;color:var(--muted);font-size:.85rem;">← 返回首页</router-link>
    <h1 style="margin-bottom:20px;">登录</h1>
    <div class="card">
      <div class="field">
        <label>用户名</label>
        <input type="text" v-model="username" @keyup.enter="login"
          placeholder="输入用户名即可开始" autofocus />
      </div>
      <div v-if="error" class="msg error">{{ error }}</div>
      <button class="btn-primary" @click="login" :disabled="loading" style="width:100%;justify-content:center;">
        {{ loading ? '进入中…' : '进入 NovaDB' }}
      </button>
    </div>
  </div>
</template>
