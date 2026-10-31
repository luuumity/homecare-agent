import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'
import DiagnoseView from './views/DiagnoseView.vue'
import ChatView from './views/ChatView.vue'
import ItemsView from './views/ItemsView.vue'
import RemindersView from './views/RemindersView.vue'
import ContactsView from './views/ContactsView.vue'
import ConfirmationsView from './views/ConfirmationsView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/chat', name: 'chat', component: ChatView },
    { path: '/items', name: 'items', component: ItemsView },
    { path: '/reminders', name: 'reminders', component: RemindersView },
    { path: '/contacts', name: 'contacts', component: ContactsView },
    { path: '/confirmations', name: 'confirmations', component: ConfirmationsView },
    { path: '/diagnose', name: 'diagnose', component: DiagnoseView },
  ],
})
