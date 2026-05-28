import { test as base, type Page } from '@playwright/test'

export const API = '**/api/v1'

export const MOCK_USER = { id: 'u1', name: 'Alice Tester', email: 'alice@test.com' }
export const MOCK_COMPANY = { id: 'c1', name: 'Acme Corp', slug: 'acme', role: 'OWNER', plan: 'starter' }
export const MOCK_CONTEXT = {
  user: MOCK_USER,
  active_company: MOCK_COMPANY,
  membership: { id: 'm1', role: 'OWNER', company_id: 'c1', user_id: 'u1' },
}
export const MOCK_STATS = {
  total_submissions: 42,
  completed: 35,
  in_progress: 7,
  avg_score: 87.5,
  recent: [],
}

export function envelope(data: unknown) {
  return { data, meta: {} }
}

export function paginated(data: unknown[]) {
  return {
    data,
    meta: { page: 1, page_size: 20, total: (data as unknown[]).length, total_pages: 1, has_next: false },
  }
}

/** Inject auth state into localStorage before the page loads. */
export async function setAuth(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('smart-audit.token', 'mock-jwt-token')
    localStorage.setItem('smart-audit.company-id', 'c1')
  })
}

/** Mock the core bootstrap endpoints needed by the router guard. */
export async function mockBootstrap(page: Page) {
  await page.route(`${API}/me/companies`, (r) => r.fulfill({ json: envelope([MOCK_COMPANY]) }))
  await page.route(`${API}/me/context`, (r) => r.fulfill({ json: envelope(MOCK_CONTEXT) }))
}

/** Authenticated test fixture: sets localStorage + mocks bootstrap before navigation. */
export const test = base.extend<{ authed: Page }>({
  authed: async ({ page }, use) => {
    await setAuth(page)
    await mockBootstrap(page)
    await use(page)
  },
})

export { expect } from '@playwright/test'
