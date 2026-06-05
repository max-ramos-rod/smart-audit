import { API, envelope, paginated, test, expect } from './fixtures'

const MOCK_TEAMS = [
  { id: 't1', name: 'Alpha Team', member_count: 2 },
  { id: 't2', name: 'Beta Team', member_count: 0 },
]

const MOCK_TEAM_DETAIL = {
  id: 't1',
  name: 'Alpha Team',
  members: [
    { user_id: 'u2', name: 'Bob Inspector', email: 'bob@test.com', role: 'INSPECTOR' },
  ],
  created_at: '2024-01-01T00:00:00Z',
}

const MOCK_USERS = [
  { id: 'u2', name: 'Bob Inspector', email: 'bob@test.com', role: 'INSPECTOR', is_active: true },
]

test.describe('Teams', () => {
  test.beforeEach(async ({ authed: page }) => {
    await page.route(`${API}/teams**`, (r) => r.fulfill({ json: paginated(MOCK_TEAMS) }))
    await page.route(`${API}/users**`, (r) => r.fulfill({ json: paginated(MOCK_USERS) }))
    await page.goto('/app/teams')
  })

  test('displays teams list', async ({ authed: page }) => {
    await expect(page.getByText('Alpha Team').first()).toBeVisible()
    await expect(page.getByText('Beta Team').first()).toBeVisible()
  })

  test('shows member count', async ({ authed: page }) => {
    await expect(page.getByText(/2 membros/i).first()).toBeVisible()
  })

  test('shows stat cards', async ({ authed: page }) => {
    await expect(page.getByText('Total de equipes')).toBeVisible()
  })

  test('create form is visible', async ({ authed: page }) => {
    await expect(page.getByRole('button', { name: /criar equipe/i })).toBeVisible()
  })

  test('opens member panel on Membros click', async ({ authed: page }) => {
    await page.route(`${API}/teams/t1**`, (r) => r.fulfill({ json: envelope(MOCK_TEAM_DETAIL) }))
    await page.getByRole('button', { name: /membros/i }).first().click()
    await expect(page.getByText('Bob Inspector')).toBeVisible()
  })

  test('shows empty state when no teams', async ({ authed: page }) => {
    await page.route(`${API}/teams**`, (r) => r.fulfill({ json: paginated([]) }))
    await page.goto('/app/teams')
    await expect(page.getByText(/nenhuma equipe/i)).toBeVisible()
  })
})
