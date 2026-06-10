import { API, envelope, paginated, test, expect } from './fixtures'

const MOCK_CLIENTS = [
  { id: 'cl1', name: 'Transportadora Alfa', is_active: true },
  { id: 'cl2', name: 'Mineradora Beta', is_active: true },
]

test.describe('Clients', () => {
  test.beforeEach(async ({ authed: page }) => {
    await page.route(`${API}/clients**`, (r) => r.fulfill({ json: paginated(MOCK_CLIENTS) }))
    await page.goto('/app/clients')
  })

  test('displays client list', async ({ authed: page }) => {
    await expect(page.getByText('Transportadora Alfa').first()).toBeVisible()
    await expect(page.getByText('Mineradora Beta').first()).toBeVisible()
  })

  test('create form is visible', async ({ authed: page }) => {
    await expect(page.getByRole('button', { name: /criar cliente/i })).toBeVisible()
  })

  test('submits create form and shows success', async ({ authed: page }) => {
    const newClient = { id: 'cl3', name: 'Construtora Gama', is_active: true }
    await page.route(`${API}/clients`, (r) => {
      if (r.request().method() === 'POST') return r.fulfill({ json: envelope(newClient) })
      return r.fulfill({ json: paginated([...MOCK_CLIENTS, newClient]) })
    })

    await page.locator('.field').filter({ hasText: /nome do cliente/i }).locator('input').fill('Construtora Gama')
    await page.getByRole('button', { name: /criar cliente/i }).click()
    await expect(page.getByText(/cliente salvo com sucesso/i)).toBeVisible()
  })

  test('shows empty state when no clients', async ({ authed: page }) => {
    await page.route(`${API}/clients**`, (r) => r.fulfill({ json: paginated([]) }))
    await page.goto('/app/clients')
    await expect(page.getByText(/nenhum cliente/i)).toBeVisible()
  })
})
