import type { FormField } from '@/types/forms'
import type { ChecklistField } from '@/types/submissions'

// Expansão da inspeção por componente (DR-0002 T8).
//
// Uma "instância respondível" = (campo × componente). Campo geral → uma instância com
// asset_id null e chave = field.key. Campo escopado → uma instância por componente, chave =
// `field.key@asset_id`. A fonte de verdade é o `checklist` expandido pelo backend (T3); quando
// ausente (respostas legadas/sem ativo) cai para uma instância geral por campo.

export interface FieldInstance {
  field: FormField
  asset_id: string | null
  componentLabel: string | null
  componentPath: string | null
  key: string
}

export type RenderRow =
  | { kind: 'section'; field: FormField }
  | { kind: 'instance'; field: FormField; instance: FieldInstance }

export function instanceKey(fieldKey: string, assetId: string | null | undefined): string {
  return assetId ? `${fieldKey}@${assetId}` : fieldKey
}

function generalInstance(field: FormField): FieldInstance {
  return { field, asset_id: null, componentLabel: null, componentPath: null, key: field.key }
}

/**
 * Constrói as linhas renderizáveis em ordem de posição: seções (divisores) + instâncias
 * respondíveis. `checklist` ausente (`null`/`undefined`) = modo legado (uma instância geral por
 * campo). Campo escopado omitido do checklist (Q2/Q3) gera zero instâncias — o aviso vem em
 * `submission.warnings`.
 */
export function buildRenderRows(
  fields: FormField[],
  checklist: ChecklistField[] | null | undefined,
): RenderRow[] {
  const hasChecklist = checklist != null
  const byKey = new Map<string, ChecklistField>()
  for (const cf of checklist ?? []) byKey.set(cf.field_key, cf)

  const instancesForField = (field: FormField): FieldInstance[] => {
    if (!hasChecklist) return [generalInstance(field)]
    const cf = byKey.get(field.key)
    if (!cf) return []
    if (!cf.components.length) return [generalInstance(field)]
    return cf.components.map((c) => ({
      field,
      asset_id: c.asset_id,
      componentLabel: c.label,
      componentPath: c.path,
      key: instanceKey(field.key, c.asset_id),
    }))
  }

  const rows: RenderRow[] = []
  for (const field of fields) {
    if (field.field_type === 'section') {
      rows.push({ kind: 'section', field })
      continue
    }
    for (const inst of instancesForField(field)) {
      rows.push({ kind: 'instance', field, instance: inst })
    }
  }
  return rows
}
