<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api, errorMessage, type Confirmation } from '../api'
import BaseModal from '../components/BaseModal.vue'
import EmptyState from '../components/EmptyState.vue'
import PageHeader from '../components/PageHeader.vue'
import { confirmationKindLabels, formatDateTime, memoryKindLabels } from '../utils'

const all = ref<Confirmation[]>([])
const loading = ref(true)
const error = ref('')
const notice = ref('')
const busyId = ref<string | null>(null)

const rejectTarget = ref<Confirmation | null>(null)
const rejectReason = ref('')
const rejecting = ref(false)

const statusLabels: Record<string, string> = {
  pending: '等老人确认',
  elder_confirmed: '等家属确认',
  approved: '已生效',
  rejected: '已拒绝',
  expired: '已过期',
}

const pending = computed(() =>
  all.value.filter((item) => item.status === 'pending' || item.status === 'elder_confirmed'),
)
const done = computed(() =>
  all.value.filter((item) => item.status !== 'pending' && item.status !== 'elder_confirmed').slice(0, 5),
)

async function load() {
  loading.value = true
  error.value = ''
  try {
    all.value = await api.confirmations.list()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

async function act(item: Confirmation, action: 'elder' | 'family') {
  busyId.value = item.id
  notice.value = ''
  error.value = ''
  try {
    if (action === 'elder') {
      await api.confirmations.elderConfirm(item.id)
      notice.value = '老人已确认。还需要家属确认，才会真正生效。'
    } else {
      await api.confirmations.familyConfirm(item.id)
      notice.value = '家属已确认，这条信息现在生效了。'
    }
    await load()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busyId.value = null
  }
}

async function confirmReject() {
  if (!rejectTarget.value) return
  rejecting.value = true
  error.value = ''
  try {
    await api.confirmations.reject(rejectTarget.value.id, rejectReason.value.trim() || undefined)
    notice.value = '已拒绝，这条信息不会生效。'
    rejectTarget.value = null
    rejectReason.value = ''
    await load()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    rejecting.value = false
  }
}

function proposedTitle(item: Confirmation) {
  const proposed = item.payload.proposed
  if (!proposed) return '待确认的信息'
  return `${proposed.subject ?? '老人'} · ${memoryKindLabels[proposed.kind ?? ''] ?? '信息'}`
}

onMounted(load)
</script>

<template>
  <main class="mx-auto flex min-h-screen max-w-5xl flex-col gap-5 px-8 py-6">
    <PageHeader title="需要确认的事" subtitle="健康、身份这类信息，要老人和家属都确认">
      <template #actions>
        <button
          class="min-h-[3.25rem] rounded-2xl border-2 border-stone-300 bg-white px-5 text-xl font-semibold active:bg-stone-100"
          :disabled="loading"
          @click="load"
        >
          {{ loading ? '刷新中' : '刷新' }}
        </button>
      </template>
    </PageHeader>

    <p class="rounded-2xl bg-amber-100 px-5 py-3 text-xl text-amber-900">
      未确认的信息不会作为事实使用。顺序是：老人当面确认 → 家属确认。
    </p>
    <p v-if="notice" class="rounded-2xl bg-emerald-100 px-5 py-3 text-xl text-emerald-900">{{ notice }}</p>
    <p v-if="error" class="rounded-2xl bg-rose-100 px-5 py-3 text-xl text-rose-900">{{ error }}</p>

    <section v-if="loading" class="py-12 text-center text-2xl text-muted">正在加载…</section>

    <EmptyState
      v-else-if="!pending.length"
      mark="确"
      title="现在没有要确认的事"
      hint="如果小陪记下了健康或身份信息，会出现在这里。"
    />

    <section v-else class="space-y-4">
      <article
        v-for="item in pending"
        :key="item.id"
        class="rounded-3xl border-2 border-amber-200 bg-white p-5 shadow-sm"
      >
        <div class="flex flex-wrap items-center gap-3">
          <span class="rounded-full bg-amber-100 px-4 py-1 text-lg font-semibold text-amber-900">
            {{ confirmationKindLabels[item.kind] ?? item.kind }}
          </span>
          <span class="rounded-full bg-stone-100 px-4 py-1 text-lg font-semibold text-stone-700">
            {{ statusLabels[item.status] ?? item.status }}
          </span>
          <span class="text-lg text-muted">{{ formatDateTime(item.created_at) }}</span>
        </div>

        <p class="mt-4 text-xl font-semibold text-muted">{{ proposedTitle(item) }}</p>
        <p class="mt-1 text-3xl font-bold leading-snug">
          {{ item.payload.proposed?.content ?? '（没有内容）' }}
        </p>

        <div class="mt-5 flex flex-wrap items-center gap-4 text-xl">
          <span
            :class="[
              'rounded-full px-4 py-2 font-semibold',
              item.elder_confirmed_at ? 'bg-emerald-100 text-emerald-900' : 'bg-stone-100 text-stone-600',
            ]"
          >
            1 老人确认{{ item.elder_confirmed_at ? ' ✓' : '' }}
          </span>
          <span
            :class="[
              'rounded-full px-4 py-2 font-semibold',
              item.family_confirmed_at ? 'bg-emerald-100 text-emerald-900' : 'bg-stone-100 text-stone-600',
            ]"
          >
            2 家属确认{{ item.family_confirmed_at ? ' ✓' : '' }}
          </span>
        </div>

        <div class="mt-5 flex flex-wrap gap-3">
          <button
            v-if="!item.elder_confirmed_at"
            class="min-h-[3.25rem] rounded-2xl bg-ink px-6 text-xl font-semibold text-white active:bg-stone-700 disabled:opacity-60"
            :disabled="busyId === item.id"
            @click="act(item, 'elder')"
          >
            老人已确认
          </button>
          <button
            v-if="item.elder_confirmed_at && !item.family_confirmed_at"
            class="min-h-[3.25rem] rounded-2xl bg-emerald-800 px-6 text-xl font-semibold text-white active:bg-emerald-900 disabled:opacity-60"
            :disabled="busyId === item.id"
            @click="act(item, 'family')"
          >
            家属确认
          </button>
          <button
            class="min-h-[3.25rem] rounded-2xl border-2 border-rose-200 bg-rose-50 px-5 text-xl font-semibold text-rose-900 active:bg-rose-100"
            :disabled="busyId === item.id"
            @click="rejectTarget = item; rejectReason = ''"
          >
            拒绝
          </button>
        </div>
      </article>
    </section>

    <section v-if="done.length" class="rounded-3xl border-2 border-stone-200 bg-white p-5">
      <h2 class="text-2xl font-bold">最近处理过的</h2>
      <div
        v-for="item in done"
        :key="item.id"
        class="flex items-center justify-between gap-3 border-t-2 border-stone-100 py-3 text-xl"
      >
        <span class="min-w-0 truncate">{{ proposedTitle(item) }}</span>
        <span class="shrink-0 text-muted">{{ formatDateTime(item.updated_at) }}</span>
        <span class="shrink-0 rounded-full bg-stone-100 px-3 py-1 font-semibold">
          {{ statusLabels[item.status] ?? item.status }}
        </span>
      </div>
    </section>

    <BaseModal
      :open="Boolean(rejectTarget)"
      title="拒绝这条信息吗"
      confirm-text="确认拒绝"
      danger
      :busy="rejecting"
      @confirm="confirmReject"
      @cancel="rejectTarget = null"
    >
      <div class="space-y-4">
        <p v-if="rejectTarget" class="text-2xl">
          「{{ rejectTarget.payload.proposed?.content ?? '这条信息' }}」将被拒绝，不会生效。
        </p>
        <label class="block">
          <span class="mb-2 block text-xl font-semibold">原因（可以不填）</span>
          <input
            v-model="rejectReason"
            maxlength="200"
            placeholder="例如：说法不准确"
            class="min-h-[3.5rem] w-full rounded-2xl border-2 border-stone-300 bg-white px-5 text-2xl outline-none focus:border-amber-600"
          />
        </label>
      </div>
    </BaseModal>
  </main>
</template>
