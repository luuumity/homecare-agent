<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { api, errorMessage, type Item } from '../api'
import BaseModal from '../components/BaseModal.vue'
import EmptyState from '../components/EmptyState.vue'
import PageHeader from '../components/PageHeader.vue'

const items = ref<Item[]>([])
const query = ref('')
const loading = ref(true)
const error = ref('')
const notice = ref('')

const formOpen = ref(false)
const editingId = ref<string | null>(null)
const form = ref({ name: '', location: '', note: '' })
const saving = ref(false)
const formError = ref('')

const deleteTarget = ref<Item | null>(null)
const deleting = ref(false)

let searchTimer: number | undefined

async function load() {
  loading.value = true
  error.value = ''
  try {
    items.value = await api.items.list(query.value.trim())
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.value = { name: '', location: '', note: '' }
  formError.value = ''
  formOpen.value = true
}

function openEdit(item: Item) {
  editingId.value = item.id
  form.value = { name: item.name, location: item.location, note: item.note ?? '' }
  formError.value = ''
  formOpen.value = true
}

async function save() {
  formError.value = ''
  if (!form.value.name.trim() || !form.value.location.trim()) {
    formError.value = '东西的名称和位置都要填'
    return
  }
  saving.value = true
  try {
    const body = {
      name: form.value.name.trim(),
      location: form.value.location.trim(),
      note: form.value.note.trim() || null,
    }
    if (editingId.value) {
      await api.items.update(editingId.value, body)
      notice.value = '位置已经改好了'
    } else {
      await api.items.create(body)
      notice.value = '新的位置记好了'
    }
    formOpen.value = false
    await load()
  } catch (e) {
    formError.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await api.items.remove(deleteTarget.value.id)
    notice.value = '这条记录已经删除'
    deleteTarget.value = null
    await load()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    deleting.value = false
  }
}

watch(query, () => {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(load, 300)
})

onMounted(load)
</script>

<template>
  <main class="mx-auto flex min-h-screen max-w-5xl flex-col gap-5 px-4 sm:px-8 py-6">
    <PageHeader title="东西放哪了" subtitle="记下位置，找起来不费劲">
      <template #actions>
        <button
          class="min-h-[3.25rem] rounded-2xl bg-ink px-6 text-xl font-semibold text-white active:bg-stone-700"
          @click="openCreate"
        >
          记新东西
        </button>
      </template>
    </PageHeader>

    <div class="flex items-center gap-3">
      <input
        v-model="query"
        type="search"
        placeholder="找一找，比如老花镜、遥控器"
        class="min-h-[3.5rem] flex-1 rounded-2xl border-2 border-stone-300 bg-white px-5 text-2xl outline-none focus:border-amber-600"
      />
      <button
        class="min-h-[3.5rem] rounded-2xl border-2 border-stone-300 bg-white px-6 text-xl font-semibold active:bg-stone-100"
        @click="load"
      >
        {{ loading ? '查找中' : '查找' }}
      </button>
    </div>

    <p v-if="notice" class="rounded-2xl bg-emerald-100 px-5 py-3 text-xl text-emerald-900">{{ notice }}</p>
    <p v-if="error" class="rounded-2xl bg-rose-100 px-5 py-3 text-xl text-rose-900">{{ error }}</p>

    <section v-if="loading" class="py-12 text-center text-2xl text-muted">正在加载…</section>

    <EmptyState
      v-else-if="!items.length"
      mark="物"
      title="还没有找到记录"
      :hint="query ? '换个说法再找找，或者记一条新的。' : '把常用的东西放在哪里记下来，以后一问就知道。'"
    >
      <button
        class="min-h-[3.25rem] rounded-2xl bg-ink px-6 text-xl font-semibold text-white"
        @click="openCreate"
      >
        记一条
      </button>
    </EmptyState>

    <section v-else class="space-y-4">
      <article
        v-for="item in items"
        :key="item.id"
        class="rounded-3xl border-2 border-stone-200 bg-white p-5 shadow-sm"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <p class="text-3xl font-bold">{{ item.name }}</p>
            <p class="mt-2 text-2xl text-amber-900">
              放在 <span class="font-bold">{{ item.location }}</span>
            </p>
            <p v-if="item.note" class="mt-1 text-xl text-muted">{{ item.note }}</p>
          </div>
          <div class="flex shrink-0 gap-2">
            <button
              class="min-h-[3rem] rounded-xl border-2 border-stone-300 bg-paper px-4 text-xl font-semibold active:bg-stone-100"
              @click="openEdit(item)"
            >
              改位置
            </button>
            <button
              class="min-h-[3rem] rounded-xl border-2 border-rose-200 bg-rose-50 px-4 text-xl font-semibold text-rose-900 active:bg-rose-100"
              @click="deleteTarget = item"
            >
              删除
            </button>
          </div>
        </div>
      </article>
    </section>

    <BaseModal
      :open="formOpen"
      :title="editingId ? '改一下位置' : '记一件东西'"
      :confirm-text="editingId ? '保存修改' : '记下来'"
      :busy="saving"
      @confirm="save"
      @cancel="formOpen = false"
    >
      <div class="space-y-5">
        <label class="block">
          <span class="mb-2 block text-xl font-semibold">东西叫什么</span>
          <input
            v-model="form.name"
            maxlength="100"
            placeholder="例如：老花镜"
            class="min-h-[3.5rem] w-full rounded-2xl border-2 border-stone-300 bg-white px-5 text-2xl outline-none focus:border-amber-600"
          />
        </label>
        <label class="block">
          <span class="mb-2 block text-xl font-semibold">放在哪里</span>
          <input
            v-model="form.location"
            maxlength="200"
            placeholder="例如：床头柜第二层"
            class="min-h-[3.5rem] w-full rounded-2xl border-2 border-stone-300 bg-white px-5 text-2xl outline-none focus:border-amber-600"
          />
        </label>
        <label class="block">
          <span class="mb-2 block text-xl font-semibold">备注（可以不填）</span>
          <input
            v-model="form.note"
            maxlength="500"
            placeholder="例如：黑色镜框"
            class="min-h-[3.5rem] w-full rounded-2xl border-2 border-stone-300 bg-white px-5 text-2xl outline-none focus:border-amber-600"
          />
        </label>
        <p v-if="formError" class="rounded-xl bg-rose-100 px-4 py-3 text-xl text-rose-900">{{ formError }}</p>
      </div>
    </BaseModal>

    <BaseModal
      :open="Boolean(deleteTarget)"
      title="确定删除这条记录吗"
      confirm-text="删除"
      danger
      :busy="deleting"
      @confirm="confirmDelete"
      @cancel="deleteTarget = null"
    >
      <p v-if="deleteTarget">
        「{{ deleteTarget.name }}」放在「{{ deleteTarget.location }}」的记录会被删除，以后就查不到了。
      </p>
    </BaseModal>
  </main>
</template>
