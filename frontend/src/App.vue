<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import BrandLogo from '@/components/ui/BrandLogo.vue'
import { readAccessToken } from '@/services/api/storage'
import { useContextStore } from '@/stores/context/context.store'

const STEPS = ['Conectando ao servidor...', 'Carregando contexto...', 'Verificando permissões...', 'Pronto!']

const contextStore = useContextStore()
const splash = ref(Boolean(readAccessToken()))
const step = ref(0)

const pct = computed(() => Math.round((step.value / STEPS.length) * 100))

onMounted(async () => {
  if (!splash.value) return

  const timers = STEPS.map((_, i) => setTimeout(() => { step.value = i + 1 }, (i + 1) * 500))

  await Promise.all([
    new Promise<void>(r => setTimeout(r, STEPS.length * 500)),
    new Promise<void>(r => {
      if (!contextStore.isLoading) return r()
      const stop = watch(() => contextStore.isLoading, v => { if (!v) { stop(); r() } })
    }),
  ])

  await new Promise(r => setTimeout(r, 400))
  timers.forEach(clearTimeout)
  splash.value = false
})
</script>

<template>
  <div>
  <Transition name="splash-fade">
    <div v-if="splash" class="splash-root">
      <div class="splash-inner">
        <div class="splash-logo">
          <BrandLogo variant="dark-mode" :height="46" />
        </div>
        <div class="splash-bar-wrap">
          <div class="splash-bar-fill" :style="{ width: pct + '%' }" />
        </div>
        <div class="splash-status">{{ step > 0 && step <= STEPS.length ? STEPS[step - 1] : '' }}</div>
        <div class="splash-dots">
          <span
            v-for="(_, i) in STEPS"
            :key="i"
            :style="{ background: i < step ? 'var(--sa-brand)' : 'rgba(255,255,255,.15)' }"
          />
        </div>
      </div>
    </div>
  </Transition>
  <router-view />
  </div>
</template>

<style>
.splash-root {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: var(--sa-nav);
  display: flex;
  align-items: center;
  justify-content: center;
}
.splash-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  width: 260px;
}
.splash-logo {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 40px;
}
.splash-mark {
  width: 48px;
  height: 48px;
  background: var(--sa-brand);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 18px;
  color: #fff;
  flex-shrink: 0;
}
.splash-name {
  font-size: 22px;
  font-weight: 800;
  color: #fff;
  letter-spacing: -.02em;
  line-height: 1.1;
}
.splash-sub {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .14em;
  text-transform: uppercase;
  color: rgba(255,255,255,.3);
  margin-top: 3px;
}
.splash-bar-wrap {
  width: 100%;
  height: 3px;
  background: rgba(255,255,255,.08);
  border-radius: 99px;
  overflow: hidden;
  margin-bottom: 16px;
}
.splash-bar-fill {
  height: 100%;
  background: var(--sa-brand);
  border-radius: 99px;
  width: 0%;
  transition: width .4s ease;
}
.splash-status {
  font-size: 12px;
  color: rgba(255,255,255,.35);
  font-weight: 500;
  letter-spacing: .01em;
  margin-bottom: 20px;
}
.splash-dots {
  display: flex;
  gap: 6px;
}
.splash-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255,255,255,.15);
  transition: background .3s;
}
.splash-fade-leave-active {
  transition: opacity .4s ease;
}
.splash-fade-leave-to {
  opacity: 0;
}
</style>
