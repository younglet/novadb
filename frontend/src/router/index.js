import { createRouter, createWebHistory } from 'vue-router'
import { getUserId } from '../api/index.js'
import LandingView from '../views/LandingView.vue'
import LoginView from '../views/LoginView.vue'
import DataListView from '../views/DataListView.vue'
import EditorView from '../views/EditorView.vue'

const routes = [
  { path: '/', component: LandingView },
  { path: '/login', component: LoginView },
  { path: '/data', component: DataListView, meta: { auth: true } },
  { path: '/editor/:dataId', component: EditorView, meta: { auth: true } },
]

const router = createRouter({
  history: createWebHistory('/novadb/'),
  routes,
})

router.beforeEach((to, from, next) => {
  if (to.meta.auth && !getUserId()) next('/login')
  else next()
})

export default router
