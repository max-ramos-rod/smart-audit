<script setup lang="ts">
import { computed, useId } from 'vue'

import darkMode from '@/assets/brand/dark-mode.svg?raw'
import horizontal from '@/assets/brand/horizontal-logo.svg?raw'
import iconOnly from '@/assets/brand/icon-only.svg?raw'
import lightMode from '@/assets/brand/light-mode.svg?raw'
import primary from '@/assets/brand/primary-logo.svg?raw'

/**
 * BrandLogo — renderiza, inline, o arquivo SVG de marca entregue (exatamente,
 * sem recolorir nem combinar com texto HTML). É inline (não <img>) para que o
 * wordmark herde a fonte Plus Jakarta Sans já carregada na página.
 *
 * Variantes (DR de identidade): superfícies escuras usam 'dark-mode'; claras
 * usam 'primary' / 'horizontal' / 'light-mode'; 'icon' é o símbolo isolado.
 */
const VARIANTS = {
  'dark-mode': darkMode,
  'light-mode': lightMode,
  primary,
  horizontal,
  icon: iconOnly,
} as const

const props = defineProps<{
  variant: keyof typeof VARIANTS
  /** Altura de render em px; a largura segue o aspect-ratio do arquivo. */
  height?: number
}>()

// Os arquivos de wordmark usam classes globais (.logo-text-smart/audit) com
// fills diferentes por variante. Inline, isso vazaria entre instâncias — então
// escopamos os seletores ao id único deste SVG, sem alterar a arte.
const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '')

const markup = computed(() => {
  const id = `brandlogo-${uid}`
  return VARIANTS[props.variant]
    .replace('<svg ', `<svg id="${id}" `)
    .replace(/\.logo-text-smart/g, `#${id} .logo-text-smart`)
    .replace(/\.logo-text-audit/g, `#${id} .logo-text-audit`)
})
</script>

<template>
  <!-- eslint-disable-next-line vue/no-v-html (conteúdo confiável: asset empacotado) -->
  <span
    class="brand-logo"
    :style="height ? { height: `${height}px` } : undefined"
    aria-label="Smart Audit"
    role="img"
    v-html="markup"
  />
</template>

<style scoped>
.brand-logo {
  display: inline-flex;
  align-items: center;
}
.brand-logo :deep(svg) {
  display: block;
  height: 100%;
  width: auto;
}
</style>
