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
  <header class="navbar" v-if="userId">
    <span class="logo">💾 NovaDB</span>
    <span class="spacer"></span>
    <span class="badge">{{ userId }}</span>
    <button class="btn-sm" @click="logout">退出</button>
  </header>
  <router-view />
</template>
