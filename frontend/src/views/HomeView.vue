<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { api, errorMessage, type Reminder } from '../api'

type Status = 'checking' | 'ok' | 'down'

const now = ref(new Date())
const status = ref<Status>('checking')
const appVersion = ref('')
const reminders = ref<Reminder[]>([])
const pendingCount = ref(0)
const loadError = ref('')

let clockTimer: number | undefined
let healthTimer: number | undefined

const timeText = computed(() =>
  now.value.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false }),
)

const dateText = computed(() =>
  now.value.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  }),
)

const greeting = computed(() => {
  const hour = now.value.getHours()
  if (hour < 5) return '夜深了，早点休息'
  if (hour < 10) return '早上好'
  if (hour < 12) return '上午好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  if (hour < 23) return '晚上好'
  return '夜深了，早点休息'
})

const statusText = computed(() => {
  if (status.value === 'ok') return '服务正常'
  if (status.value === 'down') return '服务未连接'
  return '正在检查…'
})

const statusClass = computed(() => {
  if (status.value === 'ok') return 'bg-emerald-100 text-emerald-900'
  if (status.value === 'down') return 'bg-rose-100 text-rose-900'
  return 'bg-amber-100 text-amber-900'
})

const nextReminder = computed(() => {
  const upcoming = reminders.value
    .filter((item) => item.enabled)
    .map((item) => ({ ...item, time: new Date(item.remind_at).getTime() }))
    .filter((item) => Number.isFinite(item.time) && item.time >= Date.now())
    .sort((a, b) => a.time - b.time)
  return upcoming[0] ?? null
})

const nextReminderText = computed(() => {
  if (!nextReminder.value) return ''
  const date = new Date(nextReminder.value.remind_at)
  return `${date.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' })} ${date.toLocaleTimeString(
    'zh-CN',
    { hour: '2-digit', minute: '2-digit', hour12: false },
  )}`
})

const tiles = [
  {
    to: '/chat',
    mark: '聊',
    title: '说说话',
    hint: '问东西、聊家常',
    badge: 'bg-amber-100 text-amber-900',
  },
  {
    to: '/items',
    mark: '物',
    title: '东西放哪',
    hint: '找东西、记位置',
    badge: 'bg-sky-100 text-sky-900',
  },
  {
    to: '/reminders',
    mark: '铃',
    title: '提醒',
    hint: '吃药、喝水、办事',
    badge: 'bg-emerald-100 text-emerald-900',
  },
  {
    to: '/contacts',
    mark: '电',
    title: '打电话',
    hint: '给家人拨号',
    badge: 'bg-rose-100 text-rose-900',
  },
]

async function checkHealth() {
  try {
    const health = await api.health()
    appVersion.value = health.app_version
    status.value = 'ok'
  } catch {
    status.value = 'down'
  }
}

async function loadSummary() {
  loadError.value = ''
  try {
    const [reminderList, pendingList] = await Promise.all([
      api.reminders.list(true),
      api.confirmations.list('pending'),
    ])
    reminders.value = reminderList
    pendingCount.value = pendingList.length
  } catch (error) {
    loadError.value = errorMessage(error)
  }
}

onMounted(() => {
  clockTimer = window.setInterval(() => {
    now.value = new Date()
  }, 1000)
  healthTimer = window.setInterval(checkHealth, 15000)
  checkHealth()
  loadSummary()
})

onUnmounted(() => {
  window.clearInterval(clockTimer)
  window.clearInterval(healthTimer)
})
</script>

<template>
  <main class="mx-auto flex min-h-screen max-w-6xl flex-col gap-5 px-4 py-6 sm:px-8 sm:py-7">
    <header class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <p class="text-2xl text-muted">{{ greeting }}</p>
        <h1 class="mt-1 text-4xl font-bold tracking-wide">{{ dateText }}</h1>
      </div>
      <div class="flex shrink-0 items-center gap-3">
        <router-link
          to="/confirmations"
          class="relative flex min-h-[3.25rem] items-center gap-2 rounded-2xl border-2 border-stone-300 bg-white px-5 text-xl font-semibold shadow-sm active:bg-stone-100"
        >
          待确认
          <span
            v-if="pendingCount"
            class="flex h-8 min-w-8 items-center justify-center rounded-full bg-rose-700 px-2 text-lg font-bold text-white"
          >
            {{ pendingCount }}
          </span>
        </router-link>
        <router-link
          to="/diagnose"
          class="flex min-h-[3.25rem] items-center rounded-2xl border-2 border-stone-300 bg-white px-5 text-xl font-semibold shadow-sm active:bg-stone-100"
        >
          自检
        </router-link>
      </div>
    </header>

    <section class="text-center py-1">
      <p class="text-7xl font-bold tabular-nums tracking-wider">{{ timeText }}</p>
    </section>

    <section
      v-if="nextReminder"
      class="flex items-center justify-between gap-4 rounded-2xl border-2 border-emerald-200 bg-emerald-50 px-6 py-4"
    >
      <div class="min-w-0">
        <p class="text-xl font-semibold text-emerald-900">下一件事 · {{ nextReminderText }}</p>
        <p class="truncate text-2xl font-bold text-emerald-950">{{ nextReminder.title }}</p>
      </div>
      <router-link
        to="/reminders"
        class="shrink-0 rounded-xl border-2 border-emerald-300 bg-white px-5 py-3 text-xl font-semibold text-emerald-900 active:bg-emerald-100"
      >
        查看
      </router-link>
    </section>

    <p v-if="loadError" class="rounded-2xl bg-amber-100 px-5 py-3 text-xl text-amber-900">
      提醒与待确认暂时没有加载出来：{{ loadError }}
    </p>

    <section class="grid flex-1 grid-cols-2 gap-5">
      <router-link
        v-for="tile in tiles"
        :key="tile.to"
        :to="tile.to"
        class="flex min-h-[8.5rem] flex-col justify-between rounded-3xl border-2 border-stone-200 bg-white p-5 shadow-sm transition active:scale-[0.99] active:bg-stone-50"
      >
        <span
          :class="[
            'flex h-14 w-14 items-center justify-center rounded-full text-3xl font-bold',
            tile.badge,
          ]"
        >
          {{ tile.mark }}
        </span>
        <div>
          <p class="text-3xl font-bold">{{ tile.title }}</p>
          <p class="mt-1 text-xl text-muted">{{ tile.hint }}</p>
        </div>
      </router-link>
    </section>

    <footer class="flex items-center justify-between border-t-2 border-stone-200 pt-4 text-lg">
      <span class="text-muted">陪伴大屏 {{ appVersion || '' }}</span>
      <span :class="['rounded-full px-4 py-2 font-semibold', statusClass]">{{ statusText }}</span>
    </footer>
  </main>
</template>
