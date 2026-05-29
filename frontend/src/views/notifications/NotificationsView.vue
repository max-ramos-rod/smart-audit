<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import AppShell from '@/components/layout/AppShell.vue'
import SvgIcon from '@/components/ui/SvgIcon.vue'
import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type NotificationItem,
} from '@/services/notifications.service'

const notifications = ref<NotificationItem[]>([])
const isLoading = ref(true)
const loadError = ref<string | null>(null)

onMounted(async () => {
  try {
    notifications.value = await fetchNotifications()
  } catch {
    loadError.value = 'Não foi possível carregar as notificações.'
  } finally {
    isLoading.value = false
  }
})

const filter = ref<'all' | 'unread'>('all')
const dismissIds = ref<Set<string>>(new Set())

function isDismissed(n: NotificationItem) { return dismissIds.value.has(n.id) }
function isRead(n: NotificationItem)      { return n.read }

const visible = computed(() =>
  notifications.value
    .filter(n => !isDismissed(n))
    .filter(n => filter.value === 'unread' ? !isRead(n) : true),
)

const unreadCount = computed(() =>
  notifications.value.filter(n => !isDismissed(n) && !isRead(n)).length,
)

async function markRead(n: NotificationItem) {
  try {
    await markNotificationRead(n.id)
    n.read = true
  } catch {
    // silently ignore — UI already optimistic
  }
}

function dismiss(id: string) {
  dismissIds.value = new Set([...dismissIds.value, id])
}

async function markAllRead() {
  const unreadKeys = notifications.value
    .filter(n => !isDismissed(n) && !isRead(n))
    .map(n => n.id)
  if (!unreadKeys.length) return
  try {
    await markAllNotificationsRead(unreadKeys)
    notifications.value.forEach(n => { n.read = true })
  } catch {
    // silently ignore
  }
}

type NotifType = NotificationItem['type']

const typeColor: Record<NotifType, string> = {
  excellent: 'var(--sa-ok)',
  pending:   'var(--sa-warn)',
  low_score: 'var(--sa-danger)',
}
const typeBg: Record<NotifType, string> = {
  excellent: 'var(--sa-ok-bg)',
  pending:   'var(--sa-warn-bg)',
  low_score: 'var(--sa-err-bg)',
}
const typeSymbol: Record<NotifType, string> = {
  excellent: '✓',
  pending:   '!',
  low_score: '✕',
}
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

      <p v-if="loadError" style="font-size:13px;font-weight:600;color:var(--sa-danger);margin-bottom:12px;">
        {{ loadError }}
      </p>
      <p v-else-if="isLoading" style="font-size:13px;color:var(--sa-muted);margin-bottom:12px;">
        Carregando notificações...
      </p>

      <template v-else>
        <div class="filter-tabs">
          <button type="button" class="filter-tab" :class="{ active: filter === 'all' }"    @click="filter = 'all'">Todas</button>
          <button type="button" class="filter-tab" :class="{ active: filter === 'unread' }" @click="filter = 'unread'">
            Não lidas{{ unreadCount > 0 ? ` (${unreadCount})` : '' }}
          </button>
        </div>

        <div v-if="!visible.length" class="empty">
          <div class="empty-h">Nenhuma notificação</div>
          <p class="empty-p">
            {{ filter === 'unread' ? 'Todas as notificações foram lidas.' : 'Você está em dia com os alertas operacionais.' }}
          </p>
        </div>

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
            <div :style="{
              width:'34px', height:'34px', borderRadius:'50%', flexShrink:0,
              background: typeBg[n.type],
              display:'flex', alignItems:'center', justifyContent:'center',
              fontSize:'14px', fontWeight:'800',
              color: typeColor[n.type],
            }">
              {{ typeSymbol[n.type] }}
            </div>

            <div style="flex:1;min-width:0;">
              <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:2px;">
                <div :style="{
                  fontSize:'13px',
                  fontWeight: isRead(n) ? '500' : '700',
                  color:'var(--sa-text)',
                  overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap',
                }">{{ n.title }}</div>
                <span style="font-size:11px;color:var(--sa-muted);flex-shrink:0;">
                  {{ new Date(n.created_at).toLocaleDateString('pt-BR') }}
                </span>
              </div>
              <div style="font-size:12px;color:var(--sa-muted);line-height:1.5;">{{ n.description }}</div>
              <button
                v-if="!isRead(n)"
                type="button"
                @click="markRead(n)"
                style="border:none;background:none;cursor:pointer;font-size:11px;color:var(--sa-brand);font-weight:600;padding:4px 0 0;font-family:inherit;"
              >
                Marcar como lida
              </button>
            </div>

            <button
              type="button"
              @click="dismiss(n.id)"
              style="border:none;background:none;cursor:pointer;color:var(--sa-muted);padding:0;display:flex;align-items:center;justify-content:center;flex-shrink:0;"
            >
              <SvgIcon name="close" :size="14" />
            </button>
          </div>
        </div>
      </template>

    </div>
  </AppShell>
</template>
