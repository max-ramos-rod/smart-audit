<script setup lang="ts">
import { ICONS, type IconName } from './AppIcons'
defineProps<{ name: IconName; size?: number }>()
</script>

<template>
  <span
    :style="{
      display: 'inline-flex',
      width: (size ?? 17) + 'px',
      height: (size ?? 17) + 'px',
      flexShrink: 0,
    }"
    v-html="ICONS[name]"
  />
</template>
