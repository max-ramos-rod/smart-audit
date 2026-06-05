import { API, envelope, paginated, test, expect } from './fixtures'

const MOCK_FORM = {
  id: 'f1',
  name: 'Safety Check',
  current_version_number: 2,
  is_active: true,
  status: 'published',
  published_at: '2024-01-01T00:00:00Z',
}

const MOCK_FORM_DETAIL = {
  id: 'f1',
  company_id: 'c1',
  name: 'Safety Check',
  description: 'Checklist de segurança',
  is_active: true,
  current_version: {
    id: 'v2',
    version: 2,
    status: 'published',
    published_at: '2024-02-01T00:00:00Z',
    fields: [
      { id: 'ff1', key: 'item_ok', label: 'Item OK?', field_type: 'boolean', required: true, position: 1, config_json: {} },
    ],
  },
}

const MOCK_VERSIONS = [
  { id: 'v2', version: 2, status: 'published', published_at: '2024-02-01T00:00:00Z', fields_count: 1 },
  { id: 'v1', version: 1, status: 'archived', published_at: '2024-01-01T00:00:00Z', fields_count: 1 },
]

test.describe('Forms list', () => {
  test.beforeEach(async ({ authed: page }) => {
    await page.route(`${API}/forms**`, (r) => r.fulfill({ json: paginated([MOCK_FORM]) }))
    await page.goto('/app/forms')
  })

  test('displays form list', async ({ authed: page }) => {
    await expect(page.getByText('Safety Check')).toBeVisible()
    await expect(page.getByText(/v2/)).toBeVisible()
  })

  test('shows empty state when no forms', async ({ authed: page }) => {
    await page.route(`${API}/forms**`, (r) => r.fulfill({ json: paginated([]) }))
    await page.goto('/app/forms')
    await expect(page.getByText(/nenhum formulário/i)).toBeVisible()
  })

  test('navigates to form detail on click', async ({ authed: page }) => {
    await page.route(`${API}/submissions**`, (r) => r.fulfill({ json: paginated([]) }))
    await page.route(`${API}/forms/f1**`, (r) => r.fulfill({ json: envelope(MOCK_FORM_DETAIL) }))
    await page.getByText('Safety Check').click()
    await expect(page).toHaveURL('/app/forms/f1')
  })

  test('opens create form composer', async ({ authed: page }) => {
    await page.getByRole('button', { name: /novo formulário/i }).click()
    await expect(page.getByText(/nome do formulário/i)).toBeVisible()
  })
})

test.describe('Form detail', () => {
  test.beforeEach(async ({ authed: page }) => {
    await page.route(`${API}/submissions**`, (r) => r.fulfill({ json: paginated([]) }))
    await page.route(`${API}/forms/f1**`, (r) => r.fulfill({ json: envelope(MOCK_FORM_DETAIL) }))
    await page.goto('/app/forms/f1')
  })

  test('displays form name and fields', async ({ authed: page }) => {
    await expect(page.getByText('Safety Check')).toBeVisible()
    await expect(page.getByText('Item OK?')).toBeVisible()
  })

  test('shows current version number', async ({ authed: page }) => {
    await expect(page.getByText(/versão 2|v2/i).first()).toBeVisible()
  })
})

test.describe('Form versions', () => {
  test('lists all versions with status', async ({ authed: page }) => {
    await page.route(`${API}/forms/f1**`, (r) => r.fulfill({ json: envelope(MOCK_FORM_DETAIL) }))
    await page.route(`${API}/forms/f1/versions**`, (r) =>
      r.fulfill({ json: envelope(MOCK_VERSIONS) }),
    )
    await page.goto('/app/forms/f1/versions')
    await expect(page.getByText(/v2|versão 2/i).first()).toBeVisible()
    await expect(page.getByText('Atual')).toBeVisible()
  })
})
