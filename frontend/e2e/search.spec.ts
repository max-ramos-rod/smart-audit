import { API, envelope, test, expect } from './fixtures'

const MOCK_RESULTS = {
  forms: [
    {
      id: 'f1',
      name: 'Safety Check',
      current_version_number: 1,
      status: 'published',
      created_at: '',
    },
  ],
  submissions: [
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

test.describe('Search', () => {
  test.beforeEach(async ({ authed: page }) => {
    await page.goto('/app/search')
  })

  test('shows search input', async ({ authed: page }) => {
    await expect(page.getByRole('textbox')).toBeVisible()
  })

  test('displays results after typing query', async ({ authed: page }) => {
    await page.route(`${API}/search**`, (r) => r.fulfill({ json: envelope(MOCK_RESULTS) }))
    await page.getByRole('textbox').fill('safety')
    await expect(page.getByText('Safety Check').first()).toBeVisible({ timeout: 2000 })
  })

  test('shows both form and submission results', async ({ authed: page }) => {
    await page.route(`${API}/search**`, (r) => r.fulfill({ json: envelope(MOCK_RESULTS) }))
    await page.getByRole('textbox').fill('safety')
    await expect(page.getByText('Safety Check').first()).toBeVisible({ timeout: 2000 })
    await expect(page.getByText(/95%/)).toBeVisible()
  })

  test('shows empty state when no results', async ({ authed: page }) => {
    await page.route(`${API}/search**`, (r) =>
      r.fulfill({ json: envelope({ forms: [], submissions: [] }) }),
    )
    await page.getByRole('textbox').fill('xyznotfound')
    await expect(page.getByText(/nenhum resultado/i)).toBeVisible({ timeout: 2000 })
  })

  test('navigates to form detail on form result click', async ({ authed: page }) => {
    await page.route(`${API}/search**`, (r) => r.fulfill({ json: envelope(MOCK_RESULTS) }))
    await page.route(`${API}/forms/f1**`, (r) =>
      r.fulfill({ json: envelope({ ...MOCK_RESULTS.forms[0], fields: [], versions: [] }) }),
    )
    await page.getByRole('textbox').fill('safety')
    await page.getByText('Safety Check').first().click()
    await expect(page).toHaveURL('/app/forms/f1')
  })
})
