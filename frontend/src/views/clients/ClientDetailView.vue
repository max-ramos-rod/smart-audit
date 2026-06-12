<!--
  ClientDetailView.vue  —  NOVA VIEW
  ──────────────────────────────────────────────────────────────────────────
  Hub contextual de um cliente.
  Mostra: info do cliente, árvore de ativos + inspeções recentes.
  Permite iniciar inspeção contextual a partir de qualquer ativo na árvore.

  ROTA: /clients/:id

  LIMITAÇÃO CONHECIDA (PR-6): as inspeções recentes são filtradas client-side por
  asset_id porque GET /submissions ainda não aceita ?client_id=. Para clientes com
  muitos ativos a lista pode ficar incompleta. Substituir pelo filtro server-side
  assim que o endpoint estiver disponível.
-->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import InspectionComposer from '@/components/submissions/InspectionComposer.vue'
import AssetTree from '@/components/ui/AssetTree.vue'
import { extractProblemMessage } from '@/services/api/problem'
import { fetchAssetTypes } from '@/services/asset-types.service'
import { fetchAssets } from '@/services/assets.service'
import { fetchClient, updateClient } from '@/services/clients.service'
import { fetchSubmissions } from '@/services/submissions.service'
import { scoreClass } from '@/utils/score'
import type { Asset } from '@/types/assets'
import type { Client } from '@/types/clients'
import type { SubmissionListItem } from '@/types/submissions'

const route = useRoute()
const router = useRouter()

const clientId = computed(() => route.params.id as string)

// ── Estado ────────────────────────────────────────────────────────────────

const client = ref<Client | null>(null)
const rootAssets = ref<Asset[]>([])
const typeNameMap = ref<Record<string, string>>({})
const recentSubs = ref<SubmissionListItem[]>([])
const pageError = ref<string | null>(null)
const isLoading = ref(true)

// Edição inline do cliente
const isEditing = ref(false)
const editName = ref('')
const editError = ref<string | null>(null)
const isSaving = ref(false)

// Composer
const showComposer = ref(false)
const composerAssetId = ref<string | null>(null)
const composerAssetLabel = ref<string | null>(null)

// ── Carregamento inicial ───────────────────────────────────────────────────

onMounted(async () => {
  isLoading.value = true
  pageError.value = null
  try {
    const [clientData, assetsResp, typesResp, subsResp] = await Promise.all([
      fetchClient(clientId.value),
      // Ativos raiz do cliente (client_id = clientId, sem parent → filtrado abaixo)
      fetchAssets(1, 100, { client_id: clientId.value, status: 'active' }),
      fetchAssetTypes(1, 100, true),
      // Inspeções do cliente filtradas server-side (PR-6: GET /submissions?client_id=).
      fetchSubmissions(1, 8, undefined, undefined, undefined, undefined, clientId.value),
    ])

    client.value = clientData

    // Filtra apenas raízes (componentes herdam o cliente da raiz).
    rootAssets.value = assetsResp.data.filter((a) => !a.parent_asset_id)

    // Mapa type_id → nome
    typeNameMap.value = Object.fromEntries(typesResp.data.map((t) => [t.id, t.name]))

    // Inspeções recentes — já vêm filtradas pelo backend (apenas ativos deste cliente).
    recentSubs.value = subsResp.data
  } catch (err) {
    pageError.value = extractProblemMessage(err, 'Não foi possível carregar os dados do cliente.')
  } finally {
    isLoading.value = false
  }
})

// ── Edição do cliente ──────────────────────────────────────────────────────

function startEdit() {
  editName.value = client.value?.name ?? ''
  editError.value = null
  isEditing.value = true
}

function cancelEdit() {
  isEditing.value = false
  editError.value = null
}

async function saveEdit() {
  if (!editName.value.trim()) return
  editError.value = null
  isSaving.value = true
  try {
    client.value = await updateClient(clientId.value, { name: editName.value.trim() })
    isEditing.value = false
  } catch (err) {
    editError.value = extractProblemMessage(err, 'Não foi possível salvar o cliente.')
  } finally {
    isSaving.value = false
  }
}

// ── Composer ───────────────────────────────────────────────────────────────

/** Aberto pelo header "Nova Inspeção" (sem ativo pré-selecionado, cliente fixado) */
function openComposerForClient() {
  composerAssetId.value = null
  composerAssetLabel.value = null
  showComposer.value = true
}

/** Aberto pelo hover "+ Inspeção" na árvore de ativos */
function openComposerForAsset(asset: Asset) {
  composerAssetId.value = asset.id
  composerAssetLabel.value = asset.identifier
  showComposer.value = true
}

function closeComposer() {
  showComposer.value = false
  composerAssetId.value = null
  composerAssetLabel.value = null
}

async function onInspectionCreated(submissionId: string) {
  closeComposer()
  router.push({ name: 'submission-detail', params: { id: submissionId } })
}

/** "+ Componente" na árvore → navega para /assets pré-configurado */
function onAddChild(parent: Asset) {
  router.push({ name: 'assets', query: { kind: 'component', parent_id: parent.id } })
}

// ── Helpers ────────────────────────────────────────────────────────────────

function statusLabel(status: string) {
  const map: Record<string, string> = {
    in_progress: 'Em andamento',
    completed: 'Concluída',
    draft: 'Rascunho',
    cancelled: 'Cancelada',
  }
  return map[status] ?? status
}
</script>

<template>
  <AppShell>
    <div class="page">
      <!-- ── Cabeçalho ── -->
      <div class="phdr" style="flex-wrap: wrap; gap: 10px">
        <div style="display: flex; align-items: center; gap: 10px; min-width: 0">
          <RouterLink
            to="/clients"
            class="btn-secondary btn-sm"
            style="text-decoration: none; white-space: nowrap"
          >
            ← Clientes
          </RouterLink>
          <div v-if="!isEditing">
            <p class="eyebrow">Operacional</p>
            <h2 class="page-h1" style="font-size: 22px">
              {{ client?.name ?? '…' }}
            </h2>
          </div>
          <div v-else style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap">
            <input
              v-model="editName"
              type="text"
              minlength="2"
              maxlength="150"
              style="
                font-size: 16px;
                font-weight: 700;
                height: 36px;
                padding: 0 10px;
                border: 1.5px solid var(--sa-primary);
                border-radius: 7px;
                width: 220px;
              "
              @keyup.enter="saveEdit"
              @keyup.escape="cancelEdit"
            />
            <button type="button" class="btn-primary btn-sm" :disabled="isSaving" @click="saveEdit">
              {{ isSaving ? 'Salvando…' : 'Salvar' }}
            </button>
            <button type="button" class="btn-secondary btn-sm" @click="cancelEdit">Cancelar</button>
            <p v-if="editError" style="font-size: 12px; color: var(--sa-danger); width: 100%">
              {{ editError }}
            </p>
          </div>
        </div>

        <div style="display: flex; gap: 8px; align-items: center; margin-left: auto">
          <button v-if="!isEditing" type="button" class="btn-secondary btn-sm" @click="startEdit">
            Editar
          </button>
          <button type="button" class="btn-primary" @click="openComposerForClient">
            + Nova inspeção
          </button>
        </div>
      </div>

      <!-- ── Erro de carregamento ── -->
      <p v-if="pageError" style="font-size: 13px; color: var(--sa-danger); margin-bottom: 12px">
        {{ pageError }}
      </p>

      <!-- ── Loading ── -->
      <p v-if="isLoading" style="font-size: 13px; color: var(--sa-muted)">Carregando…</p>

      <template v-else-if="!pageError">
        <!-- ── Composer (aparece acima do grid quando aberto) ── -->
        <div v-if="showComposer" class="card card-p" style="margin-bottom: 16px">
          <InspectionComposer
            :preselected-asset-id="composerAssetId"
            :preselected-asset-label="composerAssetLabel"
            :preselected-client-id="composerAssetId ? undefined : clientId"
            @created="onInspectionCreated"
            @close="closeComposer"
          />
        </div>

        <!-- ── Grid principal ── -->
        <div class="cdv-grid">
          <!-- ── Coluna esquerda: Árvore de ativos ── -->
          <div class="card card-p">
            <div
              style="
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 12px;
                gap: 8px;
              "
            >
              <div>
                <p class="eyebrow">Estrutura</p>
                <h3 style="font-size: 15px; font-weight: 700; color: var(--sa-text)">Ativos</h3>
              </div>
              <RouterLink
                :to="{ name: 'assets' }"
                class="btn-secondary btn-sm"
                style="text-decoration: none"
              >
                + Ativo
              </RouterLink>
            </div>

            <div
              v-if="rootAssets.length === 0"
              style="font-size: 13px; color: var(--sa-muted); padding: 8px 0"
            >
              Este cliente não possui ativos cadastrados.
              <RouterLink :to="{ name: 'assets' }" style="color: var(--sa-primary)">
                Cadastrar ativo →
              </RouterLink>
            </div>

            <AssetTree
              v-else
              :nodes="rootAssets"
              :type-names="typeNameMap"
              @start-inspection="openComposerForAsset"
              @add-child="onAddChild"
            />
          </div>

          <!-- ── Coluna direita: Inspeções recentes ── -->
          <div class="card card-p">
            <div
              style="
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 12px;
              "
            >
              <div>
                <p class="eyebrow">Histórico</p>
                <h3 style="font-size: 15px; font-weight: 700; color: var(--sa-text)">
                  Inspeções recentes
                </h3>
              </div>
              <RouterLink
                :to="{ name: 'submissions' }"
                class="inline-action"
                style="text-decoration: none"
              >
                Ver todas →
              </RouterLink>
            </div>

            <p v-if="recentSubs.length === 0" style="font-size: 13px; color: var(--sa-muted)">
              Nenhuma inspeção encontrada para este cliente.
            </p>

            <div v-else class="lstack">
              <div
                v-for="sub in recentSubs"
                :key="sub.id"
                class="lrow"
                style="cursor: pointer"
                @click="router.push({ name: 'submission-detail', params: { id: sub.id } })"
              >
                <div class="lrow-main">
                  <div class="lrow-title">{{ sub.form_name }}</div>
                  <div v-if="sub.asset_identifier" class="lrow-sub">🏷 {{ sub.asset_identifier }}</div>
                </div>
                <div class="lrow-end">
                  <span
                    v-if="sub.score !== null"
                    class="score-val"
                    :class="scoreClass(sub.score ?? 0)"
                  >
                    {{ sub.score }}%
                  </span>
                  <span
                    class="status-chip"
                    :class="{
                      'status-chip--warn': sub.status === 'in_progress',
                      'status-chip--inactive': sub.status === 'cancelled',
                    }"
                  >
                    {{ statusLabel(sub.status) }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <!-- /cdv-grid -->
      </template>
    </div>
  </AppShell>
</template>

<style scoped>
.cdv-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  align-items: flex-start;
}

@media (max-width: 720px) {
  .cdv-grid {
    grid-template-columns: 1fr;
  }
}
</style>
