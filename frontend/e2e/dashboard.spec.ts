import { API, MOCK_STATS, envelope, paginated, test, expect } from './fixtures'

test.describe('Dashboard (Home)', () => {
  test.beforeEach(async ({ authed: page }) => {
    await page.route(`${API}/me/stats**`, (r) => r.fulfill({ json: envelope(MOCK_STATS) }))
    await page.route(`${API}/forms**`, (r) =>
      r.fulfill({
        json: paginated([
          { id: 'f1', name: 'Safety Check', current_version_number: 1, is_active: true, published_at: '2024-01-01T00:00:00Z' },
        ]),
      }),
    )
    await page.goto('/')
  })

  test('displays greeting with user name', async ({ authed: page }) => {
    await expect(page.getByText(/alice/i).first()).toBeVisible()
  })

  test('displays stat cards with real values', async ({ authed: page }) => {
    await expect(page.getByText('42', { exact: true })).toBeVisible()
    await expect(page.getByText('35', { exact: true })).toBeVisible()
    await expect(page.getByText('7', { exact: true })).toBeVisible()
    await expect(page.getByText(/87/).first()).toBeVisible()
  })

  test('displays active forms section', async ({ authed: page }) => {
    await expect(page.getByText('Safety Check')).toBeVisible()
  })

  test('shows recent submissions when present', async ({ authed: page }) => {
    const statsWithRecent = {
      ...MOCK_STATS,
      recent: [
        {
          id: 's1',
          form_name: 'Safety Check',
          status: 'completed',
          score: 95,
          started_at: '2024-01-10T10:00:00Z',
          finished_at: '2024-01-10T11:00:00Z',
        },
      ],
    }
    await page.route(`${API}/me/stats**`, (r) => r.fulfill({ json: envelope(statsWithRecent) }))
    await page.goto('/')
    await expect(page.getByText('Inspeções recentes')).toBeVisible()
    await expect(page.getByText('95%')).toBeVisible()
  })

  test('period filter buttons are visible and trigger API call', async ({ authed: page }) => {
    const btn30d = page.getByRole('button', { name: '30 dias' })
    await expect(btn30d).toBeVisible()
    const req = page.waitForRequest((r) => r.url().includes('period=30d'))
    await btn30d.click()
    await req
  })
})
