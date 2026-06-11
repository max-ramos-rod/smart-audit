import { describe, expect, it } from 'vitest'

import type { ChecklistField, ComponentInstance } from '@/types/submissions'
import type { FieldType, FormField } from '@/types/forms'
import { buildRenderRows, instanceKey } from '@/utils/inspectionInstances'

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

function component(asset_id: string, label: string): ComponentInstance {
  return { asset_id, label, type: 'Roda', path: `Caminhão > ${label}` }
}

describe('instanceKey', () => {
  it('returns the field key for a general field (no asset)', () => {
    expect(instanceKey('pressao', null)).toBe('pressao')
    expect(instanceKey('pressao', undefined)).toBe('pressao')
  })

  it('composes field key with asset id for a scoped instance', () => {
    expect(instanceKey('pressao', 'a1')).toBe('pressao@a1')
  })
})

describe('buildRenderRows', () => {
  it('legacy mode (no checklist): one general instance per answerable field, sections preserved', () => {
    const fields = [field('sec', 1, 'section'), field('item', 2), field('obs', 3, 'text')]
    const rows = buildRenderRows(fields, null)

    expect(rows.map((r) => r.kind)).toEqual(['section', 'instance', 'instance'])
    const instances = rows.flatMap((r) => (r.kind === 'instance' ? [r.instance] : []))
    expect(instances.map((i) => i.key)).toEqual(['item', 'obs'])
    expect(instances.every((i) => i.asset_id === null && i.componentLabel === null)).toBe(true)
  })

  it('general field in checklist (empty components) → a single general instance', () => {
    const fields = [field('item', 1)]
    const checklist: ChecklistField[] = [
      { field_key: 'item', field_type: 'boolean', component_type_id: null, components: [] },
    ]
    const rows = buildRenderRows(fields, checklist)
    expect(rows).toHaveLength(1)
    expect(rows[0]).toMatchObject({ kind: 'instance' })
    if (rows[0].kind === 'instance') {
      expect(rows[0].instance.key).toBe('item')
      expect(rows[0].instance.asset_id).toBeNull()
    }
  })

  it('scoped field expands into one instance per component (Roda DD/DE/TD/TE)', () => {
    const fields = [field('pressao', 1)]
    const comps = [
      component('a1', 'Roda DD'),
      component('a2', 'Roda DE'),
      component('a3', 'Roda TD'),
      component('a4', 'Roda TE'),
    ]
    const checklist: ChecklistField[] = [
      { field_key: 'pressao', field_type: 'boolean', component_type_id: 'ct1', components: comps },
    ]
    const rows = buildRenderRows(fields, checklist)
    const instances = rows.flatMap((r) => (r.kind === 'instance' ? [r.instance] : []))

    expect(instances).toHaveLength(4)
    expect(instances.map((i) => i.key)).toEqual([
      'pressao@a1',
      'pressao@a2',
      'pressao@a3',
      'pressao@a4',
    ])
    expect(instances.map((i) => i.asset_id)).toEqual(['a1', 'a2', 'a3', 'a4'])
    expect(instances.map((i) => i.componentLabel)).toEqual([
      'Roda DD',
      'Roda DE',
      'Roda TD',
      'Roda TE',
    ])
    // todas as instâncias compartilham o mesmo FormField (peso/config do campo)
    expect(instances.every((i) => i.field.key === 'pressao')).toBe(true)
  })

  it('scoped field omitted from checklist (Q2/Q3) → zero instances', () => {
    const fields = [field('item', 1), field('pressao', 2)]
    // checklist só traz o campo geral; "pressao" foi omitido (sem componentes/sem ativo)
    const checklist: ChecklistField[] = [
      { field_key: 'item', field_type: 'boolean', component_type_id: null, components: [] },
    ]
    const rows = buildRenderRows(fields, checklist)
    const keys = rows.flatMap((r) => (r.kind === 'instance' ? [r.instance.key] : []))
    expect(keys).toEqual(['item'])
  })

  it('preserves position order across sections and expanded instances', () => {
    const fields = [field('sec', 1, 'section'), field('pressao', 2), field('item', 3)]
    const checklist: ChecklistField[] = [
      {
        field_key: 'pressao',
        field_type: 'boolean',
        component_type_id: 'ct1',
        components: [component('a1', 'Roda DD'), component('a2', 'Roda DE')],
      },
      { field_key: 'item', field_type: 'boolean', component_type_id: null, components: [] },
    ]
    const rows = buildRenderRows(fields, checklist)
    expect(rows.map((r) => (r.kind === 'section' ? 'sec' : r.instance.key))).toEqual([
      'sec',
      'pressao@a1',
      'pressao@a2',
      'item',
    ])
  })
})
