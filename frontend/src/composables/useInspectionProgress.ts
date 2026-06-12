/**
 * useInspectionProgress.ts
 * ──────────────────────────────────────────────────────────────────────────
 * Computed derivados do estado de conformidade: contadores de progresso,
 * score ao vivo, anel de score, seções do formulário e dots de navegação.
 *
 * USO em SubmissionDetailView:
 *
 *   const {
 *     progressStats, liveScore, scoreRingStyle,
 *     allAnswered, formSections, nearbyDots,
 *   } = useInspectionProgress(answerableInstances, conformityStatus, fields, inspectionIndex)
 *
 * NOTA (auditoria): `liveScore` arredonda para inteiro — é apenas o indicador
 * ao vivo. O score persistido (ADR-0008) vem do backend com 2 casas decimais.
 */
import { computed, type ComputedRef, type Ref } from 'vue'

import { scoreColorVar } from '@/utils/score'
import type { FormField } from '@/types/forms'
import type { FieldInstance } from '@/utils/inspectionInstances'

export function useInspectionProgress(
  answerableInstances: ComputedRef<FieldInstance[]>,
  /** Deve ser o mesmo reactive retornado por useConformity */
  conformityStatus: Record<string, 'conforme' | 'nao_conforme'>,
  fields: ComputedRef<FormField[]>,
  inspectionIndex: Ref<number>,
) {
  // ── Contadores ────────────────────────────────────────────────────────────

  const progressStats = computed(() => {
    let conformes = 0
    let naoConformes = 0
    for (const inst of answerableInstances.value) {
      const s = conformityStatus[inst.key]
      if (s === 'conforme') conformes++
      else if (s === 'nao_conforme') naoConformes++
    }
    const total = answerableInstances.value.length
    const evaluated = conformes + naoConformes
    const pending = total - evaluated
    const percentage = total === 0 ? 0 : Math.round((evaluated / total) * 100)
    return { conformes, naoConformes, evaluated, pending, total, percentage }
  })

  // ── Score ao vivo ─────────────────────────────────────────────────────────
  // Replica a lógica do backend (calculate_score): média ponderada por campo.
  // Para campos com instâncias múltiplas (DR-0002), weight é o mesmo por instância (Q6).

  const liveScore = computed((): number | null => {
    let wConformes = 0
    let wTotal = 0
    for (const inst of answerableInstances.value) {
      const s = conformityStatus[inst.key]
      if (!s) continue
      const weight = (inst.field.config_json?.weight as number | undefined) ?? 1
      wTotal += weight
      if (s === 'conforme') wConformes += weight
    }
    return wTotal === 0 ? null : Math.round((wConformes / wTotal) * 100)
  })

  // ── Anel de score (conic-gradient) ────────────────────────────────────────

  const scoreRingStyle = computed(() => {
    if (liveScore.value === null) {
      return { background: 'conic-gradient(#e2e8f0 100%, #e2e8f0 0)' }
    }
    const pct = liveScore.value
    const color = scoreColorVar(pct)
    return {
      background: `conic-gradient(${color} ${pct}%, #e2e8f0 0)`,
      transition: 'background .5s',
    }
  })

  // ── Status derivados ──────────────────────────────────────────────────────

  const allAnswered = computed(
    () => progressStats.value.pending === 0 && progressStats.value.total > 0,
  )

  // ── Seções com % de conclusão ─────────────────────────────────────────────

  const formSections = computed(() =>
    fields.value
      .filter((f) => f.field_type === 'section')
      .map((section, idx, arr) => {
        const nextSectionPos = arr[idx + 1]?.position ?? Infinity
        const sectionItems = answerableInstances.value.filter(
          (i) => i.field.position > section.position && i.field.position < nextSectionPos,
        )
        const evaluated = sectionItems.filter((i) => conformityStatus[i.key]).length
        const pct =
          sectionItems.length === 0 ? 100 : Math.round((evaluated / sectionItems.length) * 100)
        return { key: section.key, label: section.label, pct }
      }),
  )

  // ── Dots de navegação (modo cartão) ───────────────────────────────────────

  const nearbyDots = computed(() => {
    const idx = inspectionIndex.value
    const all = answerableInstances.value
    const half = 4
    const start = Math.max(0, idx - half)
    const end = Math.min(all.length - 1, idx + half)
    return all.slice(start, end + 1).map((inst, i) => ({
      key: inst.key,
      status: conformityStatus[inst.key] ?? 'pending',
      isCurrent: start + i === idx,
    }))
  })

  return {
    progressStats,
    liveScore,
    scoreRingStyle,
    allAnswered,
    formSections,
    nearbyDots,
  }
}
