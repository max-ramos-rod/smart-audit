import { expect, test as base } from '@playwright/test'

const API = '**/api/v1'

base.describe('Login', () => {
  base.beforeEach(async ({ page }) => {
    await page.goto('/app/login')
  })

  base('renders login form', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /entrar/i })).toBeVisible()
    await expect(page.getByPlaceholder('seu@email.com')).toBeVisible()
    await expect(page.getByPlaceholder('Digite sua senha')).toBeVisible()
    await expect(page.getByRole('button', { name: /entrar/i })).toBeVisible()
  })

  base('shows error on invalid credentials', async ({ page }) => {
    await page.route(`${API}/auth/login`, (r) =>
      r.fulfill({ status: 401, json: { detail: 'Credenciais invalidas.' } }),
    )
    await page.getByPlaceholder('seu@email.com').fill('wrong@test.com')
    await page.getByPlaceholder('Digite sua senha').fill('wrongpass')
    await page.getByRole('button', { name: /entrar/i }).click()
    await expect(page.getByText(/credenciais invalidas/i)).toBeVisible()
  })

  base('redirects to home on successful login', async ({ page }) => {
    await page.route(`${API}/auth/login`, (r) =>
      r.fulfill({
        json: {
          data: {
            access_token: 'jwt-tok',
            token_type: 'bearer',
            expires_in: 3600,
            user: { id: 'u1', name: 'Alice', email: 'alice@test.com' },
          },
        },
      }),
    )
    await page.route(`${API}/me/companies`, (r) =>
      r.fulfill({ json: { data: [{ id: 'c1', name: 'Acme', slug: 'acme', role: 'OWNER' }] } }),
    )
    await page.route(`${API}/me/context`, (r) =>
      r.fulfill({
        json: {
          data: {
            user: { id: 'u1', name: 'Alice', email: 'alice@test.com' },
            active_company: { id: 'c1', name: 'Acme', role: 'OWNER' },
            membership: { id: 'm1', role: 'OWNER', company_id: 'c1', user_id: 'u1' },
          },
        },
      }),
    )
    await page.route(`${API}/me/stats**`, (r) =>
      r.fulfill({
        json: { data: { total_submissions: 0, completed: 0, in_progress: 0, avg_score: null, recent: [] } },
      }),
    )
    await page.route(`${API}/forms**`, (r) =>
      r.fulfill({ json: { data: [], meta: { page: 1, page_size: 20, total: 0, total_pages: 1, has_next: false } } }),
    )

    await page.getByPlaceholder('seu@email.com').fill('alice@test.com')
    await page.getByPlaceholder('Digite sua senha').fill('secret123')
    await page.getByRole('button', { name: /entrar/i }).click()
    await expect(page).toHaveURL('/')
  })

  base('has link to forgot password page', async ({ page }) => {
    await page.getByRole('link', { name: /esqueceu/i }).click()
    await expect(page).toHaveURL('/forgot-password')
  })
})

base.describe('Forgot Password', () => {
  base.beforeEach(async ({ page }) => {
    await page.goto('/app/forgot-password')
  })

  base('renders email form', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Recuperação de senha' })).toBeVisible()
    await expect(page.getByRole('textbox')).toBeVisible()
  })

  base('shows confirmation message after submit', async ({ page }) => {
    await page.route(`${API}/auth/forgot-password`, (r) => r.fulfill({ status: 200, json: {} }))
    await page.getByRole('textbox').fill('alice@test.com')
    await page.getByRole('button', { name: /enviar/i }).click()
    await expect(page.getByRole('heading', { name: 'Link enviado' })).toBeVisible()
  })
})

base.describe('Reset Password', () => {
  base('shows error when no token in URL', async ({ page }) => {
    await page.goto('/app/reset-password')
    await expect(page.getByRole('heading', { name: 'Link inválido' })).toBeVisible()
  })

  base('shows form when token is present', async ({ page }) => {
    await page.goto('/app/reset-password?token=abc123')
    await expect(page.getByPlaceholder('Mínimo 8 caracteres')).toBeVisible()
  })

  base('shows success after reset', async ({ page }) => {
    await page.route(`${API}/auth/reset-password`, (r) => r.fulfill({ status: 200, json: {} }))
    await page.goto('/app/reset-password?token=validtoken')
    await page.getByPlaceholder('Mínimo 8 caracteres').fill('newpass99')
    await page.getByPlaceholder('Repita a senha').fill('newpass99')
    await page.getByRole('button', { name: 'Definir nova senha' }).click()
    await expect(page.getByText(/senha redefinida/i)).toBeVisible()
  })
})
