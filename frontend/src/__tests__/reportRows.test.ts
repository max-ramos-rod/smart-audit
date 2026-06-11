import { describe, expect, it } from 'vitest'

import type { FieldType, FormField } from '@/types/forms'
import type { ComponentSnapshotEntry, SubmissionAnswer } from '@/types/submissions'
import { buildReportRows, componentLabel } from '@/utils/reportRows'

function field(key: string, position: number, field_type: FieldType = 'boolean'): FormField {
  return {
    id: `id-${key}`,
    key,
    label: `Label ${key}`,
    field_type,
    required: false,
    position,
    config_json: {},
    instruction: null,
  }
}

function answer(
  field_key: string,
  value: SubmissionAnswer['value'],
  asset_id: string | null = null,
): SubmissionAnswer {
  return { field_key, field_type: 'boolean', value, asset_id }
}

const snapshot: Record<string, ComponentSnapshotEntry> = {
  a2: { label: 'Roda DE', type: 'Roda', path: 'Caminhão > Roda DE' },
  a1: { label: 'Roda DD', type: 'Roda', path: 'Caminhão > Roda DD' },
}

describe('componentLabel', () => {
  it('returns null for a general answer (no asset)', () => {
    expect(componentLabel(snapshot, null)).toBeNull()
    expect(componentLabel(snapshot, undefined)).toBeNull()
  })

  it('reads the frozen label from the snapshot', () => {
    expect(componentLabel(snapshot, 'a1')).toBe('Roda DD')
  })

  it('falls back to the asset id when not in the snapshot', () => {
    expect(componentLabel(snapshot, 'missing')).toBe('missing')
    expect(componentLabel(null, 'a1')).toBe('a1')
  })
})

describe('buildReportRows', () => {
  it('general field → a single row (no component)', () => {
    const rows = buildReportRows([field('item', 1)], [answer('item', true)], null)
    expect(rows).toHaveLength(1)
    expect(rows[0]).toMatchObject({ key: 'item', componentLabel: null, showEvidence: true })
  })

  it('scoped field → one row per component, ordered by frozen label', () => {
    const answers = [answer('pressao', true, 'a2'), answer('pressao', false, 'a1')]
    const rows = buildReportRows([field('pressao', 1)], answers, snapshot)

    expect(rows.map((r) => r.key)).toEqual(['pressao@a1', 'pressao@a2'])
    expect(rows.map((r) => r.componentLabel)).toEqual(['Roda DD', 'Roda DE'])
    expect(rows.map((r) => r.value)).toEqual([false, true])
  })

  it('marks only the first instance of a scoped field to show evidence (limitação T8)', () => {
    const answers = [answer('pressao', true, 'a1'), answer('pressao', true, 'a2')]
    const rows = buildReportRows([field('pressao', 1)], answers, snapshot)
    expect(rows.map((r) => r.showEvidence)).toEqual([true, false])
  })

  it('field without answers → a single empty row', () => {
    const rows = buildReportRows([field('item', 1)], [], null)
    expect(rows).toHaveLength(1)
    expect(rows[0]).toMatchObject({ value: null, componentLabel: null })
  })
})
