import { http } from '@/services/api/http'
import type { FormListItem } from '@/types/forms'
import type { SubmissionListItem } from '@/types/submissions'

export interface SearchResult {
  forms: FormListItem[]
  submissions: SubmissionListItem[]
}

export async function fetchSearch(q: string): Promise<SearchResult> {
  const res = await http.get('/search', { params: { q } })
  return res.data.data
}
