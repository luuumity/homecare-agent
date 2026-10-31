<script setup lang="ts">
defineProps<{
  mark?: string
  title: string
  hint?: string
}>()
</script>

<template>
  <div class="flex flex-col items-center gap-3 rounded-3xl border-2 border-dashed border-stone-300 bg-white/60 px-6 py-12 text-center">
    <span class="flex h-16 w-16 items-center justify-center rounded-full bg-stone-100 text-4xl font-bold text-muted">
      {{ mark ?? '空' }}
    </span>
    <p class="text-2xl font-semibold">{{ title }}</p>
    <p v-if="hint" class="max-w-md text-xl text-muted">{{ hint }}</p>
    <slot />
  </div>
</template>
