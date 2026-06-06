<script setup>
import { ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getUserId } from './api/index.js'

const router = useRouter()
const route = useRoute()
const userId = ref(getUserId())

watch(() => route.path, () => { userId.value = getUserId() })

function logout() {
  localStorage.removeItem('novadb_user_id')
  userId.value = ''
  router.push('/')
}
</script>

<template>
  <nav class="navbar">
    <span class="logo">💾 NovaDB</span>
    <template v-if="userId">
      <router-link to="/data" :class="{ active: route.path.startsWith('/data') || route.path.startsWith('/editor') }">
        我的数据
      </router-link>
      <span class="spacer"></span>
      <span class="badge">👤 {{ userId }}</span>
      <button class="btn-sm" @click="logout">退出</button>
    </template>
    <template v-else>
      <span class="spacer"></span>
      <router-link to="/login">登录</router-link>
    </template>
  </nav>
  <router-view />
</template>
