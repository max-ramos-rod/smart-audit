<!--
  AssetTree.vue
  ──────────────────────────────────────────────────────────────────────────
  Tree view recursivo para a hierarquia Ativo → Componentes.
  Lazy-load dos filhos ao expandir (chama fetchAsset individualmente).
  Hover sobre uma linha revela ações contextuais: + Inspeção / + Componente.

  USO (em ClientDetailView):
    <AssetTree
      :nodes="rootAssets"
      :type-names="typeNameMap"
      @start-inspection="onStartInspection"
      @add-child="onAddChild"
    />

  EVENTOS:
    startInspection(asset: Asset)  — usuário clicou "+ Inspeção" num nó
    addChild(parent: Asset)        — usuário clicou "+ Componente" num nó
-->
<script setup lang="ts">
import { reactive } from 'vue'

import { fetchAsset } from '@/services/assets.service'
import type { Asset } from '@/types/assets'

// Necessário para recursão: o template referencia <AssetTree> pelo nome do componente.
defineOptions({ name: 'AssetTree' })

const props = defineProps<{
  /** Lista de ativos a renderizar neste nível */
  nodes: Asset[]
  /** Map asset_type_id → nome legível */
  typeNames: Record<string, string>
  /** Nível de profundidade (0 = raiz); usado para indentação */
  depth?: number
}>()

const emit = defineEmits<{
  startInspection: [asset: Asset]
  addChild: [parent: Asset]
}>()

// ── Estado por nó ──────────────────────────────────────────────────────────

const expanded = reactive<Record<string, boolean>>({})
const children = reactive<Record<string, Asset[]>>({})
const loading = reactive<Record<string, boolean>>({})

async function toggleExpand(node: Asset) {
  if (expanded[node.id]) {
    expanded[node.id] = false
    return
  }
  // Lazy load: carrega filhos apenas na primeira expansão
  if (!(node.id in children)) {
    loading[node.id] = true
    try {
      const detail = await fetchAsset(node.id)
      children[node.id] = detail.components
    } catch {
      children[node.id] = []
    } finally {
      loading[node.id] = false
    }
  }
  expanded[node.id] = true
}
</script>

<template>
  <div class="ast" :class="{ 'ast--nested': (props.depth ?? 0) > 0 }">
    <div v-for="node in nodes" :key="node.id" class="ast-node">
      <!-- ── Linha do nó ── -->
      <div
        class="ast-row"
        :class="{
          'ast-row--root': !node.parent_asset_id,
          'ast-row--comp': !!node.parent_asset_id,
        }"
      >
        <!-- Botão expand/collapse -->
        <button
          type="button"
          class="ast-toggle"
          :aria-label="expanded[node.id] ? 'Recolher' : 'Expandir'"
          @click="toggleExpand(node)"
        >
          <span v-if="loading[node.id]" class="ast-spin">⟳</span>
          <span v-else-if="expanded[node.id]">▼</span>
          <span v-else>▶</span>
        </button>

        <!-- Ícone de tipo -->
        <span class="ast-icon" :class="node.parent_asset_id ? 'ast-icon--comp' : 'ast-icon--root'">
          {{ node.parent_asset_id ? '⚙' : '📦' }}
        </span>

        <!-- Nome + tipo -->
        <div class="ast-info">
          <span class="ast-name">{{ node.identifier }}</span>
          <span class="ast-type">{{ typeNames[node.asset_type_id] ?? '—' }}</span>
        </div>

        <!-- Ações (visíveis no hover) -->
        <div class="ast-actions" role="group" :aria-label="`Ações de ${node.identifier}`">
          <button
            type="button"
            class="ast-action ast-action--inspect"
            @click.stop="emit('startInspection', node)"
          >
            + Inspeção
          </button>
          <button
            type="button"
            class="ast-action ast-action--child"
            @click.stop="emit('addChild', node)"
          >
            + Comp.
          </button>
        </div>
      </div>

      <!-- ── Filhos (recursivo) ── -->
      <template v-if="expanded[node.id]">
        <!-- Filhos carregados e existentes -->
        <AssetTree
          v-if="children[node.id]?.length"
          :nodes="children[node.id]"
          :type-names="typeNames"
          :depth="(props.depth ?? 0) + 1"
          @start-inspection="emit('startInspection', $event)"
          @add-child="emit('addChild', $event)"
        />

        <!-- Sem filhos após carregar -->
        <div v-else-if="!loading[node.id]" class="ast-empty-children">
          Sem componentes.
          <button
            type="button"
            class="ast-action ast-action--child"
            style="display: inline-flex"
            @click="emit('addChild', node)"
          >
            Adicionar →
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
/* ── Container de nível ── */
.ast {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.ast--nested {
  margin-left: 22px;
  padding-left: 10px;
  border-left: 1px dashed var(--sa-border, #e5e7eb);
  margin-top: 2px;
}

/* ── Nó ── */
.ast-node {
  display: flex;
  flex-direction: column;
}

/* ── Linha ── */
.ast-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 7px;
  cursor: default;
  transition: background 0.12s;
  position: relative;
}

.ast-row:hover {
  background: var(--sa-surface, #f9fafb);
}

.ast-row--root {
  font-weight: 600;
}
.ast-row--comp {
  font-size: 13px;
}

/* ── Toggle ── */
.ast-toggle {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--sa-muted, #6b7280);
  font-size: 9px;
  border-radius: 3px;
  transition: background 0.1s;
  padding: 0;
}

.ast-toggle:hover {
  background: var(--sa-border, #e5e7eb);
}

.ast-spin {
  display: inline-block;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* ── Ícone ── */
.ast-icon {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
  flex-shrink: 0;
  font-size: 11px;
}

.ast-icon--root {
  background: #eff6ff;
}
.ast-icon--comp {
  background: #f0fdf4;
}

/* ── Info ── */
.ast-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.ast-name {
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ast-type {
  font-size: 11px;
  color: var(--sa-muted, #6b7280);
  flex-shrink: 0;
}

/* ── Ações (ocultas, visíveis no hover) ── */
.ast-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.12s;
  flex-shrink: 0;
}

.ast-row:hover .ast-actions {
  opacity: 1;
  pointer-events: auto;
}

.ast-action {
  display: inline-flex;
  align-items: center;
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  border: 1px solid;
  transition: background 0.12s;
  white-space: nowrap;
}

.ast-action--inspect {
  background: #eff6ff;
  color: #1d4ed8;
  border-color: #bfdbfe;
}
.ast-action--inspect:hover {
  background: #dbeafe;
}

.ast-action--child {
  background: #f0fdf4;
  color: #15803d;
  border-color: #bbf7d0;
}
.ast-action--child:hover {
  background: #dcfce7;
}

/* ── Estado vazio ── */
.ast-empty-children {
  margin-left: 46px;
  padding: 5px 8px;
  font-size: 11px;
  color: var(--sa-muted, #6b7280);
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
