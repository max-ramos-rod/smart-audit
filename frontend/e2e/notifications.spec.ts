import { API, envelope, test, expect } from './fixtures'

const MOCK_NOTIFICATIONS = [
  {
    id: 'pending-s1',
    type: 'pending',
    title: 'Inspeção pendente há 3h',
    description: 'Safety Check iniciada em 10/01/2024 sem finalização.',
    created_at: '2024-01-10T10:00:00Z',
    read: false,
  },
  {
    id: 'low-score-s2',
    type: 'low_score',
    title: 'Score abaixo do mínimo',
    description: 'Safety Check: 65% (mínimo recomendado: 80%).',
    created_at: '2024-01-09T15:00:00Z',
    read: false,
  },
  {
    id: 'excellent-s3',
    type: 'excellent',
    title: 'Inspeção concluída com excelência',
    description: 'Safety Check: score 95%.',
    created_at: '2024-01-08T12:00:00Z',
    read: true,
  },
]

test.describe('Notifications', () => {
  test.beforeEach(async ({ authed: page }) => {
    await page.route(`${API}/me/notifications**`, (r) => r.fulfill({ json: envelope(MOCK_NOTIFICATIONS) }))
    await page.goto('/notifications')
  })

  test('displays all notification titles', async ({ authed: page }) => {
    await expect(page.getByText('Inspeção pendente há 3h')).toBeVisible()
    await expect(page.getByText('Score abaixo do mínimo')).toBeVisible()
    await expect(page.getByText('Inspeção concluída com excelência')).toBeVisible()
  })

  test('shows unread count in description', async ({ authed: page }) => {
    await expect(page.getByText(/2 não lidas/i)).toBeVisible()
  })

  test('filter Não lidas hides read notifications', async ({ authed: page }) => {
    await page.getByRole('button', { name: /não lidas/i }).click()
    await expect(page.getByText('Inspeção concluída com excelência')).not.toBeVisible()
    await expect(page.getByText('Inspeção pendente há 3h')).toBeVisible()
  })

  test('Marcar como lida removes the button for that notification', async ({ authed: page }) => {
    const buttons = page.getByRole('button', { name: /marcar como lida/i })
    await expect(buttons).toHaveCount(2)
    await buttons.first().click()
    await expect(page.getByRole('button', { name: /marcar como lida/i })).toHaveCount(1)
  })

  test('Marcar todas como lidas removes all read buttons', async ({ authed: page }) => {
    await page.getByRole('button', { name: /marcar todas como lidas/i }).click()
    await expect(page.getByRole('button', { name: /marcar como lida/i })).toHaveCount(0)
  })

  test('empty state when no notifications', async ({ authed: page }) => {
    await page.route(`${API}/me/notifications**`, (r) => r.fulfill({ json: envelope([]) }))
    await page.goto('/notifications')
    await expect(page.getByText(/nenhuma notificação/i)).toBeVisible()
  })
})
