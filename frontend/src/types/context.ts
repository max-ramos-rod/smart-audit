import type { AuthenticatedUser } from './auth'
import type { SubmissionListItem } from './submissions'

export interface UserCompany {
  id: string
  name: string
  slug: string
  plan: string
  role: string
  is_active: boolean
}

export interface MembershipContext {
  role: string
}

export interface UserContext {
  user: AuthenticatedUser
  active_company: UserCompany | null
  membership: MembershipContext | null
  available_companies: UserCompany[]
  requires_company_selection: boolean
}

export interface FormScoreStat {
  form_id: string
  form_name: string
  avg_score: number
  count: number
}

export interface ScoreTrendPoint {
  date: string
  avg_score: number
}

export interface CompanyStats {
  total_submissions: number
  completed: number
  in_progress: number
  avg_score: number | null
  recent: SubmissionListItem[]
  score_by_form: FormScoreStat[]
  score_trend: ScoreTrendPoint[]
}
