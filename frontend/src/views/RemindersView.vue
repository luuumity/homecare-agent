<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api, errorMessage, type Reminder } from '../api'
import BaseModal from '../components/BaseModal.vue'
import EmptyState from '../components/EmptyState.vue'
import PageHeader from '../components/PageHeader.vue'
import { formatDateTime, repeatLabels } from '../utils'

const reminders = ref<Reminder[]>([])
const loading = ref(true)
const error = ref('')
const notice = ref('')

const formOpen = ref(false)
const editingId = ref<string | null>(null)
const form = ref({ title: '', remind_at: '', repeat_rule: 'none' as Reminder['repeat_rule'] })
const saving = ref(false)
const formError = ref('')

const deleteTarget = ref<Reminder | null>(null)
const deleting = ref(false)
const togglingId = ref<string | null>(null)

function toLocalInput(value?: string): string {
  const date = value ? new Date(value) : new Date(Date.now() + 60 * 60 * 1000)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

const sorted = computed(() =>
  [...reminders.value].sort(
    (a, b) => new Date(a.remind_at).getTime() - new Date(b.remind_at).getTime(),
  ),
)

async function load() {
  loading.value = true
  error.value = ''
  try {
    reminders.value = await api.reminders.list()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.value = { title: '', remind_at: toLocalInput(), repeat_rule: 'none' }
  formError.value = ''
  formOpen.value = true
}

function openEdit(reminder: Reminder) {
  editingId.value = reminder.id
  form.value = {
    title: reminder.title,
    remind_at: toLocalInput(reminder.remind_at),
    repeat_rule: reminder.repeat_rule,
  }
  formError.value = ''
  formOpen.value = true
}

async function save() {
  formError.value = ''
  if (!form.value.title.trim()) {
    formError.value = '要提醒什么事情？'
    return
  }
  if (!form.value.remind_at) {
    formError.value = '要选一个提醒时间'
    return
  }
  saving.value = true
  try {
    const body = {
      title: form.value.title.trim(),
      remind_at: new Date(form.value.remind_at).toISOString(),
      repeat_rule: form.value.repeat_rule,
    }
    if (editingId.value) {
      await api.reminders.update(editingId.value, body)
      notice.value = '提醒已经改好了'
    } else {
      await api.reminders.create(body)
      notice.value = '提醒设好了'
    }
    formOpen.value = false
    await load()
  } catch (e) {
    formError.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

async function toggle(reminder: Reminder) {
  togglingId.value = reminder.id
  try {
    await api.reminders.update(reminder.id, { enabled: !reminder.enabled })
    notice.value = reminder.enabled ? '提醒已暂停' : '提醒已启用'
    await load()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    togglingId.value = null
  }
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await api.reminders.remove(deleteTarget.value.id)
    notice.value = '提醒已经删除'
    deleteTarget.value = null
    await load()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    deleting.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="mx-auto flex min-h-screen max-w-5xl flex-col gap-5 px-8 py-6">
    <PageHeader title="提醒我" subtitle="吃药、喝水、出门，都可以设">
      <template #actions>
        <button
          class="min-h-[3.25rem] rounded-2xl bg-ink px-6 text-xl font-semibold text-white active:bg-stone-700"
          @click="openCreate"
        >
          新提醒
        </button>
      </template>
    </PageHeader>

    <p v-if="notice" class="rounded-2xl bg-emerald-100 px-5 py-3 text-xl text-emerald-900">{{ notice }}</p>
    <p v-if="error" class="rounded-2xl bg-rose-100 px-5 py-3 text-xl text-rose-900">{{ error }}</p>

    <section v-if="loading" class="py-12 text-center text-2xl text-muted">正在加载…</section>

    <EmptyState
      v-else-if="!sorted.length"
      mark="铃"
      title="还没有提醒"
      hint="设一个提醒，到点大屏会响。"
    >
      <button
        class="min-h-[3.25rem] rounded-2xl bg-ink px-6 text-xl font-semibold text-white"
        @click="openCreate"
      >
        设一个
      </button>
    </EmptyState>

    <section v-else class="space-y-4">
      <article
        v-for="reminder in sorted"
        :key="reminder.id"
        :class="[
          'rounded-3xl border-2 p-5 shadow-sm',
          reminder.enabled ? 'border-stone-200 bg-white' : 'border-stone-200 bg-stone-100 opacity-80',
        ]"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <p class="text-3xl font-bold">{{ reminder.title }}</p>
            <p class="mt-2 text-2xl font-semibold text-emerald-900">{{ formatDateTime(reminder.remind_at) }}</p>
            <p class="mt-1 text-xl text-muted">
              {{ repeatLabels[reminder.repeat_rule] ?? reminder.repeat_rule }}
              <span v-if="!reminder.enabled" class="ml-2 font-semibold text-stone-700">已暂停</span>
            </p>
          </div>
          <div class="flex shrink-0 flex-wrap justify-end gap-2">
            <button
              class="min-h-[3rem] rounded-xl border-2 border-stone-300 bg-paper px-4 text-xl font-semibold active:bg-stone-100"
              @click="openEdit(reminder)"
            >
              修改
            </button>
            <button
              class="min-h-[3rem] rounded-xl border-2 border-stone-300 bg-paper px-4 text-xl font-semibold active:bg-stone-100"
              :disabled="togglingId === reminder.id"
              @click="toggle(reminder)"
            >
              {{ reminder.enabled ? '暂停' : '启用' }}
            </button>
            <button
              class="min-h-[3rem] rounded-xl border-2 border-rose-200 bg-rose-50 px-4 text-xl font-semibold text-rose-900 active:bg-rose-100"
              @click="deleteTarget = reminder"
            >
              删除
            </button>
          </div>
        </div>
      </article>
    </section>

    <BaseModal
      :open="formOpen"
      :title="editingId ? '修改提醒' : '设一个提醒'"
      :confirm-text="editingId ? '保存修改' : '设好提醒'"
      :busy="saving"
      @confirm="save"
      @cancel="formOpen = false"
    >
      <div class="space-y-5">
        <label class="block">
          <span class="mb-2 block text-xl font-semibold">提醒我做什么</span>
          <input
            v-model="form.title"
            maxlength="100"
            placeholder="例如：吃降压药"
            class="min-h-[3.5rem] w-full rounded-2xl border-2 border-stone-300 bg-white px-5 text-2xl outline-none focus:border-amber-600"
          />
        </label>
        <label class="block">
          <span class="mb-2 block text-xl font-semibold">什么时候</span>
          <input
            v-model="form.remind_at"
            type="datetime-local"
            class="min-h-[3.5rem] w-full rounded-2xl border-2 border-stone-300 bg-white px-5 text-2xl outline-none focus:border-amber-600"
          />
        </label>
        <label class="block">
          <span class="mb-2 block text-xl font-semibold">多久一次</span>
          <select
            v-model="form.repeat_rule"
            class="min-h-[3.5rem] w-full rounded-2xl border-2 border-stone-300 bg-white px-5 text-2xl outline-none focus:border-amber-600"
          >
            <option v-for="(label, value) in repeatLabels" :key="value" :value="value">
              {{ label }}
            </option>
          </select>
        </label>
        <p v-if="formError" class="rounded-xl bg-rose-100 px-4 py-3 text-xl text-rose-900">{{ formError }}</p>
      </div>
    </BaseModal>

    <BaseModal
      :open="Boolean(deleteTarget)"
      title="确定删除这个提醒吗"
      confirm-text="删除"
      danger
      :busy="deleting"
      @confirm="confirmDelete"
      @cancel="deleteTarget = null"
    >
      <p v-if="deleteTarget">「{{ deleteTarget.title }}」的提醒会被删除，之后不会再响。</p>
    </BaseModal>
  </main>
</template>
