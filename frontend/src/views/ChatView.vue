<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import {
  api,
  errorMessage,
  type ChatStatus,
  type HistoryMessage,
  type ToolEvent,
} from '../api'
import PageHeader from '../components/PageHeader.vue'

interface Bubble {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  tools?: ToolEvent[]
}

const messages = ref<Bubble[]>([])
const input = ref('')
const busy = ref(false)
const loadingHistory = ref(true)
const error = ref('')
const pendingIds = ref<string[]>([])
const status = ref<ChatStatus | null>(null)
const conversation = ref<HTMLElement | null>(null)

const toolLabels: Record<string, string> = {
  find_items: '查了物品记录',
  save_item: '记下了物品位置',
  update_item: '改了物品记录',
  delete_item: '删了物品记录',
  list_reminders: '查了提醒',
  create_reminder: '设了提醒',
  update_reminder: '改了提醒',
  delete_reminder: '删了提醒',
  list_contacts: '查了联系人',
  request_call: '记了通话请求',
  search_memories: '查了长期记忆',
  save_memory: '记下了一件事',
}

const quickPrompts = [
  '我的老花镜放在哪里？',
  '今天有什么要提醒我的？',
  '帮我记一下，遥控器在床头柜',
]

function toBubble(message: HistoryMessage): Bubble {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    created_at: message.created_at,
  }
}

async function scrollToBottom() {
  await nextTick()
  if (conversation.value) {
    conversation.value.scrollTop = conversation.value.scrollHeight
  }
}

async function loadHistory() {
  loadingHistory.value = true
  error.value = ''
  try {
    const [history, chatStatus] = await Promise.all([api.chat.history(60), api.chat.status()])
    messages.value = history.map(toBubble)
    status.value = chatStatus
    await scrollToBottom()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loadingHistory.value = false
  }
}

async function send(text?: string) {
  const content = (text ?? input.value).trim()
  if (!content || busy.value) return

  error.value = ''
  pendingIds.value = []
  const localUser: Bubble = {
    id: `local-${Date.now()}`,
    role: 'user',
    content,
    created_at: new Date().toISOString(),
  }
  messages.value.push(localUser)
  input.value = ''
  busy.value = true
  await scrollToBottom()

  try {
    const result = await api.chat.send(content)
    messages.value.push({
      id: result.message_id,
      role: 'assistant',
      content: result.reply,
      created_at: result.created_at,
      tools: result.tool_calls,
    })
    pendingIds.value = result.pending_confirmation_ids
  } catch (e) {
    error.value = errorMessage(e)
    messages.value = messages.value.filter((item) => item.id !== localUser.id)
    input.value = content
  } finally {
    busy.value = false
    await scrollToBottom()
  }
}

function handleEnter(event: KeyboardEvent) {
  if (event.isComposing) return
  send()
}

function formatTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
}

onMounted(loadHistory)
</script>

<template>
  <main class="mx-auto flex h-screen max-w-5xl flex-col gap-4 px-8 py-6">
    <PageHeader title="陪我说说话" subtitle="东西放哪、今天要做什么，都可以问我">
      <template #actions>
        <span
          v-if="status"
          :class="[
            'rounded-full px-4 py-2 text-lg font-semibold',
            status.llm_configured ? 'bg-emerald-100 text-emerald-900' : 'bg-amber-100 text-amber-900',
          ]"
        >
          {{ status.llm_configured ? '可以对话' : '模型未配置' }}
        </span>
      </template>
    </PageHeader>

    <p v-if="status && !status.llm_configured" class="rounded-2xl bg-amber-100 px-5 py-3 text-xl text-amber-900">
      后端还没有配置模型密钥，暂时不能对话。请让家属在设置里填写。
    </p>

    <p v-if="pendingIds.length" class="flex items-center justify-between gap-3 rounded-2xl bg-amber-100 px-5 py-3 text-xl text-amber-900">
      <span>这件事需要确认后才生效。</span>
      <router-link to="/confirmations" class="rounded-xl bg-amber-800 px-4 py-2 font-semibold text-white">
        去确认
      </router-link>
    </p>

    <p v-if="error" class="rounded-2xl bg-rose-100 px-5 py-3 text-xl text-rose-900">{{ error }}</p>

    <section
      ref="conversation"
      class="flex-1 space-y-4 overflow-y-auto rounded-3xl border-2 border-stone-200 bg-white px-5 py-5"
    >
      <div v-if="loadingHistory" class="py-10 text-center text-2xl text-muted">正在加载对话…</div>

      <div v-else-if="!messages.length" class="flex h-full flex-col items-center justify-center gap-5 text-center">
        <span class="flex h-20 w-20 items-center justify-center rounded-full bg-amber-100 text-5xl font-bold text-amber-900">
          聊
        </span>
        <p class="text-3xl font-bold">我在这儿</p>
        <p class="max-w-lg text-xl text-muted">可以问我东西放哪、提醒什么时候，也可以让我记一件事。</p>
        <div class="flex flex-wrap justify-center gap-3">
          <button
            v-for="prompt in quickPrompts"
            :key="prompt"
            class="rounded-2xl border-2 border-stone-300 bg-paper px-5 py-3 text-xl font-semibold active:bg-stone-100"
            @click="send(prompt)"
          >
            {{ prompt }}
          </button>
        </div>
      </div>

      <template v-else>
        <article
          v-for="message in messages"
          :key="message.id"
          :class="['flex flex-col', message.role === 'user' ? 'items-end' : 'items-start']"
        >
          <div
            :class="[
              'max-w-[85%] rounded-3xl px-6 py-4 text-2xl leading-relaxed shadow-sm',
              message.role === 'user'
                ? 'bg-ink text-white'
                : 'border-2 border-stone-200 bg-paper text-ink',
            ]"
          >
            <p class="whitespace-pre-wrap break-words">{{ message.content }}</p>
          </div>
          <div class="mt-2 flex flex-wrap items-center gap-2 px-2 text-lg text-muted">
            <span>{{ message.role === 'user' ? '我' : '小陪' }} · {{ formatTime(message.created_at) }}</span>
            <span
              v-for="(tool, index) in message.tools ?? []"
              :key="index"
              :class="[
                'rounded-full px-3 py-1',
                tool.ok ? 'bg-stone-100 text-stone-700' : 'bg-rose-100 text-rose-800',
              ]"
            >
              {{ tool.ok ? toolLabels[tool.name] ?? '操作完成' : '操作没有完成' }}
            </span>
          </div>
        </article>

        <div v-if="busy" class="flex items-center gap-3 text-xl text-muted">
          <span class="h-4 w-4 animate-bounce rounded-full bg-amber-500" />
          <span class="h-4 w-4 animate-bounce rounded-full bg-amber-500 [animation-delay:0.15s]" />
          <span class="h-4 w-4 animate-bounce rounded-full bg-amber-500 [animation-delay:0.3s]" />
          <span>我在想，请稍等…</span>
        </div>
      </template>
    </section>

    <section class="rounded-3xl border-2 border-stone-200 bg-white p-4">
      <div class="flex items-end gap-3">
        <button
          class="flex min-h-[3.5rem] w-[3.5rem] shrink-0 items-center justify-center rounded-2xl border-2 border-stone-300 bg-paper text-xl font-semibold text-muted"
          disabled
          title="语音输入要等平板壳完成后启用"
          aria-label="语音输入暂未启用"
        >
          话筒
        </button>
        <textarea
          v-model="input"
          rows="2"
          maxlength="2000"
          placeholder="点这里打字，或者按下面的按钮发送"
          class="max-h-40 min-h-[3.5rem] flex-1 resize-none rounded-2xl border-2 border-stone-300 bg-paper px-5 py-3 text-2xl leading-snug outline-none focus:border-amber-600"
          @keydown.enter.exact.prevent="handleEnter"
        />
        <button
          class="min-h-[3.5rem] shrink-0 rounded-2xl bg-ink px-7 text-2xl font-semibold text-white disabled:opacity-50"
          :disabled="busy || !input.trim()"
          @click="send()"
        >
          {{ busy ? '等等' : '发送' }}
        </button>
      </div>
      <p class="mt-2 px-1 text-lg text-muted">语音输入会在平板壳完成后启用；现在先用下面的键盘打字。</p>
    </section>
  </main>
</template>
