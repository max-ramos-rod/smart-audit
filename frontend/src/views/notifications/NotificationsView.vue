<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import AppShell from '@/components/layout/AppShell.vue'
import SvgIcon from '@/components/ui/SvgIcon.vue'
import { useSubmissionsStore } from '@/stores/submissions/submissions.store'

const submissionsStore = useSubmissionsStore()

onMounted(async () => {
  if (!submissionsStore.items.length) await submissionsStore.load(1, 100)
})

type NotifType = 'warn' | 'ok' | 'info' | 'err'

interface Notif {
  id: string
  type: NotifType
  title: string
  desc: string
  time: string
  read: boolean
}

const notifications = computed<Notif[]>(() => {
  const now = Date.now()
  const notifs: Notif[] = []

  for (const s of submissionsStore.items) {
    const started = new Date(s.started_at).getTime()
    const hoursAgo = Math.floor((now - started) / 36e5)

    if (s.status === 'in_progress' && hoursAgo >= 24) {
      notifs.push({
        id: `pending-${s.id}`,
        type: 'warn',
        title: `Inspeção pendente há ${hoursAgo >= 48 ? `${Math.floor(hoursAgo / 24)} dias` : `${hoursAgo}h`}`,
        desc: `${s.form_name} iniciada em ${new Date(s.started_at).toLocaleDateString('pt-BR')} sem finalização.`,
        time: `${hoursAgo}h atrás`,
        read: false,
      })
    }

    if (s.status === 'completed' && s.score !== null && s.score < 80) {
      notifs.push({
        id: `low-score-${s.id}`,
        type: 'err',
        title: 'Score abaixo do mínimo',
        desc: `${s.form_name}: ${s.score}% (mínimo recomendado: 80%).`,
        time: s.finished_at ? new Date(s.finished_at).toLocaleDateString('pt-BR') : '',
        read: true,
      })
    }

    if (s.status === 'completed' && s.score !== null && s.score >= 90) {
      notifs.push({
        id: `good-score-${s.id}`,
        type: 'ok',
        title: 'Inspeção concluída com excelência',
        desc: `${s.form_name}: score ${s.score}%.`,
        time: s.finished_at ? new Date(s.finished_at).toLocaleDateString('pt-BR') : '',
        read: true,
      })
    }
  }

  return notifs.slice(0, 20)
})

const filter = ref<'all' | 'unread'>('all')
const readIds    = ref<Set<string>>(new Set())
const dismissIds = ref<Set<string>>(new Set())

function isRead(n: Notif)      { return n.read || readIds.value.has(n.id) }
function isDismissed(n: Notif) { return dismissIds.value.has(n.id) }

const visible = computed(() =>
  notifications.value
    .filter(n => !isDismissed(n))
    .filter(n => filter.value === 'unread' ? !isRead(n) : true)
)

const unreadCount = computed(() =>
  notifications.value.filter(n => !isDismissed(n) && !isRead(n)).length
)

function markRead(id: string) {
  readIds.value = new Set([...readIds.value, id])
}

function dismiss(id: string) {
  dismissIds.value = new Set([...dismissIds.value, id])
}

function markAllRead() {
  const allIds = notifications.value.map(n => n.id)
  readIds.value = new Set(allIds)
}

const typeColor: Record<NotifType, string> = {
  ok:   'var(--sa-ok)',
  warn: 'var(--sa-warn)',
  err:  'var(--sa-danger)',
  info: 'var(--sa-brand)',
}
const typeBg: Record<NotifType, string> = {
  ok:   'var(--sa-ok-bg)',
  warn: 'var(--sa-warn-bg)',
  err:  'var(--sa-err-bg)',
  info: 'var(--sa-brand-soft)',
}
const typeSymbol: Record<NotifType, string> = { ok: '✓', warn: '!', err: '✕', info: 'i' }
</script>

<template>
  <AppShell>
    <div class="page">

      <div class="phdr">
        <div>
          <div class="eyebrow">Central</div>
          <h1 class="page-h1">Notificações</h1>
          <p class="page-desc">{{ unreadCount > 0 ? `${unreadCount} não lidas` : 'Tudo em dia' }}</p>
        </div>
        <button
          v-if="unreadCount > 0"
          type="button"
          class="btn-secondary btn-sm"
          @click="markAllRead"
        >
          Marcar todas como lidas
        </button>
      </div>

      <!-- Filter tabs -->
      <div class="filter-tabs">
        <button type="button" class="filter-tab" :class="{ active: filter === 'all' }"    @click="filter = 'all'">Todas</button>
        <button type="button" class="filter-tab" :class="{ active: filter === 'unread' }" @click="filter = 'unread'">
          Não lidas{{ unreadCount > 0 ? ` (${unreadCount})` : '' }}
        </button>
      </div>

      <!-- Empty -->
      <div v-if="!visible.length" class="empty">
        <div class="empty-h">Nenhuma notificação</div>
        <p class="empty-p">{{ filter === 'unread' ? 'Todas as notificações foram lidas.' : 'Você está em dia com os alertas operacionais.' }}</p>
      </div>

      <!-- List -->
      <div v-else style="display:flex;flex-direction:column;gap:6px;">
        <div
          v-for="n in visible"
          :key="n.id"
          class="card"
          style="padding:14px 16px;display:flex;gap:12px;align-items:flex-start;"
          :style="{
            opacity: isRead(n) ? 0.7 : 1,
            borderLeft: !isRead(n) ? '3px solid var(--sa-brand)' : '1px solid var(--sa-line)',
          }"
        >
          <!-- Icon -->
          <div :style="{
            width:'34px', height:'34px', borderRadius:'50%', flexShrink:0,
            background: typeBg[n.type],
            display:'flex', alignItems:'center', justifyContent:'center',
            fontSize:'14px', fontWeight:'800',
            color: typeColor[n.type],
          }">
            {{ typeSymbol[n.type] }}
          </div>

          <!-- Content -->
          <div style="flex:1;min-width:0;">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:2px;">
              <div :style="{
                fontSize:'13px',
                fontWeight: isRead(n) ? '500' : '700',
                color:'var(--sa-text)',
                overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap',
              }">{{ n.title }}</div>
              <span style="font-size:11px;color:var(--sa-muted);flex-shrink:0;">{{ n.time }}</span>
            </div>
            <div style="font-size:12px;color:var(--sa-muted);line-height:1.5;">{{ n.desc }}</div>
            <button
              v-if="!isRead(n)"
              type="button"
              @click="markRead(n.id)"
              style="border:none;background:none;cursor:pointer;font-size:11px;color:var(--sa-brand);font-weight:600;padding:4px 0 0;font-family:inherit;"
            >
              Marcar como lida
            </button>
          </div>

          <!-- Dismiss -->
          <button
            type="button"
            @click="dismiss(n.id)"
            style="border:none;background:none;cursor:pointer;color:var(--sa-muted);padding:0;display:flex;align-items:center;justify-content:center;flex-shrink:0;"
          >
            <SvgIcon name="close" :size="14" />
          </button>
        </div>
      </div>

      <div style="margin-top:20px;" class="info-box">
        Notificações geradas automaticamente a partir do estado das inspeções. Um módulo de eventos em tempo real está previsto para uma próxima fase.
      </div>

    </div>
  </AppShell>
</template>
