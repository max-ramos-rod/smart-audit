# DR-0006 — Abstração de Relatório (`ReportRenderer`)

**Status:** Proposta · **Data:** 2026-06-08 · **Depende de:** — · **Toca o core:** Não (aditivo)
**ADRs relacionadas:** 0013 (provider abstraction — precedente), 0011 (contrato HTTP), 0001

---

## 1. Resumo Executivo

**O que é.** Introduzir uma **abstração de renderização de relatório** (`ReportRenderer`) que
separa **o conteúdo do relatório** (dados da inspeção/laudo) **da forma de saída** (PDF, Excel,
JSON, webhook, API). O PDF atual vira **um renderer entre vários**.

**Problema que resolve.** Hoje o PDF é gerado **diretamente** (acoplado) em
`submissions/pdf.py`; o CSV é um caminho à parte. Não há como adicionar Excel, JSON, webhook ou
integração via API sem duplicar lógica. Mercado enterprise/internacional cobra integração
(ERP/CMMS) e formatos variados.

**Quem se beneficia.** Clientes que integram (SAP, Maximo, planilhas), empresas de inspeção que
emitem laudo em formatos exigidos, e a evolução de **laudo** (DR-0005).

---

## 2. Contexto Atual

> Fatos verificados.

- **PDF:** gerado com fpdf2 diretamente em `backend/app/modules/submissions/pdf.py`; endpoint
  `GET /submissions/{id}/export` (com `?inline`); fonte DejaVu Sans (Unicode).
- **CSV:** exportação da lista com filtro de status, caminho próprio.
- **Precedente de abstração (ADR 0013):** o módulo de e-mail já usa **provider abstraction** —
  protocol `EmailSender` + implementações (`SmtpEmailSender`/`ConsoleEmailSender`) + factory.
  É o **mesmo molde** a aplicar em relatórios.
- **Não existe:** abstração de relatório; nenhum formato além de PDF/CSV; sem webhook/API de
  saída.

**Dor:** acoplamento ao PDF; adicionar formato = mexer no gerador; integração enterprise
inviável.

---

## 3. Objetivos

### Funcionais

- **OF1.** Definir um **`ReportRenderer`** (protocol) que recebe um modelo de dados de relatório
  e produz uma saída.
- **OF2.** Reescrever o PDF atual como **`PdfReportRenderer`** (sem mudança de saída visível).
- **OF3.** Permitir **novos renderers** (Excel, JSON) sem alterar o serviço de inspeção.
- **OF4.** Suportar **entrega** além de download: webhook/POST para sistemas externos (integração).
- **OF5.** Servir de base para o **laudo** (DR-0005), que é um relatório com veredito/validade.

### Não Funcionais

- **ONF1. Aditivo:** o serviço de inspeção monta o **modelo de relatório**; renderers não contêm
  regra de negócio.
- **ONF2.** Seguir o **mesmo padrão** do `EmailSender` (ADR 0013): protocol + implementações +
  factory por settings/registro.
- **ONF3.** Renderização **determinística** (mesmos dados ⇒ mesma saída).
- **ONF4.** Isolamento por `company_id` e respeito ao contrato HTTP (ADR 0011) nos endpoints.

---

## 4. Não Objetivos

- **NÃO** mudar o conteúdo/visual do PDF atual nesta fase (só desacoplar).
- **NÃO** definir o **veredito**/laudo (isso é DR-0004/DR-0005); aqui é só a renderização.
- **NÃO** construir portal externo nem autenticação de webhooks de terceiros (evolução).
- **NÃO** substituir a exportação CSV existente de imediato (pode coexistir e migrar depois).

---

## 5. Alternativas Consideradas

### 5.1 Estrutura da abstração

**A) Protocol `ReportRenderer` + implementações + factory (molde do `EmailSender`, ADR 0013).** ✅
- *Vantagens:* coerência total com um padrão já aceito no projeto; trocar/adicionar formato sem
  tocar o serviço; testável.
- *Escolha:* recomendada.

**B) Funções soltas por formato (`export_pdf`, `export_excel`…).**
- *Desvantagens:* sem contrato comum; duplicação; difícil registrar/selecionar formato.
- *Rejeição:* não escala para vários formatos/entregas.

### 5.2 Modelo de dados do relatório

**A) Um **ReportModel** explícito (DTO) montado pelo serviço, agnóstico de formato.** ✅
- *Vantagens:* renderers puros; uma fonte de verdade; fácil adicionar formato.
- *Escolha:* recomendada.

**B) Cada renderer consulta o banco por conta própria.**
- *Desvantagens:* duplica queries; risco de divergência entre formatos.
- *Rejeição:* quebra "uma fonte de verdade".

### 5.3 Entrega

**A) Download (resposta HTTP) + webhook (POST a URL configurada) como estratégias de entrega.** ✅
- *Escolha:* cobre download e integração; webhook entra quando houver demanda.

---

## 6. Solução Recomendada

### Estrutura (espelha o `core/email/`)

```
core/report/  (ou modules/reports/)
  ├─ model.py      ReportModel (DTO agnóstico: dados da inspeção/laudo)
  ├─ renderer.py   ReportRenderer (protocol) + PdfReportRenderer + (futuro) Excel/Json
  └─ service.py    ReportService (monta o ReportModel; seleciona renderer; entrega)
```

### Comportamento e regras

- **RN1.** O `ReportService` monta um **`ReportModel`** a partir da inspeção (score, breakdown,
  conformidades, evidências, e — com DR-0004/DR-0005 — veredito, não conformidades, ações,
  validade).
- **RN2.** Um `ReportRenderer` recebe `ReportModel` e produz bytes + content-type; **não** contém
  regra de negócio.
- **RN3.** A seleção de renderer é por formato solicitado (factory/registro), à la
  `get_email_sender` (ADR 0013).
- **RN4.** O PDF atual vira `PdfReportRenderer` com saída idêntica (regressão zero).
- **RN5.** Entrega por **download** (HTTP) ou **webhook** (POST a URL), conforme configuração.
- **RN6.** Renderização determinística e isolada por empresa.

---

## 7. Impacto Arquitetural

- **Banco.** Nenhuma mudança obrigatória. (Opcional, com DR-0005: `report_emissions` para
  snapshot imutável de laudo.)
- **Backend.** Novo módulo de relatórios (`core/report` ou `modules/reports`): `ReportModel`,
  `ReportRenderer` (protocol) + `PdfReportRenderer` (migra `submissions/pdf.py`), `ReportService`.
  O endpoint `GET /submissions/{id}/export` passa a delegar ao `ReportService` com formato
  parametrizável.
- **Frontend.** Seleção de formato no export (PDF/Excel/JSON); para laudo (DR-0005), botão de
  emissão. Base `/app/`.
- **APIs.** `GET /submissions/{id}/export?format=pdf|excel|json` (envelope/binário conforme o
  caso; manter content-type correto). Webhook como entrega configurável. RFC 7807 (ADR 0011).
- **Auditoria/Observabilidade.** Registrar emissões/integrações (`report.exported`); métricas por
  formato.

---

## 8. Impacto em ADRs

- **ADR 0013 (provider abstraction) — precedente reaplicado.** O `ReportRenderer` segue o mesmo
  padrão do `EmailSender`. Pode-se generalizar o 0013 ou criar ADR irmã.
- **Reusa** ADR 0011 (contrato HTTP), 0001 (camadas).
- **Nova ADR:** *"Abstração de relatório (`ReportRenderer`)"* — protocol + `ReportModel` +
  estratégias de entrega; PDF como um renderer.

---

## 9. Modelo de Domínio

> Sem novas entidades de persistência obrigatórias; o foco é estrutura de código/contrato.

### Conceitos

- **ReportModel** — DTO agnóstico com tudo que um relatório precisa (cabeçalho, score,
  breakdown, itens + conformidades, evidências; e veredito/ações/validade com DR-0004/0005).
- **ReportRenderer** — protocol: `render(model) -> (bytes, content_type)`.
- **PdfReportRenderer / ExcelReportRenderer / JsonReportRenderer** — implementações.
- **ReportService** — monta o `ReportModel`, escolhe o renderer, entrega (download/webhook).

### Invariantes

- **INV1.** Renderers são puros: mesma entrada ⇒ mesma saída; sem regra de negócio.
- **INV2.** Há uma única fonte de verdade do conteúdo (`ReportModel`); formatos não divergem.
- **INV3.** Geração isolada por empresa (ADR 0003) e fiel ao contrato HTTP (ADR 0011).

---

## 10. Fluxos

### Principal — exportar inspeção

1. Usuário solicita export com `format=pdf|excel|json`.
2. `ReportService` monta o `ReportModel` da inspeção.
3. Seleciona o renderer correspondente; produz bytes + content-type.
4. Entrega por download (ou webhook, se configurado).

### Cenários de erro/limite

- **Formato não suportado** → erro RFC 7807 (formato inválido).
- **Inspeção inexistente / outra empresa** → 404 (isolamento).
- **Falha de webhook** → registrar e reportar; não corromper a geração (fail-soft, à la ADR 0013).

---

## 11. Riscos

### Técnicos
- **R-T1. Regressão visual do PDF** ao migrar. *Mitigação:* `PdfReportRenderer` reproduz a saída
  atual; testes de baseline.
- **R-T2. Complexidade prematura de formatos.** *Mitigação:* entregar PDF (migração) + 1 formato
  (JSON) primeiro; Excel/webhook sob demanda.

### Negócio
- **R-N1. Demanda real de formatos** incerta. *Mitigação:* priorizar pela exigência de contrato;
  a abstração custa pouco e o PDF já justifica.

### Operacionais
- **R-O1. Webhooks a terceiros** (retry/segurança). *Mitigação:* tratar como evolução; começar
  com download.

---

## 12. Estratégia de Implementação

- **Fase 1.** Extrair `ReportModel` + `ReportRenderer` (protocol) + `PdfReportRenderer`
  (migração do `pdf.py`), sem mudar a saída. Endpoint passa a delegar.
- **Fase 2.** `JsonReportRenderer` (base de integração/API) + `format=` no endpoint.
- **Fase 3.** `ExcelReportRenderer`; entrega por webhook (configurável).
- **Fase 4.** Integração com o **laudo** (DR-0005): `ReportModel` ganha veredito/ações/validade.

---

## 13. Critérios de Aceitação

- **CA1.** O export PDF atual continua idêntico após a migração para `PdfReportRenderer`
  (regressão zero).
- **CA2.** Adicionar um novo formato (ex.: JSON) **não** exige alterar o serviço de inspeção.
- **CA3.** `GET /submissions/{id}/export?format=…` retorna o content-type correto por formato.
- **CA4.** Formato inválido retorna erro RFC 7807.
- **CA5.** Renderização é determinística e isolada por empresa.
- **CA6.** O `ReportModel` é a única fonte de conteúdo (formatos não consultam o banco
  separadamente).

---

## 14. Questões em Aberto

- **Q1.** Local do módulo: `core/report/` (infra, como `core/email`) ou `modules/reports/`?
- **Q2.** Primeiro formato novo após o PDF: JSON (integração) ou Excel (operacional)?
- **Q3.** Webhook: autenticação/retry/segurança — escopo mínimo quando entrar.
- **Q4.** CSV atual: migrar para um `CsvReportRenderer` ou manter o caminho existente por ora?
- **Q5.** Laudo emitido deve ser **persistido** (snapshot imutável) — conecta DR-0005 (Q5 de lá).

---

## 15. Evoluções Futuras

> Fora do escopo deste DR.

- **API pública / integração** (CMMS/ERP: SAP, Maximo) consumindo o `ReportModel`.
- **Templates de laudo configuráveis** por norma/cliente (`ReportTemplate`).
- **Renderização de laudo assinado** (e-signature; mercado regulado).
- **Internacionalização do relatório** (locale: idioma, data, número, unidade).
- **Exportação em massa** (lote de inspeções para um cliente/período).
