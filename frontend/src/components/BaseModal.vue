<script setup lang="ts">
withDefaults(
  defineProps<{
    open: boolean
    title: string
    confirmText?: string
    cancelText?: string
    busy?: boolean
    danger?: boolean
    hideConfirm?: boolean
  }>(),
  {
    confirmText: '确定',
    cancelText: '取消',
    busy: false,
    danger: false,
    hideConfirm: false,
  },
)

const emit = defineEmits<{ confirm: []; cancel: [] }>()
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/40 p-4"
      role="dialog"
      aria-modal="true"
      @click.self="emit('cancel')"
    >
      <div class="flex max-h-[90vh] w-full max-w-2xl flex-col rounded-3xl bg-paper shadow-2xl">
        <div class="border-b-2 border-stone-200 px-7 py-5">
          <h2 class="text-3xl font-bold">{{ title }}</h2>
        </div>
        <div class="flex-1 overflow-y-auto px-7 py-6 text-2xl">
          <slot />
        </div>
        <div class="flex justify-end gap-3 border-t-2 border-stone-200 px-7 py-5">
          <slot name="footer-extra" />
          <button
            class="min-h-[3.25rem] rounded-2xl border-2 border-stone-300 bg-white px-6 text-2xl font-semibold active:bg-stone-100"
            :disabled="busy"
            @click="emit('cancel')"
          >
            {{ cancelText }}
          </button>
          <button
            v-if="!hideConfirm"
            :disabled="busy"
            :class="[
              'min-h-[3.25rem] rounded-2xl px-7 text-2xl font-semibold text-white disabled:opacity-60',
              danger ? 'bg-rose-700 active:bg-rose-800' : 'bg-ink active:bg-stone-700',
            ]"
            @click="emit('confirm')"
          >
            {{ busy ? '处理中…' : confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
