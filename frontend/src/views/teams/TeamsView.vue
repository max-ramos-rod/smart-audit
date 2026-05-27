<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import AppShell from '@/components/layout/AppShell.vue'
import { extractProblemMessage } from '@/services/api/problem'
import { useTeamsStore } from '@/stores/teams/teams.store'
import { useUsersStore } from '@/stores/users/users.store'
import type { TeamListItem } from '@/types/teams'

const teamsStore = useTeamsStore()
const usersStore = useUsersStore()

const mode = ref<'create' | 'edit' | 'members'>('create')
const formError = ref<string | null>(null)
const memberError = ref<string | null>(null)
const memberUserId = ref('')

const form = reactive({
  id: '',
  name: '',
})

const title = computed(() => {
  if (mode.value === 'edit') return 'Editar equipe'
  if (mode.value === 'members') return 'Membros da equipe'
  return 'Nova equipe'
})

const totalMembers  = computed(() => teamsStore.items.reduce((a, t) => a + t.member_count, 0))
const largestTeam   = computed(() => teamsStore.items.length ? Math.max(...teamsStore.items.map(t => t.member_count)) : 0)

onMounted(async () => {
  await teamsStore.load()
  await usersStore.load(1, 100)
})

function resetToCreate() {
  form.id = ''
  form.name = ''
  mode.value = 'create'
  formError.value = null
  memberError.value = null
  memberUserId.value = ''
  teamsStore.clearSelectedTeam()
}

async function openEdit(team: TeamListItem) {
  const detail = await teamsStore.loadTeam(team.id)
  form.id = detail.id
  form.name = detail.name
  mode.value = 'edit'
  formError.value = null
  memberError.value = null
}

async function openMembers(team: TeamListItem) {
  await teamsStore.loadTeam(team.id)
  mode.value = 'members'
  memberError.value = null
  memberUserId.value = ''
}

async function submitForm() {
  formError.value = null
  try {
    if (mode.value === 'edit') {
      await teamsStore.update(form.id, { name: form.name })
    } else {
      await teamsStore.create({ name: form.name })
    }
    resetToCreate()
  } catch (err: any) {
    formError.value = extractProblemMessage(err, 'Não foi possível salvar a equipe.')
  }
}

async function confirmDelete(team: TeamListItem) {
  if (!confirm(`Excluir a equipe "${team.name}"? Esta ação não pode ser desfeita.`)) return
  try {
    await teamsStore.remove(team.id)
    resetToCreate()
  } catch {
    // error already set in store
  }
}

async function submitAddMember() {
  if (!memberUserId.value) return
  memberError.value = null
  try {
    await teamsStore.addMember(teamsStore.selectedTeam!.id, memberUserId.value)
    memberUserId.value = ''
  } catch (err: any) {
    memberError.value = extractProblemMessage(err, 'Não foi possível adicionar membro.')
  }
}

async function doRemoveMember(userId: string) {
  memberError.value = null
  try {
    await teamsStore.removeMember(teamsStore.selectedTeam!.id, userId)
  } catch (err: any) {
    memberError.value = extractProblemMessage(err, 'Não foi possível remover membro.')
  }
}

const availableUsers = computed(() => {
  if (!teamsStore.selectedTeam) return usersStore.items
  const memberIds = new Set(teamsStore.selectedTeam.members.map((m) => m.user_id))
  return usersStore.items.filter((u) => !memberIds.has(u.id))
})

const submitLabel = computed(() => {
  if (teamsStore.isSaving) return mode.value === 'edit' ? 'Salvando...' : 'Criando...'
  return mode.value === 'edit' ? 'Salvar alterações' : 'Criar equipe'
})

function memberInitials(name: string) {
  return name.split(' ').map(n => n[0]).slice(0, 2).join('')
}
</script>

<template>
  <AppShell>
    <div class="page">

      <div class="phdr">
        <div>
          <p class="eyebrow">Administração</p>
          <h2 class="page-h1">Equipes</h2>
          <p class="page-desc">Organize usuários em equipes operacionais para atribuição de inspeções.</p>
        </div>
        <button type="button" class="btn-secondary btn-sm" @click="resetToCreate">+ Nova equipe</button>
      </div>

      <!-- Stats -->
      <div class="stats-grid" style="margin-bottom:20px;">
        <div class="scard">
          <div class="sc-label">Total de equipes</div>
          <div class="sc-value">{{ teamsStore.items.length }}</div>
        </div>
        <div class="scard">
          <div class="sc-label">Total de membros</div>
          <div class="sc-value">{{ totalMembers }}</div>
        </div>
        <div class="scard sc-accent">
          <div class="sc-label">Maior equipe</div>
          <div class="sc-value">{{ largestTeam }}</div>
          <div class="sc-desc">membros</div>
        </div>
        <div class="scard">
          <div class="sc-label">Usuários disponíveis</div>
          <div class="sc-value">{{ usersStore.items.length }}</div>
        </div>
      </div>

      <p v-if="teamsStore.error" style="margin-bottom:12px;font-size:13px;font-weight:600;color:var(--sa-danger);">
        {{ teamsStore.error }}
      </p>

      <div class="users-layout">

        <!-- Side panel -->
        <div class="card card-p" style="align-self:flex-start;position:sticky;top:20px;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
            <div>
              <div class="eyebrow">{{ mode === 'members' && teamsStore.selectedTeam ? teamsStore.selectedTeam.name : 'Operação' }}</div>
              <div style="font-size:16px;font-weight:700;color:var(--sa-text);margin-top:3px;">{{ title }}</div>
            </div>
            <span
              class="status-chip"
              :class="{
                'status-chip--warn': mode === 'edit',
                'status-chip--neu': mode === 'members',
              }"
            >
              {{ mode === 'edit' ? 'Edição' : mode === 'members' ? 'Membros' : 'Criação' }}
            </span>
          </div>

          <!-- Create / Edit form -->
          <form v-if="mode !== 'members'" style="display:grid;gap:12px;" @submit.prevent="submitForm">
            <label style="display:grid;gap:6px;">
              <span style="font-size:12px;font-weight:600;color:var(--sa-muted);">Nome da equipe</span>
              <input v-model="form.name" type="text" minlength="1" maxlength="150" required placeholder="Ex: Auditoria Norte" />
            </label>

            <p v-if="formError" style="font-size:13px;font-weight:600;color:var(--sa-danger);">{{ formError }}</p>

            <div style="display:grid;gap:8px;">
              <button type="submit" class="btn-primary btn-full" :disabled="teamsStore.isSaving">
                {{ submitLabel }}
              </button>
              <button
                v-if="mode === 'edit'"
                type="button"
                class="btn-secondary btn-full"
                @click="resetToCreate"
              >
                Cancelar edição
              </button>
            </div>
          </form>

          <!-- Members panel -->
          <div v-else style="display:grid;gap:14px;">
            <div style="font-size:13px;color:var(--sa-muted);">
              {{ teamsStore.selectedTeam?.members.length ?? 0 }} membro{{ (teamsStore.selectedTeam?.members.length ?? 0) !== 1 ? 's' : '' }} nesta equipe
            </div>

            <form v-if="availableUsers.length > 0" style="display:grid;gap:10px;" @submit.prevent="submitAddMember">
              <label style="display:grid;gap:6px;">
                <span style="font-size:12px;font-weight:600;color:var(--sa-muted);">Adicionar membro</span>
                <select v-model="memberUserId" required>
                  <option value="" disabled>Selecione um usuário</option>
                  <option v-for="u in availableUsers" :key="u.id" :value="u.id">
                    {{ u.name }} ({{ u.role }})
                  </option>
                </select>
              </label>
              <button
                type="submit"
                class="btn-primary btn-full"
                :disabled="!memberUserId || teamsStore.isSaving"
              >
                {{ teamsStore.isSaving ? 'Adicionando...' : 'Adicionar' }}
              </button>
            </form>
            <div v-else class="info-box">Todos os usuários já são membros desta equipe.</div>

            <p v-if="memberError" style="font-size:13px;font-weight:600;color:var(--sa-danger);">{{ memberError }}</p>

            <!-- Members list -->
            <div v-if="teamsStore.selectedTeam?.members.length" style="display:flex;flex-direction:column;gap:8px;">
              <div
                v-for="member in teamsStore.selectedTeam.members"
                :key="member.user_id"
                style="display:flex;align-items:center;gap:12px;padding:10px 12px;background:#f8fafc;border:1px solid var(--sa-line);border-radius:8px;"
              >
                <div style="width:28px;height:28px;border-radius:50%;background:var(--sa-brand-soft);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;color:var(--sa-brand);flex-shrink:0;">
                  {{ memberInitials(member.name) }}
                </div>
                <div style="flex:1;min-width:0;">
                  <div style="font-size:13px;font-weight:600;color:var(--sa-text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ member.name }}</div>
                  <div style="font-size:11px;color:var(--sa-muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ member.email }}</div>
                </div>
                <button
                  type="button"
                  style="border:none;background:none;cursor:pointer;font-size:11px;font-weight:600;color:var(--sa-danger);font-family:inherit;flex-shrink:0;padding:0;"
                  :disabled="teamsStore.isSaving"
                  @click="doRemoveMember(member.user_id)"
                >
                  Remover
                </button>
              </div>
            </div>
            <p v-else style="font-size:13px;color:var(--sa-muted);">Nenhum membro nesta equipe.</p>

            <button type="button" class="btn-secondary btn-full" @click="resetToCreate">← Voltar</button>
          </div>
        </div>

        <!-- Teams list -->
        <div>

          <!-- Empty state -->
          <div v-if="!teamsStore.isLoading && !teamsStore.items.length" class="empty">
            <div class="empty-h">Nenhuma equipe cadastrada</div>
            <p class="empty-p">Use o painel ao lado para criar sua primeira equipe.</p>
          </div>

          <template v-else>
            <!-- Mobile cards -->
            <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:8px;" class="lg:hidden">
              <div
                v-for="team in teamsStore.items"
                :key="team.id"
                class="card card-p"
              >
                <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:12px;">
                  <div>
                    <div class="eyebrow">Equipe</div>
                    <div style="font-size:15px;font-weight:700;color:var(--sa-text);margin-top:4px;">{{ team.name }}</div>
                  </div>
                  <span class="status-chip">{{ team.member_count }} membro{{ team.member_count !== 1 ? 's' : '' }}</span>
                </div>
                <div style="display:flex;flex-direction:column;gap:6px;">
                  <button type="button" class="btn-secondary btn-full btn-sm" @click="openMembers(team)">Gerenciar membros</button>
                  <button type="button" class="btn-secondary btn-full btn-sm" @click="openEdit(team)">Editar</button>
                  <button
                    type="button"
                    class="btn-secondary btn-full btn-sm"
                    style="color:var(--sa-danger);border-color:var(--sa-err-bg);"
                    @click="confirmDelete(team)"
                  >
                    Excluir
                  </button>
                </div>
              </div>
            </div>

            <!-- Desktop table -->
            <div class="card hidden lg:block" style="overflow-x:auto;">
              <table class="tbl">
                <thead>
                  <tr>
                    <th>Nome da equipe</th>
                    <th>Membros</th>
                    <th>Ações</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="team in teamsStore.items" :key="team.id">
                    <td class="tbl-name">{{ team.name }}</td>
                    <td>
                      <span class="status-chip">{{ team.member_count }} membro{{ team.member_count !== 1 ? 's' : '' }}</span>
                    </td>
                    <td>
                      <div style="display:flex;gap:6px;flex-wrap:wrap;">
                        <button type="button" class="btn-secondary btn-sm" @click="openMembers(team)">Membros</button>
                        <button type="button" class="btn-secondary btn-sm" @click="openEdit(team)">Editar</button>
                        <button
                          type="button"
                          class="btn-secondary btn-sm"
                          style="color:var(--sa-danger);border-color:var(--sa-err-bg);"
                          @click="confirmDelete(team)"
                        >
                          Excluir
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>

        </div>
      </div>

    </div>
  </AppShell>
</template>
