import type { FormField } from '@/types/forms'
import type { ComponentSnapshotEntry, SubmissionAnswer } from '@/types/submissions'

// Expansão do laudo por componente (DR-0002 T9). Campo geral → uma linha; campo escopado → uma
// linha por componente, com o rótulo congelado do `components_snapshot` (imune a renomeação do
// ativo). Evidência é por campo (limitação T8): só a primeira instância do campo a exibe.

export interface ReportRow {
  field: FormField
  answer: SubmissionAnswer | undefined
  value: SubmissionAnswer['value']
  componentLabel: string | null
  key: string
  showEvidence: boolean
}

export function componentLabel(
  snapshot: Record<string, ComponentSnapshotEntry> | null | undefined,
  assetId: string | null | undefined,
): string | null {
  if (!assetId) return null
  return snapshot?.[assetId]?.label ?? assetId
}

export function buildReportRows(
  fields: FormField[],
  answers: SubmissionAnswer[],
  snapshot: Record<string, ComponentSnapshotEntry> | null | undefined,
): ReportRow[] {
  const out: ReportRow[] = []
  const seen = new Set<string>()
  for (const field of fields) {
    const matches = answers.filter((a) => a.field_key === field.key)
    const scoped = matches.filter((a) => a.asset_id)
    if (scoped.length) {
      const sorted = [...scoped].sort((a, b) =>
        (componentLabel(snapshot, a.asset_id) ?? '').localeCompare(
          componentLabel(snapshot, b.asset_id) ?? '',
        ),
      )
      for (const a of sorted) {
        const first = !seen.has(field.key)
        seen.add(field.key)
        out.push({
          field,
          answer: a,
          value: a.value,
          componentLabel: componentLabel(snapshot, a.asset_id),
          key: `${field.key}@${a.asset_id}`,
          showEvidence: first,
        })
      }
    } else {
      const answer = matches[0]
      out.push({
        field,
        answer,
        value: answer?.value ?? null,
        componentLabel: null,
        key: field.key,
        showEvidence: true,
      })
    }
  }
  return out
}
