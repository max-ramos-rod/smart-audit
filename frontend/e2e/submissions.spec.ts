import { API, envelope, paginated, test, expect } from './fixtures'

const MOCK_LIST_ITEM = {
  id: 's1',
  form_id: 'f1',
  form_name: 'Safety Check',
  asset_id: null,
  asset_identifier: null,
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
  asset_id: null,
  asset_identifier: null,
  status: 'in_progress',
  score: null,
  score_breakdown: null,
  started_at: '2024-01-10T10:00:00Z',
  finished_at: null,
  answers: [],
}

const MOCK_ASSETS = [
  {
    id: 'a1',
    asset_type_id: 'at1',
    identifier: 'Caminhão 01',
    parent_asset_id: null,
    client_id: null,
    attributes_json: {},
    status: 'active',
  },
]

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
  // Sprint 2: o composer inline (selects) foi substituído pelo InspectionComposer,
  // um wizard de 3 passos (formulário → cliente → ativo) com itens clicáveis.
  const MOCK_CLIENTS = [{ id: 'c1', name: 'Cliente X', is_active: true }]

  test('opens composer wizard on the form step after clicking Nova inspeção', async ({
    authed: page,
  }) => {
    await page.route(`${API}/submissions**`, (r) => r.fulfill({ json: paginated([]) }))
    await page.route(`${API}/assets**`, (r) => r.fulfill({ json: paginated(MOCK_ASSETS) }))
    await page.route(`${API}/forms**`, (r) =>
      r.fulfill({
        json: paginated([{ id: 'f1', name: 'Safety Check', current_version_number: 1 }]),
      }),
    )
    await page.goto('/app/submissions')
    await page.getByRole('button', { name: /nova inspeção/i }).click()
    await expect(page.getByText('Selecione o formulário')).toBeVisible()
    // O passo de formulário lista os formulários como itens clicáveis.
    await expect(page.getByRole('button', { name: /Safety Check/ })).toBeVisible()
  })

  test('creates submission and navigates to detail', async ({ authed: page }) => {
    await page.route(`${API}/forms/f1/versions/v1**`, (r) =>
      r.fulfill({ json: envelope(MOCK_VERSION) }),
    )
    await page.route(`${API}/assets**`, (r) => r.fulfill({ json: paginated(MOCK_ASSETS) }))
    await page.route(`${API}/clients**`, (r) => r.fulfill({ json: paginated(MOCK_CLIENTS) }))
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
    // Passo 1: formulário
    await page.getByRole('button', { name: /Safety Check/ }).click()
    await page.getByRole('button', { name: /avançar/i }).click()
    // Passo 2: cliente (sem cliente)
    await page.getByRole('button', { name: /sem cliente/i }).click()
    await page.getByRole('button', { name: /avançar/i }).click()
    // Passo 3: ativo (sem ativo) → iniciar
    await page.getByRole('button', { name: /iniciar inspeção/i }).click()
    await expect(page).toHaveURL('/app/submissions/s1')
  })

  test('links the selected asset on create (DR-0002 vínculo)', async ({ authed: page }) => {
    let postedAssetId: string | undefined
    await page.route(`${API}/forms/f1/versions/v1**`, (r) =>
      r.fulfill({ json: envelope(MOCK_VERSION) }),
    )
    await page.route(`${API}/assets**`, (r) => r.fulfill({ json: paginated(MOCK_ASSETS) }))
    await page.route(`${API}/clients**`, (r) => r.fulfill({ json: paginated(MOCK_CLIENTS) }))
    await page.route(`${API}/forms**`, (r) =>
      r.fulfill({
        json: paginated([{ id: 'f1', name: 'Safety Check', current_version_number: 1 }]),
      }),
    )
    await page.route(`${API}/submissions/s1**`, (r) => r.fulfill({ json: envelope(MOCK_DETAIL) }))
    await page.route(`${API}/submissions**`, (r) => {
      if (r.request().method() === 'POST') {
        postedAssetId = r.request().postDataJSON()?.asset_id
        return r.fulfill({ json: envelope(MOCK_DETAIL) })
      }
      return r.fulfill({ json: paginated([]) })
    })

    await page.goto('/app/submissions')
    await page.getByRole('button', { name: /nova inspeção/i }).click()
    // Passo 1: formulário
    await page.getByRole('button', { name: /Safety Check/ }).click()
    await page.getByRole('button', { name: /avançar/i }).click()
    // Passo 2: cliente (sem cliente) → carrega ativos
    await page.getByRole('button', { name: /sem cliente/i }).click()
    await page.getByRole('button', { name: /avançar/i }).click()
    // Passo 3: seleciona o ativo Caminhão 01 e inicia
    await page.getByRole('button', { name: /Caminhão 01/ }).click()
    await page.getByRole('button', { name: /iniciar inspeção/i }).click()
    await expect(page).toHaveURL('/app/submissions/s1')
    expect(postedAssetId).toBe('a1')
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

  test('shows linked asset identifier in the header', async ({ authed: page }) => {
    const linked = { ...MOCK_DETAIL, asset_id: 'a1', asset_identifier: 'Caminhão 01' }
    await page.route(`${API}/forms/f1/versions/v1**`, (r) =>
      r.fulfill({ json: envelope(MOCK_VERSION) }),
    )
    await page.route(`${API}/submissions/s1**`, (r) => r.fulfill({ json: envelope(linked) }))
    await page.goto('/app/submissions/s1')
    await expect(page.getByText(/Caminhão 01/).first()).toBeVisible()
  })
})

test.describe('Submission detail — inspeção por componente (DR-0002 T8)', () => {
  const SCOPED_VERSION = (required = false) => ({
    id: 'v1',
    version: 1,
    status: 'published',
    published_at: null,
    fields: [
      {
        id: 'ff1',
        key: 'pressao',
        label: 'Pressão do pneu',
        field_type: 'boolean',
        required,
        position: 1,
        config_json: {},
        component_type_id: 'ct1',
      },
    ],
  })

  const COMPONENT_DETAIL = {
    ...MOCK_DETAIL,
    asset_id: 'truck1',
    asset_identifier: 'Caminhão 01',
    checklist: [
      {
        field_key: 'pressao',
        field_type: 'boolean',
        component_type_id: 'ct1',
        components: [
          { asset_id: 'a1', label: 'Roda DD', type: 'Roda', path: 'Caminhão 01 > Roda DD' },
          { asset_id: 'a2', label: 'Roda DE', type: 'Roda', path: 'Caminhão 01 > Roda DE' },
          { asset_id: 'a3', label: 'Roda TD', type: 'Roda', path: 'Caminhão 01 > Roda TD' },
          { asset_id: 'a4', label: 'Roda TE', type: 'Roda', path: 'Caminhão 01 > Roda TE' },
        ],
      },
    ],
    warnings: [],
  }

  // Rotas específicas são registradas DEPOIS do catch-all `/submissions/s1**` porque o
  // Playwright prioriza a rota adicionada por último.
  test('renders one row per component for a scoped field', async ({ authed: page }) => {
    await page.route(`${API}/forms/f1/versions/v1**`, (r) =>
      r.fulfill({ json: envelope(SCOPED_VERSION()) }),
    )
    await page.route(`${API}/submissions/s1**`, (r) =>
      r.fulfill({ json: envelope(COMPONENT_DETAIL) }),
    )
    await page.route(`${API}/submissions/s1/attachments**`, (r) =>
      r.fulfill({ json: paginated([]) }),
    )
    await page.goto('/app/submissions/s1')

    for (const roda of ['Roda DD', 'Roda DE', 'Roda TD', 'Roda TE']) {
      await expect(page.getByText(roda).first()).toBeVisible()
    }
  })

  test('sends asset_id when marking a component conforme', async ({ authed: page }) => {
    let conformityBody: { items?: Array<{ field_key: string; asset_id?: string }> } | undefined
    await page.route(`${API}/forms/f1/versions/v1**`, (r) =>
      r.fulfill({ json: envelope(SCOPED_VERSION()) }),
    )
    await page.route(`${API}/submissions/s1**`, (r) =>
      r.fulfill({ json: envelope(COMPONENT_DETAIL) }),
    )
    await page.route(`${API}/submissions/s1/attachments**`, (r) =>
      r.fulfill({ json: paginated([]) }),
    )
    await page.route(`${API}/submissions/s1/conformity**`, (r) => {
      conformityBody = r.request().postDataJSON()
      return r.fulfill({ json: envelope(COMPONENT_DETAIL) })
    })
    await page.goto('/app/submissions/s1')

    // Expande a primeira instância (Roda DD) e marca Conforme.
    // exact: true evita casar com o chip de filtro "✓ Conformes" (plural).
    await page.getByText('Roda DD').first().click()
    await page.getByRole('button', { name: '✓ Conforme', exact: true }).first().click()

    await expect.poll(() => conformityBody?.items?.[0]?.asset_id, { timeout: 5000 }).toBe('a1')
    expect(conformityBody?.items?.[0]?.field_key).toBe('pressao')
  })

  test('blocks finish while a required component instance is pending', async ({ authed: page }) => {
    await page.route(`${API}/forms/f1/versions/v1**`, (r) =>
      r.fulfill({ json: envelope(SCOPED_VERSION(true)) }),
    )
    await page.route(`${API}/submissions/s1**`, (r) =>
      r.fulfill({ json: envelope(COMPONENT_DETAIL) }),
    )
    await page.route(`${API}/submissions/s1/attachments**`, (r) =>
      r.fulfill({ json: paginated([]) }),
    )
    await page.goto('/app/submissions/s1')

    await page.getByRole('button', { name: /finalizar inspeção/i }).click()
    await expect(page.getByText(/Campos com pendências/i).first()).toBeVisible()
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

  test('groups report results by component using the frozen snapshot (DR-0002 T9)', async ({
    authed: page,
  }) => {
    const SCOPED_VERSION = {
      id: 'v1',
      version: 1,
      status: 'published',
      published_at: null,
      fields: [
        {
          id: 'ff1',
          key: 'pressao',
          label: 'Pressão do pneu',
          field_type: 'boolean',
          required: true,
          position: 1,
          config_json: {},
          component_type_id: 'ct1',
        },
      ],
    }
    const reportDetail = {
      ...MOCK_DETAIL,
      status: 'completed',
      score: 75,
      finished_at: '2024-01-10T11:00:00Z',
      asset_id: 'truck1',
      asset_identifier: 'Caminhão 01',
      answers: [
        { field_key: 'pressao', field_type: 'boolean', value: true, asset_id: 'a1' },
        { field_key: 'pressao', field_type: 'boolean', value: false, asset_id: 'a2' },
        { field_key: 'pressao', field_type: 'boolean', value: true, asset_id: 'a3' },
        { field_key: 'pressao', field_type: 'boolean', value: true, asset_id: 'a4' },
      ],
      conformity: [
        {
          field_key: 'pressao',
          status: 'nao_conforme',
          justification: 'Pneu furado',
          asset_id: 'a2',
        },
      ],
      components_snapshot: {
        a1: { label: 'Roda DD', type: 'Roda', path: 'Caminhão 01 > Roda DD' },
        a2: { label: 'Roda DE', type: 'Roda', path: 'Caminhão 01 > Roda DE' },
        a3: { label: 'Roda TD', type: 'Roda', path: 'Caminhão 01 > Roda TD' },
        a4: { label: 'Roda TE', type: 'Roda', path: 'Caminhão 01 > Roda TE' },
      },
    }
    await page.route(`${API}/forms/f1/versions/v1**`, (r) =>
      r.fulfill({ json: envelope(SCOPED_VERSION) }),
    )
    await page.route(`${API}/submissions/s1**`, (r) => r.fulfill({ json: envelope(reportDetail) }))
    await page.route(`${API}/submissions/s1/attachments**`, (r) =>
      r.fulfill({ json: paginated([]) }),
    )
    await page.goto('/app/submissions/s1/report')

    // Uma linha por componente, com o rótulo congelado do snapshot.
    for (const roda of ['Roda DD', 'Roda DE', 'Roda TD', 'Roda TE']) {
      await expect(page.getByText(roda).first()).toBeVisible()
    }
    // A não conformidade aponta o componente afetado.
    await expect(page.getByText('Pneu furado')).toBeVisible()
  })
})
