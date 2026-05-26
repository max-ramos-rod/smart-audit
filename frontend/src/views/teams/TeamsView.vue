<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import AppShell from '@/components/layout/AppShell.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
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
    formError.value = extractProblemMessage(err, 'Nao foi possivel salvar a equipe.')
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
    memberError.value = extractProblemMessage(err, 'Nao foi possivel adicionar membro.')
  }
}

async function doRemoveMember(userId: string) {
  memberError.value = null
  try {
    await teamsStore.removeMember(teamsStore.selectedTeam!.id, userId)
  } catch (err: any) {
    memberError.value = extractProblemMessage(err, 'Nao foi possivel remover membro.')
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
</script>

<template>
  <AppShell>
    <section class="flex flex-wrap items-center justify-between gap-3 px-1">
      <div>
        <p class="eyebrow">Administração</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-sa-text">Equipes</h2>
      </div>
      <BaseButton type="button" @click="resetToCreate">Nova equipe</BaseButton>
    </section>

    <p v-if="teamsStore.error" class="text-sm font-medium text-sa-danger">{{ teamsStore.error }}</p>

    <section class="grid gap-4 xl:grid-cols-[minmax(320px,400px)_minmax(0,1fr)]">
      <!-- Side panel -->
      <article class="surface-panel p-5 sm:p-6">
        <div class="flex items-center justify-between gap-3">
          <div>
            <p class="eyebrow">Operação</p>
            <h3 class="mt-2 text-xl font-semibold text-sa-text">{{ title }}</h3>
          </div>
          <span class="status-chip">
            {{ mode === 'edit' ? 'Edição' : mode === 'members' ? 'Membros' : 'Criação' }}
          </span>
        </div>

        <!-- Create / Edit form -->
        <form v-if="mode !== 'members'" class="mt-5 grid gap-4" @submit.prevent="submitForm">
          <label class="grid gap-2">
            <span>Nome da equipe</span>
            <input v-model="form.name" type="text" minlength="1" maxlength="150" required />
          </label>

          <p v-if="formError" class="text-sm font-medium text-sa-danger">{{ formError }}</p>

          <div class="flex flex-col gap-3">
            <BaseButton type="submit" :full-width="true" :disabled="teamsStore.isSaving">
              {{ submitLabel }}
            </BaseButton>
            <BaseButton
              v-if="mode === 'edit'"
              type="button"
              variant="ghost"
              :full-width="true"
              @click="resetToCreate"
            >
              Cancelar edição
            </BaseButton>
          </div>
        </form>

        <!-- Members panel -->
        <div v-else class="mt-5 grid gap-4">
          <div v-if="teamsStore.selectedTeam">
            <p class="text-sm font-medium text-sa-text">
              {{ teamsStore.selectedTeam.name }}
            </p>
            <p class="mt-1 text-sm text-sa-muted">
              {{ teamsStore.selectedTeam.members.length }} membro(s)
            </p>
          </div>

          <form class="grid gap-3" @submit.prevent="submitAddMember">
            <label class="grid gap-2">
              <span>Adicionar membro</span>
              <select v-model="memberUserId" required>
                <option value="" disabled>Selecione um usuário</option>
                <option v-for="u in availableUsers" :key="u.id" :value="u.id">
                  {{ u.name }} ({{ u.role }})
                </option>
              </select>
            </label>
            <BaseButton
              type="submit"
              :full-width="true"
              :disabled="!memberUserId || teamsStore.isSaving"
            >
              {{ teamsStore.isSaving ? 'Adicionando...' : 'Adicionar' }}
            </BaseButton>
          </form>

          <p v-if="memberError" class="text-sm font-medium text-sa-danger">{{ memberError }}</p>

          <ul v-if="teamsStore.selectedTeam?.members.length" class="grid gap-2">
            <li
              v-for="member in teamsStore.selectedTeam.members"
              :key="member.user_id"
              class="flex items-center justify-between gap-3 rounded-2xl border border-[color:var(--sa-line)] px-4 py-3"
            >
              <div>
                <p class="text-sm font-medium text-sa-text">{{ member.name }}</p>
                <p class="text-xs text-sa-muted">{{ member.email }}</p>
              </div>
              <button
                class="inline-action"
                type="button"
                :disabled="teamsStore.isSaving"
                @click="doRemoveMember(member.user_id)"
              >
                Remover
              </button>
            </li>
          </ul>
          <p v-else class="text-sm text-sa-muted">Nenhum membro nesta equipe.</p>

          <BaseButton type="button" variant="ghost" :full-width="true" @click="resetToCreate">
            Voltar
          </BaseButton>
        </div>
      </article>

      <!-- List -->
      <section class="grid gap-4">
        <div class="grid gap-3 lg:hidden">
          <article v-for="team in teamsStore.items" :key="team.id" class="surface-panel p-5">
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="eyebrow">Equipe</p>
                <h3 class="mt-2 text-lg font-semibold text-sa-text">{{ team.name }}</h3>
              </div>
              <span class="status-chip">{{ team.member_count }} membro(s)</span>
            </div>
            <div class="mt-4 flex flex-col gap-2">
              <BaseButton type="button" variant="ghost" :full-width="true" @click="openMembers(team)">
                Gerenciar membros
              </BaseButton>
              <BaseButton type="button" variant="ghost" :full-width="true" @click="openEdit(team)">
                Editar
              </BaseButton>
              <BaseButton
                type="button"
                variant="danger"
                :full-width="true"
                @click="confirmDelete(team)"
              >
                Excluir
              </BaseButton>
            </div>
          </article>
        </div>

        <section class="surface-panel hidden overflow-auto p-2 lg:block">
          <table>
            <thead>
              <tr>
                <th>Nome</th>
                <th>Membros</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="team in teamsStore.items" :key="team.id">
                <td>{{ team.name }}</td>
                <td>{{ team.member_count }}</td>
                <td class="flex gap-2">
                  <button class="inline-action" type="button" @click="openMembers(team)">
                    Membros
                  </button>
                  <button class="inline-action" type="button" @click="openEdit(team)">
                    Editar
                  </button>
                  <button
                    class="inline-action text-red-600"
                    type="button"
                    @click="confirmDelete(team)"
                  >
                    Excluir
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </section>
      </section>
    </section>
  </AppShell>
</template>
