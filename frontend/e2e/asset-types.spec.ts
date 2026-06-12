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

  test('builds attributes_schema via the visual builder (zero JSON)', async ({ authed: page }) => {
    // Sprint 1: o textarea de JSON foi substituído pelo AttributeSchemaBuilder.
    // Não há mais "JSON inválido"; o schema é montado de forma estruturada.
    let postedSchema: Record<string, { type?: string; required?: boolean }> | null | undefined
    await page.route(`${API}/asset-types`, (r) => {
      if (r.request().method() === 'POST') {
        postedSchema = r.request().postDataJSON()?.attributes_schema
        return r.fulfill({
          json: envelope({
            id: 'at3',
            name: 'Equipamento',
            description: null,
            attributes_schema: postedSchema ?? null,
            is_active: true,
          }),
        })
      }
      return r.fulfill({ json: paginated(MOCK_TYPES) })
    })

    await page
      .locator('.field')
      .filter({ hasText: /nome do tipo/i })
      .locator('input')
      .fill('Equipamento')
    await page.getByRole('button', { name: /adicionar atributo/i }).click()
    await page.locator('.asb-input').first().fill('placa')
    await page.getByRole('button', { name: /criar tipo/i }).click()

    await expect(page.getByText(/tipo salvo com sucesso/i)).toBeVisible()
    expect(postedSchema?.placa?.type).toBe('string')
  })

  test('shows empty state when no asset types', async ({ authed: page }) => {
    await page.route(`${API}/asset-types**`, (r) => r.fulfill({ json: paginated([]) }))
    await page.goto('/app/asset-types')
    await expect(page.getByText(/nenhum tipo de ativo/i)).toBeVisible()
  })
})
