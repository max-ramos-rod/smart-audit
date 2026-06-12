/**
 * useConformity.ts
 * ──────────────────────────────────────────────────────────────────────────
 * Gerencia todo o estado de conformidade de uma inspeção:
 * status (conforme/nao_conforme), justificativa, bottom sheet de justificativa
 * e persistência debounced via saveConformity.
 *
 * USO em SubmissionDetailView:
 *
 *   const {
 *     conformityStatus, conformityJustification,
 *     showJustificationSheet, justificationFieldKey, justificationError,
 *     setConformity, setNaoConformeCard, confirmJustification,
 *     openJustificationSheet, closeJustificationSheet,
 *     buildConformityItems, triggerConformitySave,
 *   } = useConformity(submissionId, answerableInstances, inspectionNext)
 *
 * NOTA: a inicialização do estado (populateDraft) é feita pela própria view,
 * que muta `conformityStatus`/`conformityJustification` diretamente — por isso
 * este composable não expõe `populateConformity` (removido na auditoria de
 * integração: evitava um `require()` incompatível com ESM/Vite).
 */
import { reactive, ref, type ComputedRef, type Ref } from 'vue'

import { saveConformity } from '@/services/submissions.service'
import type { FieldInstance } from '@/utils/inspectionInstances'

export function useConformity(
  submissionId: Ref<string>,
  answerableInstances: ComputedRef<FieldInstance[]>,
  /** Chamado após confirmar justificativa (avança para o próximo campo) */
  onAdvanceInspection: () => void,
) {
  // ── Estado ──────────────────────────────────────────────────────────────

  const conformityStatus = reactive<Record<string, 'conforme' | 'nao_conforme'>>({})
  const conformityJustification = reactive<Record<string, string>>({})

  const showJustificationSheet = ref(false)
  const justificationFieldKey = ref<string | null>(null)
  const justificationError = ref<string | null>(null)

  // ── Persistência debounced ───────────────────────────────────────────────

  let saveTimer: ReturnType<typeof setTimeout> | null = null

  /** Itens de conformidade prontos para envio, incluindo asset_id para campos escopados (T8). */
  function buildConformityItems() {
    return answerableInstances.value
      .filter((inst) => conformityStatus[inst.key])
      .map((inst) => ({
        field_key: inst.field.key,
        status: conformityStatus[inst.key],
        justification: conformityJustification[inst.key] || null,
        ...(inst.asset_id ? { asset_id: inst.asset_id } : {}),
      }))
  }

  function triggerConformitySave() {
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = setTimeout(async () => {
      const items = buildConformityItems()
      if (items.length === 0) return
      try {
        await saveConformity(submissionId.value, { items })
      } catch {
        // Falha silenciosa — dado é resalvo no próximo disparo ou no handleFinish
      }
    }, 800)
  }

  // ── Ações ────────────────────────────────────────────────────────────────

  function setConformity(fieldKey: string, status: 'conforme' | 'nao_conforme') {
    conformityStatus[fieldKey] = status
    triggerConformitySave()
  }

  /** Marca não-conforme e abre o bottom sheet de justificativa (modo cartão). */
  function setNaoConformeCard(fieldKey: string) {
    setConformity(fieldKey, 'nao_conforme')
    justificationError.value = null
    justificationFieldKey.value = fieldKey
    showJustificationSheet.value = true
  }

  function openJustificationSheet(fieldKey: string) {
    justificationFieldKey.value = fieldKey
    showJustificationSheet.value = true
  }

  function closeJustificationSheet() {
    showJustificationSheet.value = false
  }

  /** Valida e fecha o sheet de justificativa; avança para o próximo campo. */
  function confirmJustification() {
    const key = justificationFieldKey.value
    if (!key) return
    const text = (conformityJustification[key] || '').trim()
    if (!text) {
      justificationError.value = 'Descreva o problema encontrado.'
      return
    }
    justificationError.value = null
    triggerConformitySave()
    showJustificationSheet.value = false
    setTimeout(() => onAdvanceInspection(), 250)
  }

  return {
    conformityStatus,
    conformityJustification,
    showJustificationSheet,
    justificationFieldKey,
    justificationError,
    setConformity,
    setNaoConformeCard,
    openJustificationSheet,
    closeJustificationSheet,
    confirmJustification,
    buildConformityItems,
    triggerConformitySave,
  }
}
