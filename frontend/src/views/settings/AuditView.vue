<script setup lang="ts">
import { onMounted, ref } from 'vue'

import AppShell from '@/components/layout/AppShell.vue'
import { fetchAuditLogs, type AuditLogItem } from '@/services/audit.service'
import type { PaginationMeta } from '@/types/api'

const items = ref<AuditLogItem[]>([])
const meta = ref<PaginationMeta | null>(null)
const isLoading = ref(false)
const error = ref<string | null>(null)
const actionFilter = ref('')

const ACTION_LABELS: Record<string, string> = {
  'membership.revoked':     'Acesso revogado',
  'membership.reactivated': 'Acesso reativado',
  'user.created':           'Usuário criado',
  'user.invited':           'Usuário convidado',
  'team.deactivated':       'Equipe desativada',
  'company.deactivated':    'Empresa desativada',
}

const ACTION_CLASSES: Record<string, string> = {
  'membership.revoked':     'status-chip--inactive',
  'membership.reactivated': '',
  'user.created':           '',
  'user.invited':           '',
  'team.deactivated':       'status-chip--inactive',
  'company.deactivated':    'status-chip--inactive',
}

function actionLabel(action: string) {
  return ACTION_LABELS[action] ?? action
}

function actionClass(action: string) {
  return ACTION_CLASSES[action] ?? ''
}

function metaSummary(item: AuditLogItem): string {
  if (!item.meta) return ''
  const m = item.meta as Record<string, string>
  if (m.user_name && m.role) return `${m.user_name} (${m.role})`
  if (m.user_name) return m.user_name
  if (m.team_name) return m.team_name
  return ''
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

async function load(page = 1) {
  isLoading.value = true
  error.value = null
  try {
    const res = await fetchAuditLogs(page, 30, actionFilter.value || undefined)
    items.value = res.data
    meta.value = res.meta
  } catch {
    error.value = 'Não foi possível carregar o log de auditoria.'
  } finally {
    isLoading.value = false
  }
}

onMounted(() => load())
</script>

<template>
  <AppShell>
    <div class="page">
      <div class="phdr">
        <div>
          <div class="eyebrow">Administração</div>
          <h1 class="page-h1">Log de auditoria</h1>
          <p class="page-desc">Rastreabilidade de ações administrativas críticas.</p>
        </div>
      </div>

      <!-- Filtro por ação -->
      <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px;">
        <select
          v-model="actionFilter"
          style="font-size: 13px; padding: 6px 10px; border: 1px solid var(--sa-line); border-radius: 6px; background: var(--sa-card-bg); color: var(--sa-text);"
          @change="load(1)"
        >
          <option value="">Todas as ações</option>
          <option value="membership.revoked">Acesso revogado</option>
          <option value="membership.reactivated">Acesso reativado</option>
          <option value="user.created">Usuário criado</option>
          <option value="user.invited">Usuário convidado</option>
          <option value="team.deactivated">Equipe desativada</option>
          <option value="company.deactivated">Empresa desativada</option>
        </select>
      </div>

      <p v-if="error" style="font-size:13px;font-weight:600;color:var(--sa-danger);margin-bottom:12px;">{{ error }}</p>

      <div class="card" style="overflow-x: auto;">
        <p v-if="isLoading" style="font-size:13px;color:var(--sa-muted);padding:16px;">Carregando...</p>

        <template v-else-if="items.length === 0">
          <p style="font-size:13px;color:var(--sa-muted);padding:16px;">Nenhum evento registrado ainda.</p>
        </template>

        <table v-else class="tbl">
          <thead>
            <tr>
              <th>Data / Hora</th>
              <th>Ação</th>
              <th>Alvo</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td class="tbl-muted" style="font-family:'DM Mono',monospace;font-size:12px;white-space:nowrap;">
                {{ formatDate(item.created_at) }}
              </td>
              <td>
                <span class="status-chip" :class="actionClass(item.action)">
                  {{ actionLabel(item.action) }}
                </span>
              </td>
              <td class="tbl-muted" style="font-size:12px;">{{ metaSummary(item) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Paginação -->
      <div v-if="meta && meta.total_pages > 1" style="display:flex;gap:8px;margin-top:12px;align-items:center;font-size:13px;">
        <button
          class="btn-secondary btn-sm"
          :disabled="meta.page <= 1"
          @click="load(meta!.page - 1)"
        >Anterior</button>
        <span style="color:var(--sa-muted);">{{ meta.page }} / {{ meta.total_pages }}</span>
        <button
          class="btn-secondary btn-sm"
          :disabled="!meta.has_next"
          @click="load(meta!.page + 1)"
        >Próxima</button>
      </div>
    </div>
  </AppShell>
</template>
