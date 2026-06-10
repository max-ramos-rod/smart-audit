import { API, envelope, paginated, test, expect } from './fixtures'

const MOCK_TYPES = [
  { id: 'at1', name: 'Veículo', description: null, attributes_schema: null, is_active: true },
]
const MOCK_CLIENTS = [{ id: 'cl1', name: 'Transportadora Alfa', is_active: true }]
const MOCK_ASSETS = [
  {
    id: 'a1',
    asset_type_id: 'at1',
    identifier: 'Caminhão 01',
    parent_asset_id: null,
    client_id: 'cl1',
    attributes_json: {},
    status: 'active',
  },
]

test.describe('Assets', () => {
  test.beforeEach(async ({ authed: page }) => {
    await page.route(`${API}/asset-types**`, (r) => r.fulfill({ json: paginated(MOCK_TYPES) }))
    await page.route(`${API}/clients**`, (r) => r.fulfill({ json: paginated(MOCK_CLIENTS) }))
    await page.route(`${API}/assets**`, (r) => r.fulfill({ json: paginated(MOCK_ASSETS) }))
    await page.goto('/app/assets')
  })

  test('displays asset list with type and client', async ({ authed: page }) => {
    // Escopado à tabela: "Veículo"/"Transportadora Alfa" também aparecem nos <option> dos filtros.
    const table = page.locator('.tbl')
    await expect(table.getByText('Caminhão 01')).toBeVisible()
    await expect(table.getByText('Veículo')).toBeVisible()
    await expect(table.getByText('Transportadora Alfa')).toBeVisible()
  })

  test('create form is visible', async ({ authed: page }) => {
    await expect(page.getByRole('button', { name: /criar ativo/i })).toBeVisible()
  })

  test('switching to component mode reveals the parent select', async ({ authed: page }) => {
    await page.getByRole('button', { name: /^componente$/i }).click()
    await expect(
      page
        .locator('.field')
        .filter({ hasText: /ativo pai/i })
        .locator('select'),
    ).toBeVisible()
  })

  test('submits create root asset and shows success', async ({ authed: page }) => {
    const newAsset = {
      id: 'a2',
      asset_type_id: 'at1',
      identifier: 'Van 02',
      parent_asset_id: null,
      client_id: null,
      attributes_json: {},
      status: 'active',
      components: [],
    }
    await page.route(`${API}/assets`, (r) => {
      if (r.request().method() === 'POST') return r.fulfill({ json: envelope(newAsset) })
      return r.fulfill({ json: paginated([...MOCK_ASSETS, newAsset]) })
    })

    await page
      .locator('.field')
      .filter({ hasText: /tipo de ativo/i })
      .locator('select')
      .selectOption('at1')
    await page
      .locator('.field')
      .filter({ hasText: /identificador/i })
      .locator('input')
      .fill('Van 02')
    await page.getByRole('button', { name: /criar ativo/i }).click()
    await expect(page.getByText(/ativo salvo com sucesso/i)).toBeVisible()
  })

  test('shows empty state when no assets', async ({ authed: page }) => {
    await page.route(`${API}/assets**`, (r) => r.fulfill({ json: paginated([]) }))
    await page.goto('/app/assets')
    await expect(page.getByText(/nenhum ativo/i)).toBeVisible()
  })
})
