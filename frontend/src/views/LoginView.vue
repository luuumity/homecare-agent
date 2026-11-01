<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, errorMessage } from '../api'
import { markIn } from '../session'

const router = useRouter()
const route = useRoute()

const pin = ref('')
const busy = ref(false)
const error = ref('')
const dots = computed(() => Array.from({ length: 6 }, (_, i) => i < pin.value.length))

const keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '清空', '0', '删除']

function press(key: string) {
  if (busy.value) return
  error.value = ''
  if (key === '清空') {
    pin.value = ''
    return
  }
  if (key === '删除') {
    pin.value = pin.value.slice(0, -1)
    return
  }
  if (pin.value.length >= 6) return
  pin.value += key
  if (pin.value.length === 6) submit()
}

async function submit() {
  if (busy.value) return
  busy.value = true
  try {
    await api.auth.login(pin.value)
    markIn()
    const next = typeof route.query.next === 'string' ? route.query.next : '/'
    router.replace(next.startsWith('/') ? next : '/')
  } catch (e) {
    error.value = errorMessage(e)
    pin.value = ''
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="mx-auto flex min-h-screen max-w-xl flex-col justify-center gap-8 px-6 py-10">
    <div class="text-center">
      <h1 class="text-5xl font-bold">陪伴大屏</h1>
      <p class="mt-3 text-2xl text-muted">请输入 6 位数字密码</p>
    </div>

    <div class="flex justify-center gap-4">
      <span
        v-for="(filled, index) in dots"
        :key="index"
        :class="[
          'h-5 w-5 rounded-full border-2',
          filled ? 'border-accent bg-accent' : 'border-stone-300 bg-white',
        ]"
      />
    </div>

    <p v-if="error" class="rounded-2xl bg-rose-100 px-5 py-4 text-center text-xl text-rose-900">
      {{ error }}
    </p>
    <p v-if="busy" class="text-center text-xl text-muted">正在登录…</p>

    <div class="grid grid-cols-3 gap-4">
      <button
        v-for="key in keys"
        :key="key"
        class="min-h-[5rem] rounded-2xl border-2 border-stone-200 bg-white text-3xl font-semibold shadow-sm active:bg-stone-100 disabled:opacity-40"
        :disabled="busy"
        @click="press(key)"
      >
        {{ key }}
      </button>
    </div>

    <p class="text-center text-lg text-muted">登录一次后，这台设备会记住一个月</p>
  </main>
</template>
