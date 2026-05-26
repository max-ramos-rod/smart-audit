export interface TeamMember {
  user_id: string
  name: string
  email: string
}

export interface TeamListItem {
  id: string
  company_id: string
  name: string
  member_count: number
}

export interface Team {
  id: string
  company_id: string
  name: string
  members: TeamMember[]
}

export interface TeamCreatePayload {
  name: string
}

export interface TeamUpdatePayload {
  name: string
}
