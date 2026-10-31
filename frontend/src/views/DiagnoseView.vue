<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type Diagnose, type VersionInfo, type WebVersion } from '../api'

const data = ref<Diagnose | null>(null)
const version = ref<VersionInfo | null>(null)
const web = ref<WebVersion | null>(null)
const error = ref('')
const loading = ref(false)

const yesNo = (value: boolean) => (value ? '正常' : '异常')
const okClass = (value: boolean) => (value ? 'text-emerald-700' : 'text-rose-700')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [diagnose, versionInfo, webVersion] = await Promise.all([
      api.diagnose(),
      api.version(),
      api.webVersion().catch(() => null),
    ])
    data.value = diagnose
    version.value = versionInfo
    web.value = webVersion
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 px-8 py-8">
    <header class="flex items-center justify-between gap-4">
      <h1 class="text-5xl font-bold">设备自检</h1>
      <div class="flex gap-4">
        <button
          class="rounded-2xl border-2 border-stone-300 bg-white px-6 py-4 text-2xl font-semibold shadow-sm active:bg-stone-100"
          :disabled="loading"
          @click="load"
        >
          {{ loading ? '检查中…' : '重新检查' }}
        </button>
        <router-link
          to="/"
          class="rounded-2xl bg-ink px-6 py-4 text-2xl font-semibold text-white active:bg-stone-700"
        >
          返回首页
        </router-link>
      </div>
    </header>

    <p v-if="error" class="rounded-2xl bg-rose-100 px-6 py-4 text-2xl text-rose-900">
      {{ error }}
    </p>

    <template v-if="data">
      <section class="rounded-3xl border-2 border-stone-200 bg-white px-6 py-2">
        <h2 class="py-4 text-3xl font-bold text-muted">版本</h2>
        <div class="flex justify-between gap-6 border-t-2 border-stone-100 py-4 text-2xl">
          <span class="text-muted">后端版本</span>
          <span class="font-semibold">{{ version?.app_version ?? '—' }}</span>
        </div>
        <div class="flex justify-between gap-6 border-t-2 border-stone-100 py-4 text-2xl">
          <span class="text-muted">接口版本</span>
          <span class="font-semibold">{{ version?.api_version ?? '—' }}</span>
        </div>
        <div class="flex justify-between gap-6 border-t-2 border-stone-100 py-4 text-2xl">
          <span class="text-muted">前端版本</span>
          <span class="font-semibold">{{ web?.web_version ?? '未读取' }}</span>
        </div>
        <div class="flex justify-between gap-6 border-t-2 border-stone-100 py-4 text-2xl">
          <span class="text-muted">Shell 最低版本</span>
          <span class="font-semibold">{{ version?.min_shell_version ?? '—' }}</span>
        </div>
        <div class="flex justify-between gap-6 border-t-2 border-stone-100 py-4 text-2xl">
          <span class="text-muted">前端构建时间</span>
          <span class="font-semibold">{{ web?.built_at ?? '—' }}</span>
        </div>
      </section>

      <section class="rounded-3xl border-2 border-stone-200 bg-white px-6 py-2">
        <h2 class="py-4 text-3xl font-bold text-muted">数据库与中文检索</h2>
        <div class="flex justify-between gap-6 border-t-2 border-stone-100 py-4 text-2xl">
          <span class="text-muted">数据库路径</span>
          <span class="break-all text-right font-semibold">{{ data.db.path }}</span>
        </div>
        <div class="flex justify-between gap-6 border-t-2 border-stone-100 py-4 text-2xl">
          <span class="text-muted">SQLite 版本</span>
          <span class="font-semibold">{{ data.db.sqlite_version }}</span>
        </div>
        <div class="flex justify-between gap-6 border-t-2 border-stone-100 py-4 text-2xl">
          <span class="text-muted">可写</span>
          <span :class="['font-semibold', okClass(data.db.writable)]">
            {{ yesNo(data.db.writable) }}
          </span>
        </div>
        <div class="flex justify-between gap-6 border-t-2 border-stone-100 py-4 text-2xl">
          <span class="text-muted">FTS5</span>
          <span :class="['font-semibold', okClass(data.db.fts5_available)]">
            {{ yesNo(data.db.fts5_available) }}
          </span>
        </div>
        <div class="flex justify-between gap-6 border-t-2 border-stone-100 py-4 text-2xl">
          <span class="text-muted">中文子串检索（trigram）</span>
          <span :class="['font-semibold', okClass(data.db.fts5_trigram_available)]">
            {{ yesNo(data.db.fts5_trigram_available) }}
          </span>
        </div>
        <p class="border-t-2 border-stone-100 py-4 text-xl text-muted">{{ data.db.detail }}</p>
        <p v-if="data.db.error" class="py-4 text-xl text-rose-700">{{ data.db.error }}</p>
      </section>

      <section class="rounded-3xl border-2 border-stone-200 bg-white px-6 py-2">
        <h2 class="py-4 text-3xl font-bold text-muted">对话模型</h2>
        <div class="flex justify-between gap-6 border-t-2 border-stone-100 py-4 text-2xl">
          <span class="text-muted">接口地址</span>
          <span class="break-all text-right font-semibold">{{ data.llm.base_url }}</span>
        </div>
        <div class="flex justify-between gap-6 border-t-2 border-stone-100 py-4 text-2xl">
          <span class="text-muted">模型</span>
          <span class="font-semibold">{{ data.llm.model }}</span>
        </div>
        <div class="flex justify-between gap-6 border-t-2 border-stone-100 py-4 text-2xl">
          <span class="text-muted">密钥已配置</span>
          <span :class="['font-semibold', data.llm.api_key_set ? 'text-emerald-700' : 'text-amber-700']">
            {{ data.llm.api_key_set ? '是' : '否' }}
          </span>
        </div>
      </section>

      <section class="rounded-3xl border-2 border-stone-200 bg-white px-6 py-2">
        <h2 class="py-4 text-3xl font-bold text-muted">服务器</h2>
        <div class="flex justify-between gap-6 border-t-2 border-stone-100 py-4 text-2xl">
          <span class="text-muted">服务器时间</span>
          <span class="font-semibold">{{ data.server_time }}</span>
        </div>
        <div class="flex justify-between gap-6 border-t-2 border-stone-100 py-4 text-2xl">
          <span class="text-muted">时区</span>
          <span class="font-semibold">{{ data.timezone }}</span>
        </div>
      </section>
    </template>
  </main>
</template>
