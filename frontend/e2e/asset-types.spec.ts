import { API, envelope, paginated, test, expect } from './fixtures'

const MOCK_TYPES = [
  { id: 'at1', name: 'Veículo', description: 'Frota', attributes_schema: null, is_active: true },
  { id: 'at2', name: 'Prédio', description: null, attributes_schema: null, is_active: true },
]

test.describe('Asset types', () => {
  test.beforeEach(async ({ authed: page }) => {
    await page.route(`${API}/asset-types**`, (r) => r.fulfill({ json: paginated(MOCK_TYPES) }))
    await page.goto('/app/asset-types')
  })

  test('displays asset type list', async ({ authed: page }) => {
    await expect(page.getByText('Veículo').first()).toBeVisible()
    await expect(page.getByText('Prédio').first()).toBeVisible()
  })

  test('create form is visible', async ({ authed: page }) => {
    await expect(page.getByRole('button', { name: /criar tipo/i })).toBeVisible()
  })

  test('submits create form and shows success', async ({ authed: page }) => {
    const newType = {
      id: 'at3',
      name: 'Equipamento',
      description: null,
      attributes_schema: null,
      is_active: true,
    }
    await page.route(`${API}/asset-types`, (r) => {
      if (r.request().method() === 'POST') return r.fulfill({ json: envelope(newType) })
      return r.fulfill({ json: paginated([...MOCK_TYPES, newType]) })
    })

    await page
      .locator('.field')
      .filter({ hasText: /nome do tipo/i })
      .locator('input')
      .fill('Equipamento')
    await page.getByRole('button', { name: /criar tipo/i }).click()
    await expect(page.getByText(/tipo salvo com sucesso/i)).toBeVisible()
  })

  test('rejects invalid JSON schema before submitting', async ({ authed: page }) => {
    await page
      .locator('.field')
      .filter({ hasText: /nome do tipo/i })
      .locator('input')
      .fill('Equipamento')
    await page
      .locator('.field')
      .filter({ hasText: /schema de atributos/i })
      .locator('textarea')
      .fill('{ invalid json')
    await page.getByRole('button', { name: /criar tipo/i }).click()
    await expect(page.getByText(/json inválido/i)).toBeVisible()
  })

  test('shows empty state when no asset types', async ({ authed: page }) => {
    await page.route(`${API}/asset-types**`, (r) => r.fulfill({ json: paginated([]) }))
    await page.goto('/app/asset-types')
    await expect(page.getByText(/nenhum tipo de ativo/i)).toBeVisible()
  })
})
