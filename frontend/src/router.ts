import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'
import DiagnoseView from './views/DiagnoseView.vue'
import ChatView from './views/ChatView.vue'
import ItemsView from './views/ItemsView.vue'
import RemindersView from './views/RemindersView.vue'
import ContactsView from './views/ContactsView.vue'
import ConfirmationsView from './views/ConfirmationsView.vue'
import LoginView from './views/LoginView.vue'
import { ensureAuth, markOut } from './session'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginView },
    { path: '/', name: 'home', component: HomeView },
    { path: '/chat', name: 'chat', component: ChatView },
    { path: '/items', name: 'items', component: ItemsView },
    { path: '/reminders', name: 'reminders', component: RemindersView },
    { path: '/contacts', name: 'contacts', component: ContactsView },
    { path: '/confirmations', name: 'confirmations', component: ConfirmationsView },
    { path: '/diagnose', name: 'diagnose', component: DiagnoseView },
  ],
})

router.beforeEach(async (to) => {
  if (to.path === '/login') {
    if (await ensureAuth()) return '/'
    return true
  }
  if (!(await ensureAuth())) {
    return { path: '/login', query: { next: to.fullPath } }
  }
  return true
})

window.addEventListener('homecare-auth-expired', () => {
  markOut()
  if (router.currentRoute.value.path !== '/login') {
    router.replace({ path: '/login', query: { next: router.currentRoute.value.fullPath } })
  }
})
