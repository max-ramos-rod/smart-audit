# DR-0003 — Geração de Checklist por IA

**Status:** Proposta · **Data:** 2026-06-08 · **Depende de:** — · **Toca o core:** Não
**ADRs relacionadas:** 0005 (versionamento), 0007 (config_json), 0001 (camadas)

> **Diferencial estratégico.** É a iniciativa mais defensável do roadmap, *desde que* o moat
> seja construído na **qualidade, biblioteca de normas e loop de feedback** — não na chamada de
> LLM em si (copiável). Ver Riscos R-N1.

---

## 1. Resumo Executivo

**O que é.** Um pipeline que recebe o **upload de um documento** (norma, contrato, procedimento,
NR/ISO) e produz, via IA, um **rascunho de formulário** pronto para revisão — campos com tipo,
label, peso, instrução e (sugestão de) item crítico. O humano revisa no composer existente e
publica.

**Problema que resolve.** Montar um checklist do zero é a maior fricção de adoção. Empresas já
têm a norma/contrato; falta transformá-la em auditoria executável. A IA encurta de horas para
minutos.

**Quem se beneficia.** Todo cliente que adota o produto (acelera onboarding) e, comercialmente,
é o **demo que fecha vendas**. Reduz custo de implantação.

---

## 2. Contexto Atual

> Fatos verificados.

- **Composer de formulário** existe: o front monta `FormFieldCreatePayload` (key, label,
  field_type, required, position, config_json, instruction) e publica via `forms`.
- **Importador existe (irmão conceitual):** `POST /api/v1/forms/import` cria um formulário a
  partir de CSV/Excel — ou seja, **já há um caminho "fonte externa → formulário"**.
- **Versionamento imutável (ADR 0005):** publicar cria versão; não há editor de rascunho de
  versão. A IA deve produzir um **rascunho** que segue o fluxo de publicação humano.
- **Uploads** existem (arquivos em disco; ver storage externo na fundação).
- **Sem** qualquer integração de IA hoje.
- **Modelos disponíveis:** família Claude (Opus/Sonnet/Haiku) — a aplicação deve usar o modelo
  adequado por etapa e **prompt caching** para baratear.

**Dores:** onboarding lento; clientes desistem na etapa de montar o checklist.

---

## 3. Objetivos

### Funcionais

- **OF1.** Aceitar upload de documento (PDF/DOCX/TXT) como fonte de geração.
- **OF2.** Extrair texto (incl. OCR quando necessário) e segmentar (chunking) documentos longos.
- **OF3.** Gerar, via LLM, um **rascunho** de campos no formato `FormFieldCreatePayload`
  (tipo, label, required, weight, instruction; sugestão de item crítico — ver DR-0004).
- **OF4.** Apresentar o rascunho no **composer existente** para revisão/edição humana.
- **OF5.** Publicar segue o fluxo humano normal (ADR 0005) — a IA **nunca** publica.
- **OF6.** **Deduplicar** por hash do documento; o mesmo documento não é reprocessado.
- **OF7.** Persistir o resultado e o estado do job (consultável, reexecutável sob demanda).

### Não Funcionais

- **ONF1. Assíncrono:** processamento fora do caminho do request (fila/worker), com estados.
- **ONF2. Custo controlado:** dedup por hash, prompt caching, geração rara (versionamento
  reusa), nunca reprocessar o mesmo documento.
- **ONF3. Human-in-the-loop:** todo output é rascunho revisável; rastreabilidade de origem.
- **ONF4. Isolamento por `company_id`** (ADR 0003) em jobs e resultados.
- **ONF5. Observabilidade:** custo/latência/erro por job; taxa de aceitação pós-revisão (sinal
  de qualidade).

---

## 4. Não Objetivos

- **NÃO** auto-publicar formulário gerado (ADR 0005).
- **NÃO** treinar modelo próprio; usa-se LLM gerenciado.
- **NÃO** gerar ativos/componentes a partir do documento (poderia ser evolução futura).
- **NÃO** traduzir o documento (i18n de conteúdo é evolução futura).
- **NÃO** garantir 100% de fidelidade — o gate de qualidade é a revisão humana.

---

## 5. Alternativas Consideradas

### 5.1 Topologia do processamento

**A) Síncrono no request (upload → LLM → resposta).**
- *Vantagens:* simples.
- *Desvantagens:* request longo; custo no caminho quente; sem retry/dedup; trava com documentos
  grandes.
- *Rejeição:* não escala em custo nem UX.

**B) Pipeline assíncrono (fila → extração/OCR → chunking → LLM → rascunho → revisão).** ✅
- *Vantagens:* custo e latência controlados; dedup; estados; human-in-the-loop natural.
- *Desvantagens:* mais peças (job, worker, estados).
- *Escolha:* recomendada.

### 5.2 Worker/fila

**A) In-process (BackgroundTasks/`asyncio`).**
- *Vantagens:* zero infra nova; coerente com o porte atual.
- *Desvantagens:* não sobrevive a restart; sem retry robusto; limite de concorrência.
- *Uso:* aceitável para o MVP de baixo volume.

**B) Fila externa (Redis/RQ, Celery, etc.).**
- *Vantagens:* durabilidade, retry, escala.
- *Desvantagens:* infra nova (mais um serviço no Compose).
- *Escolha:* adotar quando o volume justificar (Q4); começar com A.

### 5.3 Formato de saída da IA

**A) `FormFieldCreatePayload[]` (o mesmo do composer).** ✅
- *Escolha:* plugga direto no composer e no fluxo de versão; zero formato novo.

**B) Formato intermediário próprio.**
- *Rejeição:* exige tradução extra e diverge do composer.

---

## 6. Solução Recomendada

### Pipeline

```
Upload do documento
   │  (hash; se já processado → reusa resultado, dedup)
   ▼
Extração de texto (+ OCR se imagem/escaneado)
   ▼
Chunking (documentos longos; respeitar limites de contexto)
   ▼
LLM (Claude) → rascunho de FormFieldCreatePayload[]
   │  (prompt caching do texto da norma entre chamadas)
   ▼
Persistência do resultado + estado do job
   ▼
Composer (revisão humana) → publicação (ADR 0005)
```

### Comportamento e regras

- **RN1.** Dedup por **hash do conteúdo**: documento idêntico não é reprocessado; reusa
  resultado.
- **RN2.** A IA produz **rascunho**; publicação é ação humana (ADR 0005).
- **RN3.** O job tem estados (ex.: `queued`, `extracting`, `generating`, `ready`, `failed`) e é
  isolado por empresa.
- **RN4.** Falha em qualquer etapa não publica nada e é reportada ao usuário (fail-safe).
- **RN5.** Saída no formato `FormFieldCreatePayload[]`, validável pelos schemas existentes.
- **RN6.** Registrar origem (documento → versão gerada) para auditoria e para o loop de feedback.

### O moat (não é a chamada de LLM)

- **Biblioteca curada** de checklists de normas (ISO/NR/etc.) acumulada dos clientes.
- **Loop de feedback:** as edições humanas pós-geração alimentam a melhoria do prompt/seleção.
- **Engenharia de domínio** no prompt (mapear cláusula → campo bom, com peso/criticidade).

---

## 7. Impacto Arquitetural

- **Banco.** Nova tabela de **job de geração** (`ai_generation_jobs` ou similar): `company_id`,
  hash do documento, referência ao arquivo, estado, resultado (JSONB), origem, timestamps.
  Nenhuma alteração no core de forms.
- **Backend.** Novo bounded context (`ai_forms`/`form_generation`): `service`/`repository`/
  `schemas` (ADR 0001) + worker. Integração com provedor de IA isolada atrás de uma abstração
  (à la `EmailSender`/`ReportRenderer`) para trocar de modelo/fornecedor.
- **Frontend.** Tela "Gerar de documento": upload, acompanhamento do job, abertura do rascunho
  no composer para revisão. Base `/app/`.
- **APIs.** Recursos sob `/api/v1` (criar job, consultar estado, obter rascunho). Envelope +
  RFC 7807 (ADR 0011).
- **Infra.** Worker/fila (in-process no MVP; externo depois). Storage do documento (usa a
  fundação de storage externo). Chave/credencial do provedor de IA via settings (padrão
  `get_settings`).
- **Observabilidade.** Métricas por job (custo, tokens, latência, erro) + taxa de aceitação
  pós-revisão como KPI de qualidade.
- **Auditoria.** `audit_logs`: `form.generated_from_document` (origem → versão).

---

## 8. Impacto em ADRs

- **Reforça ADR 0005** (rascunho → publicação humana).
- **Reusa ADR 0007** (saída usa `config_json` para weight etc.) e ADR 0001/0011.
- **Nova ADR:** *"Pipeline de geração por IA"* — assíncrono, dedup por hash, human-in-the-loop,
  abstração de provedor, prompt caching. (Pode referenciar o guia de Claude API do projeto.)

---

## 9. Modelo de Domínio

### Entidades

- **AiGenerationJob** — um processamento de documento→rascunho: empresa, documento (hash + ref),
  estado, resultado (rascunho de campos), origem, erros.

### Relacionamentos

```
Company 1─N AiGenerationJob
AiGenerationJob 0─1 Form (quando o rascunho é aceito e publicado, registra a origem)
```

### Invariantes

- **INV1.** Job isolado por `company_id`.
- **INV2.** Documento com mesmo hash (na mesma empresa) reusa resultado (dedup).
- **INV3.** Nenhum formulário é publicado sem ação humana (ADR 0005).
- **INV4.** Resultado é sempre um rascunho no formato `FormFieldCreatePayload[]` válido pelos
  schemas existentes.

---

## 10. Fluxos

### Principal

1. Usuário faz upload da norma.
2. Sistema calcula hash; se já processado, reusa; senão enfileira o job.
3. Worker: extrai texto (OCR se preciso) → chunking → LLM → rascunho → persiste.
4. Usuário abre o rascunho no composer, ajusta, e publica (ADR 0005).

### Cenários de erro

- **Documento sem texto extraível** → job `failed` com motivo; nada publicado.
- **Resposta da IA inválida** (campos fora do schema) → tentativa de saneamento; se falhar,
  `failed`; revisão humana sempre disponível.
- **Timeout/limite do provedor** → retry controlado; sem reprocessar duplicado.
- **Documento muito grande** → chunking; se exceder, sinaliza limite ao usuário.

---

## 11. Riscos

### Técnicos
- **R-T1. Custo/latência.** *Mitigação:* assíncrono, dedup por hash, prompt caching, geração
  rara (versionamento reusa).
- **R-T2. Qualidade variável da extração** (PDF escaneado). *Mitigação:* OCR; sinalizar baixa
  confiança; revisão humana.
- **R-T3. Acoplamento ao provedor de IA.** *Mitigação:* abstração de provedor (padrão
  `EmailSender`).

### Negócio
- **R-N1. Moat raso.** "PDF→LLM→checklist" é copiável em dias. *Mitigação:* defender com
  biblioteca proprietária, qualidade e loop de feedback — medir taxa de aceitação pós-revisão.
- **R-N2. Expectativa irreal** ("a IA faz tudo"). *Mitigação:* comunicar que é rascunho;
  revisão humana é parte do fluxo.

### Operacionais
- **R-O1. Vazamento de documento sensível** ao provedor de IA. *Mitigação:* política de dados
  do provedor; anonimização quando aplicável; transparência contratual.

---

## 12. Estratégia de Implementação

- **Fase 1 (MVP).** Upload + extração de texto (sem OCR) + LLM síncrono-em-background
  (in-process) + rascunho no composer + dedup por hash. Documentos pequenos/texto.
- **Fase 2.** OCR + chunking de documentos longos + abstração de provedor + prompt caching.
- **Fase 3.** Fila externa durável + métricas/KPIs (custo, aceitação) + biblioteca de normas.
- **Fase 4.** Loop de feedback (edições humanas melhoram a geração) — o moat.

---

## 13. Critérios de Aceitação

- **CA1.** Dado um PDF com texto extraível, o sistema gera um rascunho com ≥1 campo por
  requisito identificável, **sem** publicar.
- **CA2.** O mesmo documento (mesmo hash) não é reprocessado (dedup verificável).
- **CA3.** O rascunho abre no composer existente e pode ser editado e publicado pelo fluxo
  humano (ADR 0005).
- **CA4.** Falha de extração/IA resulta em job `failed` com motivo, sem publicar nada.
- **CA5.** Jobs e resultados não vazam entre empresas.
- **CA6.** Há métrica de custo por job e de taxa de aceitação pós-revisão.

---

## 14. Questões em Aberto

- **Q1.** Formatos de entrada suportados no MVP (só PDF? DOCX? imagens?).
- **Q2.** Modelo Claude por etapa (extração/estruturação vs geração) e limites de contexto.
- **Q3.** A IA sugere **peso e item crítico** (conecta DR-0004) ou só estrutura de campos?
- **Q4.** Worker in-process vs fila externa — gatilho de volume para migrar.
- **Q5.** Política de retenção do documento-fonte e do resultado (compliance/privacidade).
- **Q6.** A IA pode sugerir **seções** e agrupamento, não só campos planos?

---

## 15. Evoluções Futuras

> Fora do escopo deste DR.

- **Geração de ativos/componentes** a partir do documento (ex.: norma que descreve um
  equipamento → árvore de componentes; conecta DR-0001/DR-0002).
- **Biblioteca pública de checklists** de normas (ativo proprietário, reforça o moat).
- **Sugestão de melhoria** de formulários existentes (não só geração nova).
- **Multi-idioma na geração** (gerar o mesmo checklist em N idiomas sob demanda).
- **Citação de cláusula** — cada campo aponta o trecho da norma que o originou (rastreabilidade
  regulatória).
