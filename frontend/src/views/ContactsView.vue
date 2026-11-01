<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, errorMessage, type CallLog, type Contact } from '../api'
import BaseModal from '../components/BaseModal.vue'
import EmptyState from '../components/EmptyState.vue'
import PageHeader from '../components/PageHeader.vue'
import { callStatusLabels, formatDateTime } from '../utils'

const contacts = ref<Contact[]>([])
const calls = ref<CallLog[]>([])
const loading = ref(true)
const error = ref('')
const notice = ref('')

const callTarget = ref<Contact | null>(null)
const calling = ref(false)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [contactList, callList] = await Promise.all([api.contacts.list(), api.calls.list(8)])
    contacts.value = contactList
    calls.value = callList
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

async function confirmCall() {
  if (!callTarget.value) return
  calling.value = true
  notice.value = ''
  try {
    await api.calls.create({
      contact_id: callTarget.value.id,
      status: 'initiated',
      note: '网页大屏发起',
    })
    notice.value = `已记录给${callTarget.value.name}的通话请求。当前网页版不会真的拨号，平板壳完成后才会执行。`
    callTarget.value = null
    await load()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    calling.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="mx-auto flex min-h-screen max-w-5xl flex-col gap-5 px-4 sm:px-8 py-6">
    <PageHeader title="打电话" subtitle="只能打给名单里的家人，不能接外面电话" />

    <p v-if="notice" class="rounded-2xl bg-emerald-100 px-5 py-3 text-xl text-emerald-900">{{ notice }}</p>
    <p v-if="error" class="rounded-2xl bg-rose-100 px-5 py-3 text-xl text-rose-900">{{ error }}</p>

    <section v-if="loading" class="py-12 text-center text-2xl text-muted">正在加载…</section>

    <EmptyState
      v-else-if="!contacts.length"
      mark="电"
      title="还没有联系人"
      hint="家属需要先在后台把可以拨打的人加进名单。"
    />

    <section v-else class="grid gap-4 sm:grid-cols-2">
      <article
        v-for="contact in contacts"
        :key="contact.id"
        class="flex flex-col justify-between gap-4 rounded-3xl border-2 border-stone-200 bg-white p-5 shadow-sm"
      >
        <div>
          <p class="text-3xl font-bold">{{ contact.name }}</p>
          <p class="mt-1 text-xl text-muted">
            {{ contact.relation ?? '家人' }} · {{ contact.phone_desensitized }}
          </p>
        </div>
        <button
          class="min-h-[3.5rem] rounded-2xl bg-ink text-2xl font-semibold text-white active:bg-stone-700"
          @click="callTarget = contact"
        >
          给{{ contact.name }}打电话
        </button>
      </article>
    </section>

    <section v-if="calls.length" class="rounded-3xl border-2 border-stone-200 bg-white p-5">
      <h2 class="text-2xl font-bold">最近的通话记录</h2>
      <div
        v-for="log in calls"
        :key="log.id"
        class="flex items-center justify-between gap-4 border-t-2 border-stone-100 py-3 text-xl"
      >
        <span class="font-semibold">{{ log.contact_name }}</span>
        <span class="text-muted">{{ formatDateTime(log.created_at) }}</span>
        <span
          :class="[
            'rounded-full px-3 py-1',
            log.status === 'completed'
              ? 'bg-emerald-100 text-emerald-900'
              : log.status === 'failed'
                ? 'bg-rose-100 text-rose-900'
                : 'bg-stone-100 text-stone-700',
          ]"
        >
          {{ callStatusLabels[log.status] ?? log.status }}
        </span>
      </div>
    </section>

    <BaseModal
      :open="Boolean(callTarget)"
      title="现在打电话吗"
      :confirm-text="callTarget ? `给${callTarget.name}打` : '拨打'"
      :busy="calling"
      @confirm="confirmCall"
      @cancel="callTarget = null"
    >
      <div v-if="callTarget" class="space-y-4">
        <p class="text-2xl">
          将联系 <span class="font-bold">{{ callTarget.name }}</span>
          <span class="text-muted">（{{ callTarget.phone_desensitized }}）</span>
        </p>
        <p class="rounded-2xl bg-amber-100 px-4 py-3 text-xl text-amber-900">
          网页版只会记录这次请求，不会真的拨号。平板壳完成后才会自动拨打。
        </p>
      </div>
    </BaseModal>
  </main>
</template>
