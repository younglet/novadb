<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getUserId } from '../api/index.js'

const router = useRouter()

onMounted(() => {
  if (getUserId()) router.replace('/data')
})

const features = [
  { icon: '⚡', title: '无需安装', desc: '不用装 MySQL、不用建表、不用写 SQL，一行 POST 就搞定' },
  { icon: '🔐', title: 'id + token', desc: '每个数据对象像账号密码一样：id 公开分享，token 保密修改' },
  { icon: '🌐', title: '一键公开', desc: '设为公开即可生成分享链接，发给同学直接看' },
  { icon: '💾', title: '256KB 存储', desc: '足够存游戏存档、配置、待办列表，覆盖 95% 教学场景' },
  { icon: '🐍', title: 'Python 友好', desc: '只需要 import requests，初学者三行代码就能读写数据' },
  { icon: '🎯', title: '即时生效', desc: '网页保存 = 一次标准 POST 请求，编辑器与 API 完全对齐' },
]
</script>

<template>
  <div class="landing-hero">
    <h1>NovaDB</h1>
    <p>给你的 Python 程序装上「数据硬盘」。无需数据库，一行 POST，永久保存。</p>
    <router-link to="/login" class="btn-primary" style="font-size:1rem;padding:12px 32px;display:inline-flex;text-decoration:none;">
      开始使用
    </router-link>
  </div>

  <div class="feature-grid">
    <div v-for="f in features" :key="f.title" class="feature-card">
      <div class="icon">{{ f.icon }}</div>
      <h3>{{ f.title }}</h3>
      <p>{{ f.desc }}</p>
    </div>
  </div>
</template>
