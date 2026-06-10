export interface AssetType {
  id: string
  name: string
  description: string | null
  // Aceito livre na Fase 1 (M1): nao ha validacao de conteudo.
  attributes_schema: Record<string, unknown> | null
  is_active: boolean
}

export interface AssetTypeCreatePayload {
  name: string
  description?: string | null
  attributes_schema?: Record<string, unknown> | null
}

export interface AssetTypeUpdatePayload {
  name?: string
  description?: string | null
  attributes_schema?: Record<string, unknown> | null
  is_active?: boolean
}
