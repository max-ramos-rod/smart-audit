import { API, envelope, paginated, test, expect } from './fixtures'

const MOCK_LIST_ITEM = {
  id: 's1',
  form_id: 'f1',
  form_name: 'Safety Check',
  status: 'in_progress',
  score: null,
  started_at: '2024-01-10T10:00:00Z',
  finished_at: null,
}

const MOCK_DETAIL = {
  id: 's1',
  form_id: 'f1',
  form_name: 'Safety Check',
  form_version_id: 'v1',
  status: 'in_progress',
  score: null,
  score_breakdown: null,
  started_at: '2024-01-10T10:00:00Z',
  finished_at: null,
  answers: [],
}

const MOCK_VERSION = {
  id: 'v1',
  version: 1,
  status: 'published',
  published_at: null,
  fields: [
    {
      id: 'ff1',
      key: 'item_ok',
      label: 'Item OK?',
      field_type: 'boolean',
      required: true,
      position: 1,
      config_json: {},
    },
  ],
}

test.describe('Submissions list', () => {
  test.beforeEach(async ({ authed: page }) => {
    await page.route(`${API}/submissions**`, (r) =>
      r.fulfill({ json: paginated([MOCK_LIST_ITEM]) }),
    )
    await page.goto('/app/submissions')
  })

  test('displays submission list', async ({ authed: page }) => {
    await expect(page.getByText('Safety Check')).toBeVisible()
    await expect(page.getByText(/em andamento/i).first()).toBeVisible()
  })

  test('shows empty state when no submissions', async ({ authed: page }) => {
    await page.route(`${API}/submissions**`, (r) => r.fulfill({ json: paginated([]) }))
    await page.goto('/app/submissions')
    await expect(page.getByText(/nenhuma inspeção/i)).toBeVisible()
  })

  test('export CSV button is visible', async ({ authed: page }) => {
    await expect(page.getByRole('button', { name: /exportar csv/i })).toBeVisible()
  })

  test('filter tabs are visible', async ({ authed: page }) => {
    await expect(page.getByRole('button', { name: /todas/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /em andamento/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /concluídas/i })).toBeVisible()
  })
})

test.describe('Create submission', () => {
  test('opens composer with form select after clicking Nova inspeção', async ({ authed: page }) => {
    await page.route(`${API}/submissions**`, (r) => r.fulfill({ json: paginated([]) }))
    await page.route(`${API}/forms**`, (r) =>
      r.fulfill({
        json: paginated([{ id: 'f1', name: 'Safety Check', current_version_number: 1 }]),
      }),
    )
    await page.goto('/app/submissions')
    await page.getByRole('button', { name: /nova inspeção/i }).click()
    await expect(page.getByText('Selecione o formulário')).toBeVisible()
    await expect(page.getByRole('combobox')).toBeVisible()
  })

  test('creates submission and navigates to detail', async ({ authed: page }) => {
    await page.route(`${API}/forms/f1/versions/v1**`, (r) =>
      r.fulfill({ json: envelope(MOCK_VERSION) }),
    )
    await page.route(`${API}/forms**`, (r) =>
      r.fulfill({
        json: paginated([{ id: 'f1', name: 'Safety Check', current_version_number: 1 }]),
      }),
    )
    await page.route(`${API}/submissions/s1**`, (r) => r.fulfill({ json: envelope(MOCK_DETAIL) }))
    await page.route(`${API}/submissions**`, (r) => {
      if (r.request().method() === 'POST') return r.fulfill({ json: envelope(MOCK_DETAIL) })
      return r.fulfill({ json: paginated([]) })
    })

    await page.goto('/app/submissions')
    await page.getByRole('button', { name: /nova inspeção/i }).click()
    await page.getByRole('combobox').selectOption('f1')
    await page.getByRole('button', { name: /iniciar inspeção/i }).click()
    await expect(page).toHaveURL('/app/submissions/s1')
  })
})

test.describe('Submission detail', () => {
  test.beforeEach(async ({ authed: page }) => {
    await page.route(`${API}/forms/f1/versions/v1**`, (r) =>
      r.fulfill({ json: envelope(MOCK_VERSION) }),
    )
    await page.route(`${API}/submissions/s1**`, (r) => r.fulfill({ json: envelope(MOCK_DETAIL) }))
    await page.goto('/app/submissions/s1')
  })

  test('displays form name and status', async ({ authed: page }) => {
    await expect(page.getByRole('heading', { name: 'Safety Check' })).toBeVisible()
    await expect(page.getByText('Em andamento').first()).toBeVisible()
  })

  test('displays fields', async ({ authed: page }) => {
    await expect(page.getByText('Item OK?')).toBeVisible()
  })

  test('finish button is visible', async ({ authed: page }) => {
    await expect(page.getByRole('button', { name: /finalizar/i })).toBeVisible()
  })
})

test.describe('Submission report', () => {
  test('shows completed submission report', async ({ authed: page }) => {
    const completed = {
      ...MOCK_DETAIL,
      status: 'completed',
      score: 100,
      finished_at: '2024-01-10T11:00:00Z',
    }
    await page.route(`${API}/forms/f1/versions/v1**`, (r) =>
      r.fulfill({ json: envelope(MOCK_VERSION) }),
    )
    await page.route(`${API}/submissions/s1**`, (r) => r.fulfill({ json: envelope(completed) }))
    await page.goto('/app/submissions/s1/report')
    await expect(page.getByText('100').first()).toBeVisible()
    await expect(page.getByText('Aprovado')).toBeVisible()
  })
})
