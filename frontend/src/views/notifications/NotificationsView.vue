<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import { useSubmissionsStore } from '@/stores/submissions/submissions.store'

const router = useRouter()
const submissionsStore = useSubmissionsStore()

onMounted(async () => {
  if (!submissionsStore.items.length) await submissionsStore.load(1, 100)
})

// Gera notificações a partir dos dados reais de inspeções
const notifications = computed(() => {
  const now = Date.now()
  const notifs: Array<{
    id: string
    type: 'warn' | 'ok' | 'info' | 'err'
    title: string
    desc: string
    time: string
    read: boolean
  }> = []

  for (const s of submissionsStore.items) {
    const started = new Date(s.started_at).getTime()
    const hoursAgo = Math.floor((now - started) / 36e5)

    if (s.status === 'in_progress' && hoursAgo >= 24) {
      notifs.push({
        id: 'pending-' + s.id,
        type: 'warn',
        title: 'Inspeção pendente há ' + (hoursAgo >= 48 ? Math.floor(hoursAgo/24) + ' dias' : hoursAgo + 'h'),
        desc: s.form_name + ' iniciada em ' + new Date(s.started_at).toLocaleDateString('pt-BR') + ' sem finalização.',
        time: hoursAgo + 'h atrás',
        read: false,
      })
    }

    if (s.status === 'completed' && s.score !== null && s.score < 80) {
      notifs.push({
        id: 'low-score-' + s.id,
        type: 'err',
        title: 'Score abaixo do mínimo',
        desc: s.form_name + ': ' + s.score + '% (mínimo recomendado: 80%).',
        time: s.finished_at ? new Date(s.finished_at).toLocaleDateString('pt-BR') : '',
        read: true,
      })
    }

    if (s.status === 'completed' && s.score !== null && s.score >= 90) {
      notifs.push({
        id: 'good-score-' + s.id,
        type: 'ok',
        title: 'Inspeção concluída com excelência',
        desc: s.form_name + ': score ' + s.score + '%.',
        time: s.finished_at ? new Date(s.finished_at).toLocaleDateString('pt-BR') : '',
        read: true,
      })
    }
  }

  return notifs.slice(0, 20)
})

const unread = computed(() => notifications.value.filter(n => !n.read).length)

const readAll = ref(false)

const typeColors: Record<string, string> = {
  ok: 'var(--sa-ok)',
  warn: 'var(--sa-warn)',
  err: 'var(--sa-danger)',
  info: 'var(--sa-brand)',
}
const typeBg: Record<string, string> = {
  ok: 'var(--sa-ok-bg)',
  warn: 'var(--sa-warn-bg)',
  err: 'var(--sa-err-bg)',
  info: 'var(--sa-brand-soft)',
}
const typeSymbol: Record<string, string> = { ok: '✓', warn: '!', err: '✕', info: 'i' }
</script>

<template>
  <AppShell>
    <div class="page">

      <div class="phdr">
        <div>
          <div class="eyebrow">Central</div>
          <h1 class="page-h1">Notificações</h1>
          <p class="page-desc">{{ unread > 0 && !readAll ? unread + ' não lidas' : 'Tudo em dia' }}</p>
        </div>
        <button v-if="unread > 0 && !readAll" class="btn-secondary btn-sm" @click="readAll = true" type="button">
          Marcar todas como lidas
        </button>
      </div>

      <div v-if="!notifications.length" style="text-align:center;padding:48px 0;">
        <div style="font-size:32px;margin-bottom:12px;">🔔</div>
        <div style="font-size:15px;font-weight:600;color:var(--sa-text);margin-bottom:6px;">Nenhuma notificação</div>
        <div style="font-size:13px;color:var(--sa-muted);">Você está em dia com tudo.</div>
      </div>

      <div v-else style="display:flex;flex-direction:column;gap:6px;">
        <div
          v-for="n in notifications"
          :key="n.id"
          class="card"
          style="padding:14px 16px;display:flex;gap:12px;align-items:flex-start;"
          :style="{
            opacity: (n.read || readAll) ? 0.7 : 1,
            borderLeft: (!n.read && !readAll) ? '3px solid var(--sa-brand)' : '1px solid var(--sa-line)',
          }"
        >
          <!-- Icon -->
          <div :style="{ width:'34px',height:'34px',borderRadius:'50%',flexShrink:0,background:typeBg[n.type],display:'flex',alignItems:'center',justifyContent:'center',fontSize:'14px',fontWeight:'800',color:typeColors[n.type] }">
            {{ typeSymbol[n.type] }}
          </div>

          <!-- Content -->
          <div style="flex:1;min-width:0;">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:2px;">
              <div style="font-size:13px;font-weight:700;color:var(--sa-text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ n.title }}</div>
              <span style="font-size:11px;color:var(--sa-muted);flex-shrink:0;">{{ n.time }}</span>
            </div>
            <div style="font-size:12px;color:var(--sa-muted);line-height:1.5;">{{ n.desc }}</div>
          </div>
        </div>
      </div>

      <div style="margin-top:24px;padding:12px 14px;background:var(--sa-brand-soft);border:1px solid rgba(37,99,235,.15);border-radius:8px;font-size:12px;color:var(--sa-brand);line-height:1.6;">
        <strong>Nota:</strong> Estas notificações são geradas automaticamente a partir do estado das inspeções.
        Um módulo de notificações em tempo real está previsto para uma próxima fase.
      </div>

    </div>
  </AppShell>
</template>
