export interface Client {
  id: string
  name: string
  is_active: boolean
}

export interface ClientCreatePayload {
  name: string
}

export interface ClientUpdatePayload {
  name?: string
  is_active?: boolean
}
