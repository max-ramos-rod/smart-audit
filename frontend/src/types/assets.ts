export type AssetStatus = 'active' | 'inactive' | 'retired'

export interface Asset {
  id: string
  asset_type_id: string
  identifier: string
  // NULL = raiz; preenchido = componente (M5: imutável após o create).
  parent_asset_id: string | null
  // Só em raiz (M6); derivado da raiz nos componentes.
  client_id: string | null
  attributes_json: Record<string, unknown>
  status: string
}

export interface AssetDetail extends Asset {
  components: Asset[] // filhos diretos
}

export interface AssetCreatePayload {
  asset_type_id: string
  identifier: string
  parent_asset_id?: string | null
  client_id?: string | null
  attributes_json?: Record<string, unknown> | null
}

// parent_asset_id é imutável (M5) — não faz parte do update.
export interface AssetUpdatePayload {
  identifier?: string
  client_id?: string | null
  attributes_json?: Record<string, unknown> | null
  status?: AssetStatus
}

export interface AssetListFilters {
  asset_type_id?: string
  client_id?: string
  parent_asset_id?: string
  status?: string
}
