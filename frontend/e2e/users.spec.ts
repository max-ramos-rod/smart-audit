import { API, envelope, paginated, test, expect } from './fixtures'

const MOCK_USERS = [
  { id: 'u2', name: 'Bob Inspector', email: 'bob@test.com', role: 'INSPECTOR', is_active: true },
  { id: 'u3', name: 'Carol Viewer', email: 'carol@test.com', role: 'VIEWER', is_active: false },
]

test.describe('Users', () => {
  test.beforeEach(async ({ authed: page }) => {
    await page.route(`${API}/users**`, (r) => r.fulfill({ json: paginated(MOCK_USERS) }))
    await page.goto('/users')
  })

  test('displays user list', async ({ authed: page }) => {
    await expect(page.getByText('Bob Inspector')).toBeVisible()
    await expect(page.getByText('Carol Viewer')).toBeVisible()
  })

  test('shows role badges', async ({ authed: page }) => {
    await expect(page.locator('tbody').getByText('INSPECTOR', { exact: true })).toBeVisible()
    await expect(page.locator('tbody').getByText('VIEWER', { exact: true })).toBeVisible()
  })

  test('shows active and inactive status chips', async ({ authed: page }) => {
    await expect(page.locator('tbody').getByText('Ativo', { exact: true })).toBeVisible()
    await expect(page.locator('tbody').getByText('Inativo', { exact: true })).toBeVisible()
  })

  test('create form is visible', async ({ authed: page }) => {
    await expect(page.getByRole('button', { name: /criar usuário/i })).toBeVisible()
  })

  test('submits create form and shows success', async ({ authed: page }) => {
    const newUser = { id: 'u4', name: 'Dave New', email: 'dave@test.com', role: 'INSPECTOR', is_active: true }
    await page.route(`${API}/users`, (r) => {
      if (r.request().method() === 'POST') return r.fulfill({ json: envelope(newUser) })
      return r.fulfill({ json: paginated([...MOCK_USERS, newUser]) })
    })

    await page.locator('.field').filter({ hasText: /nome completo/i }).locator('input').fill('Dave New')
    await page.locator('.field').filter({ hasText: /^E-mail$/i }).locator('input').fill('dave@test.com')
    await page.locator('.field').filter({ hasText: /senha inicial/i }).locator('input').fill('secret123')
    await page.getByRole('button', { name: /criar usuário/i }).click()
    await expect(page.getByText(/usuário salvo com sucesso/i)).toBeVisible()
  })
})
