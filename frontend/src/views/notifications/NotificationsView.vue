<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import AppShell from '@/components/layout/AppShell.vue'
import { useSubmissionsStore } from '@/stores/submissions/submissions.store'

const submissionsStore = useSubmissionsStore()

onMounted(async () => {
  if (!submissionsStore.items.length) await submissionsStore.load(1, 100)
})

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

  for (const submission of submissionsStore.items) {
    const started = new Date(submission.started_at).getTime()
    const hoursAgo = Math.floor((now - started) / 36e5)

    if (submission.status === 'in_progress' && hoursAgo >= 24) {
      notifs.push({
        id: `pending-${submission.id}`,
        type: 'warn',
        title: `Inspecao pendente ha ${hoursAgo >= 48 ? `${Math.floor(hoursAgo / 24)} dias` : `${hoursAgo}h`}`,
        desc: `${submission.form_name} iniciada em ${new Date(submission.started_at).toLocaleDateString('pt-BR')} sem finalizacao.`,
        time: `${hoursAgo}h atras`,
        read: false,
      })
    }

    if (submission.status === 'completed' && submission.score !== null && submission.score < 80) {
      notifs.push({
        id: `low-score-${submission.id}`,
        type: 'err',
        title: 'Score abaixo do minimo',
        desc: `${submission.form_name}: ${submission.score}% (minimo recomendado: 80%).`,
        time: submission.finished_at ? new Date(submission.finished_at).toLocaleDateString('pt-BR') : '',
        read: true,
      })
    }

    if (submission.status === 'completed' && submission.score !== null && submission.score >= 90) {
      notifs.push({
        id: `good-score-${submission.id}`,
        type: 'ok',
        title: 'Inspecao concluida com excelencia',
        desc: `${submission.form_name}: score ${submission.score}%.`,
        time: submission.finished_at ? new Date(submission.finished_at).toLocaleDateString('pt-BR') : '',
        read: true,
      })
    }
  }

  return notifs.slice(0, 20)
})

const unread = computed(() => notifications.value.filter((notification) => !notification.read).length)
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

const typeSymbol: Record<string, string> = { ok: 'OK', warn: '!', err: 'X', info: 'i' }
</script>

<template>
  <AppShell>
    <div class="page">
      <div class="phdr">
        <div>
          <div class="eyebrow">Central</div>
          <h1 class="page-h1">Notificacoes</h1>
          <p class="page-desc">
            {{ unread > 0 && !readAll ? `${unread} nao lidas` : 'Tudo em dia' }}
          </p>
        </div>
        <button
          v-if="unread > 0 && !readAll"
          class="btn-secondary btn-sm"
          @click="readAll = true"
          type="button"
        >
          Marcar todas como lidas
        </button>
      </div>

      <div class="info-box" style="margin-bottom: 16px;">
        Estas notificacoes sao derivadas do estado atual das inspecoes. Ainda nao existe um modulo dedicado de eventos em tempo real.
      </div>

      <div v-if="!notifications.length" class="empty">
        <div class="empty-h">Nenhuma notificacao</div>
        <p class="empty-p">Voce esta em dia com os alertas operacionais disponiveis hoje.</p>
      </div>

      <div v-else style="display: flex; flex-direction: column; gap: 6px;">
        <div
          v-for="notification in notifications"
          :key="notification.id"
          class="card"
          style="padding: 14px 16px; display: flex; gap: 12px; align-items: flex-start;"
          :style="{
            opacity: notification.read || readAll ? 0.7 : 1,
            borderLeft: !notification.read && !readAll ? '3px solid var(--sa-brand)' : '1px solid var(--sa-line)',
          }"
        >
          <div
            :style="{
              width: '34px',
              height: '34px',
              borderRadius: '50%',
              flexShrink: 0,
              background: typeBg[notification.type],
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '14px',
              fontWeight: '800',
              color: typeColors[notification.type],
            }"
          >
            {{ typeSymbol[notification.type] }}
          </div>

          <div style="flex: 1; min-width: 0;">
            <div
              style="display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 2px;"
            >
              <div
                style="font-size: 13px; font-weight: 700; color: var(--sa-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"
              >
                {{ notification.title }}
              </div>
              <span style="font-size: 11px; color: var(--sa-muted); flex-shrink: 0;">{{ notification.time }}</span>
            </div>
            <div style="font-size: 12px; color: var(--sa-muted); line-height: 1.5;">{{ notification.desc }}</div>
          </div>
        </div>
      </div>
    </div>
  </AppShell>
</template>
