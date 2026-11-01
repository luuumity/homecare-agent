<script setup lang="ts">
import { useRouter } from 'vue-router'

defineProps<{
  title: string
  subtitle?: string
}>()

const router = useRouter()
</script>

<template>
  <header class="flex items-start gap-4 border-b-2 border-stone-200 pb-5 max-sm:gap-3 max-sm:pb-3">
    <button
      class="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border-2 border-stone-300 bg-white text-4xl font-bold text-ink shadow-sm active:bg-stone-100 max-sm:h-12 max-sm:w-12 max-sm:text-3xl"
      aria-label="返回首页"
      @click="router.push('/')"
    >
      ←
    </button>
    <div class="min-w-0 flex-1">
      <h1 class="text-4xl font-bold leading-tight max-sm:text-3xl">{{ title }}</h1>
      <p v-if="subtitle" class="mt-1 text-xl text-muted">{{ subtitle }}</p>
    </div>
    <div class="flex shrink-0 items-center gap-3">
      <slot name="actions" />
    </div>
  </header>
</template>
