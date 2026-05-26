<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    variant?: 'primary' | 'ghost' | 'danger'
    fullWidth?: boolean
  }>(),
  {
    variant: 'primary',
    fullWidth: false,
  },
)

const variantClass = computed(() => {
  if (props.variant === 'ghost') {
    return 'border border-white/60 bg-white/70 text-sa-text hover:bg-white'
  }

  if (props.variant === 'danger') {
    return 'bg-gradient-to-br from-red-700 to-red-900 text-white hover:opacity-95'
  }

  return 'bg-gradient-to-br from-sa-brand to-sa-brand-strong text-white shadow-lg shadow-amber-950/15 hover:opacity-95'
})
</script>

<template>
  <button
    class="inline-flex min-h-12 items-center justify-center rounded-2xl px-4 py-3 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60"
    :class="[variantClass, { 'w-full': fullWidth }]"
    v-bind="$attrs"
  >
    <slot />
  </button>
</template>
