/**
 * useEvidence.ts
 * ──────────────────────────────────────────────────────────────────────────
 * Gerencia evidências (attachments) por campo/instância:
 * upload, delete, estado de carregamento e bottom sheet de evidência.
 *
 * USO em SubmissionDetailView:
 *
 *   const {
 *     evidenceAttachments, evidenceUploading, evidenceErrors, evidenceLoaded,
 *     showEvidenceSheet, evidenceSheetKey, evidenceSheetLabel,
 *     totalEvidenceCount, evidenceCanAddMore,
 *     loadEvidenceAttachments,
 *     handleEvidenceUpload, handleEvidenceDelete,
 *     openEvidenceSheet, closeEvidenceSheet, uploadEvidenceFromSheet,
 *   } = useEvidence(submissionId, answerableInstances)
 */
import { computed, reactive, ref, type ComputedRef, type Ref } from 'vue'

import { extractProblemMessage } from '@/services/api/problem'
import { createAttachment, deleteAttachment, listAttachments } from '@/services/attachments.service'
import { uploadFile } from '@/services/uploads.service'
import { instanceKey } from '@/utils/inspectionInstances'
import type { AttachmentItem } from '@/types/attachments'
import type { FieldInstance } from '@/utils/inspectionInstances'

export function useEvidence(
  submissionId: Ref<string>,
  answerableInstances: ComputedRef<FieldInstance[]>,
) {
  // ── Estado ──────────────────────────────────────────────────────────────

  /** Evidências indexadas por instanceKey (campo × componente — DR-0017) */
  const evidenceAttachments = reactive<Record<string, AttachmentItem[]>>({})
  const evidenceUploading = reactive<Record<string, boolean>>({})
  const evidenceErrors = reactive<Record<string, string>>({})
  const evidenceLoaded = ref(false)

  // Bottom sheet de evidência
  const showEvidenceSheet = ref(false)
  const evidenceSheetKey = ref<string | null>(null)

  // ── Computed ─────────────────────────────────────────────────────────────

  const totalEvidenceCount = computed(() =>
    Object.values(evidenceAttachments).reduce((sum, arr) => sum + arr.length, 0),
  )

  const evidenceSheetLabel = computed(() => {
    if (!evidenceSheetKey.value) return ''
    const inst = answerableInstances.value.find((i) => i.key === evidenceSheetKey.value)
    if (!inst) return evidenceSheetKey.value
    return inst.componentLabel ? `${inst.field.label} · ${inst.componentLabel}` : inst.field.label
  })

  // ── Helpers ───────────────────────────────────────────────────────────────

  function evidenceMaxFiles(configJson: Record<string, unknown>): number {
    const v = configJson.max_files
    return typeof v === 'number' ? v : 20
  }

  function evidenceCanAddMore(key: string, configJson: Record<string, unknown>): boolean {
    return (evidenceAttachments[key]?.length ?? 0) < evidenceMaxFiles(configJson)
  }

  /** Resolve a instanceKey de um attachment (campo × componente). */
  function evidenceInstanceKey(att: AttachmentItem): string | null {
    if (!att.field_key) return null
    return instanceKey(att.field_key, att.asset_id ?? null)
  }

  // ── Carregamento inicial ──────────────────────────────────────────────────

  async function loadEvidenceAttachments() {
    try {
      const all = await listAttachments(submissionId.value)
      for (const att of all) {
        const key = evidenceInstanceKey(att)
        if (!key) continue
        if (!evidenceAttachments[key]) evidenceAttachments[key] = []
        evidenceAttachments[key].push(att)
      }
    } catch (err) {
      console.error('[useEvidence] loadEvidenceAttachments failed:', err)
    } finally {
      evidenceLoaded.value = true
    }
  }

  // ── Upload ────────────────────────────────────────────────────────────────

  async function handleEvidenceUpload(
    fieldKey: string,
    assetId: string | null,
    configJson: Record<string, unknown>,
    event: Event,
  ) {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return

    const key = instanceKey(fieldKey, assetId)

    if (!evidenceCanAddMore(key, configJson)) {
      evidenceErrors[key] = `Limite de ${evidenceMaxFiles(configJson)} evidências atingido.`
      input.value = ''
      return
    }

    evidenceUploading[key] = true
    delete evidenceErrors[key]

    try {
      const result = await uploadFile(file)
      const att = await createAttachment(submissionId.value, {
        field_key: fieldKey,
        ...(assetId ? { asset_id: assetId } : {}),
        file_url: result.url,
        mime_type: result.mime_type,
        file_size: result.file_size,
      })
      if (!evidenceAttachments[key]) evidenceAttachments[key] = []
      evidenceAttachments[key].push(att)
    } catch (err) {
      evidenceErrors[key] = extractProblemMessage(err, 'Erro ao enviar evidência.')
    } finally {
      evidenceUploading[key] = false
      input.value = ''
    }
  }

  async function handleEvidenceDelete(instKey: string, attachmentId: string) {
    try {
      await deleteAttachment(submissionId.value, attachmentId)
      if (evidenceAttachments[instKey]) {
        evidenceAttachments[instKey] = evidenceAttachments[instKey].filter(
          (a) => a.id !== attachmentId,
        )
      }
    } catch (err) {
      evidenceErrors[instKey] = extractProblemMessage(err, 'Erro ao remover evidência.')
    }
  }

  // ── Bottom sheet ──────────────────────────────────────────────────────────

  function openEvidenceSheet(fieldKey: string) {
    evidenceSheetKey.value = fieldKey
    showEvidenceSheet.value = true
  }

  function closeEvidenceSheet() {
    showEvidenceSheet.value = false
  }

  /** Upload disparado pelo bottom sheet de evidência (resolve inst por key). */
  function uploadEvidenceFromSheet(event: Event) {
    if (!evidenceSheetKey.value) return
    const inst = answerableInstances.value.find((i) => i.key === evidenceSheetKey.value)
    if (!inst) return
    void handleEvidenceUpload(inst.field.key, inst.asset_id, inst.field.config_json ?? {}, event)
  }

  return {
    evidenceAttachments,
    evidenceUploading,
    evidenceErrors,
    evidenceLoaded,
    showEvidenceSheet,
    evidenceSheetKey,
    evidenceSheetLabel,
    totalEvidenceCount,
    evidenceMaxFiles,
    evidenceCanAddMore,
    loadEvidenceAttachments,
    handleEvidenceUpload,
    handleEvidenceDelete,
    openEvidenceSheet,
    closeEvidenceSheet,
    uploadEvidenceFromSheet,
  }
}
