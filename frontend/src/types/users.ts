export interface UserListItem {
  id: string
  name: string
  email: string
  is_active: boolean
  role: string
}

export interface UserDetail extends UserListItem {
  company_id: string
}

export interface UserCreatePayload {
  name: string
  email: string
  password: string
  role: string
  is_active: boolean
}

export interface UserUpdatePayload {
  name?: string
  password?: string
  role?: string
  is_active?: boolean
}

export interface UserRevokedItem {
  id: string
  name: string
  email: string
  role: string
  revoked_at: string
}
