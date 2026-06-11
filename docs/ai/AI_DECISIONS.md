# AI_DECISIONS — Decisões arquiteturais

Decisões **verificadas no código**. Inclui as explícitas (documentadas em
`docs/Arquitetura_Smart_Audit.md`/`docs/DER_Smart_Audit.md`) e as **implícitas** levantadas
em `docs/AUDIT_REPORT.md`. Cada uma traz o "porquê" e onde confirmar.

## Explícitas (consolidadas)

### Multiempresa desde o núcleo
Tenant ativo por membership; toda query de domínio filtra `company_id`. Sem isso, vazamento
entre empresas. — `modules/memberships/dependencies.py`.

### Versionamento imutável de formulários
Publicar nova versão cria `FormVersion` + `FormField` novos; a anterior nunca é mutada.
Mantém inspeções históricas legíveis. — `FormService.publish_new_version`.

### Modelo híbrido de respostas
`submission_values` (relacional, tipado) + `answers_json` (snapshot denormalizado). O
snapshot evita N+1 na leitura/finalização. Ambos escritos em `save_answers`.

### `config_json` como extensão de campo
Config específica (peso, allow_na, opções) em JSONB, evitando colunas esparsas e migrações a
cada nova opção. O service interpreta/valida.

### `section` sem `submission_value`
Campos `section` são divisores visuais: não geram valor, não entram no score nem nas
validações de finalização. Chave gerada como `__section_{posicao}__` pelo frontend.

### N/A em booleano
`value_text = "na"` com `value_boolean = NULL` distingue N/A de "sem resposta" (linha
inexistente). N/A não gera conformidade e fica fora do denominador do score.

### Score ponderado via conformities
Score sai de `submission_conformities`, não de `submission_values` — permite responder e
avaliar conformidade em etapas distintas. — `SubmissionService.calculate_score`.

### Soft delete por semântica da entidade
`memberships.revoked_at` (timestamp) e `teams.is_active` (bool). Histórico preservado em
ambos. Queries ativas filtram `revoked_at IS NULL` / `is_active = TRUE`.

### Notificações sem tabela própria
Derivadas em tempo real de `submissions`. Persistência só em `notification_reads`. Ver
"lida derivada" abaixo.

### Convite reaproveita o reset de senha
`POST /users/invite` cria usuário com senha aleatória inutilizável e gera token na **mesma**
`password_reset_tokens` (TTL 72h); o convidado define a senha pelo **mesmo**
`POST /auth/reset-password`. Evita uma máquina de "ativação" separada. — `UserService.invite_user`.

### E-mail como infraestrutura fail-soft
Tudo em `backend/app/core/email/` (sender/templates/service); `SmtpEmailSender` roda
`smtplib` via `asyncio.to_thread` e engole exceções — o fluxo HTTP nunca quebra por SMTP
(sustenta o anti-enumeração do forgot-password).

### PDF com fonte DejaVu Sans TTF
fpdf2 + DejaVu Sans embutida para cobrir Unicode/acentos PT. — `modules/submissions/pdf.py`.

## Implícitas (encontradas no código)

### "Lida" = existência de linha não-dispensada
`notification_reads` **não tem coluna `read`**. Uma notificação é "lida" se existe linha com
`dismissed = FALSE`; "dispensada" (`dismissed = TRUE`) é filtrada da resposta; "não lida" =
sem linha. Consequência: não dá para representar "li mas não dispensei" e "dispensei sem ler"
como estados ortogonais. — `NotificationReadRepository.get_read_keys`.

### `field_type` validado só pela CHECK do banco
O schema Pydantic usa `field_type: str` livre e `FormService.validate_fields` não reenumera os
tipos — a única barreira é o `CHECK` em `form_fields`. Ao mexer em tipos, a migration é
mandatória.

### `weight` é capacidade latente de qualquer campo
`calculate_score` lê `config_json.weight` de qualquer campo não-`section` com conformidade. A
restrição a `boolean` é convenção da UI (`FormFieldEditor.vue`), não do motor de score.

### `create_submission` usa sempre a maior versão
`max(form.versions, key=version)` sem filtrar `status='published'`. Funciona porque toda
versão é criada como `published`; não há rascunho de versão no fluxo atual.

### Upload não tem persistência própria
`POST /uploads` grava o arquivo em disco e devolve URL, mas **não cria registro em banco**. A
persistência de metadados só ocorre no `POST .../attachments`, sempre ligado a um
`submission_value` (criado on-demand).

### Janela e teto das notificações
`pending`: `in_progress` há +24h (**sem piso de data**). `low_score`/`excellent`: só
`completed` finalizadas nos **últimos 30 dias**. A query lê no máximo **50** submissions e a
resposta é limitada às **20** mais recentes. — `SubmissionRepository.list_for_notifications`.

### Faixa de score 80–89% silenciosa
Limiares de notificação: `< 80` → `low_score`, `>= 90` → `excellent`. A faixa intermediária
não gera alerta por design.

### Exportação CSV: BOM + teto
`export_csv` prefixa BOM UTF-8 (compatibilidade Excel PT-BR) e `list_all_for_export` limita a
**5000 linhas**.

### `X-Company-Id` opcional para membership único
O header é opcional quando o usuário tem exatamente 1 membership; obrigatório com 2+.

### Isolamento de teste por savepoint
`conftest.py` usa `join_transaction_mode="create_savepoint"` + rollback no teardown;
`expire_on_commit=False` e `populate_existing=True` nos reads garantem correção pós-mutação em
contexto async. Não substitua por mocks/SQLite — testes de integração exigem Postgres real.

## Inspeção por componente (DR-0002 / ADR-0016) — decisões finas (2026-06-10)

> Decididas no encerramento da discussão arquitetural das Fases 2–4. As estruturais (formato do
> `answers_json`, chave UUID, `components_snapshot`, `component_type_id`) estão na **ADR-0016**;
> abaixo, as de granularidade fina. Q1.2 (abaixo) **já implementada** na T1; as demais decididas,
> implementação em andamento.

### Semântica de NULL na unicidade (Q1.2) — DECIDIDO 2026-06-11, IMPLEMENTADO
A unicidade `(submission_id, form_field_id, asset_id)` usa **`NULLS NOT DISTINCT`**. Trata `NULL`
como **igual**, preservando a garantia histórica de **uma** resposta para campos gerais
(`asset_id NULL`) — retrocompatível com o constraint antigo — e permitindo **múltiplas** respostas
por componente quando `asset_id` está preenchido. O padrão (`NULLS DISTINCT`) trataria cada `NULL`
como distinto e perderia essa garantia (regressão). Requer **PostgreSQL 15+** (prod: PG 17 ✓; dev:
PG 18 ✓). — migration `e3f4a5b6c7d8`; modelos `submission_values`/`submission_conformities`
(`postgresql_nulls_not_distinct=True`); teste `test_submissions_component.py`.

### Campo escopado sem componentes correspondentes (Q2)
Se o ativo alvo não tem componentes do tipo escopado, o campo é **omitido da execução** + **aviso
não-bloqueante**. Não bloquear — inspecionar um ativo sem aquele componente é legítimo.

### Campo escopado em inspeção sem `asset_id` (Q3)
**Erro de configuração**: a **finalização é bloqueada** com mensagem clara; o rascunho ainda pode
ser salvo. Não ignorar silenciosamente.

### Peso por componente (Q6)
O `weight` vem sempre do `config_json` do **campo**, igual para todas as instâncias expandidas. Sem
peso por componente. A fórmula do ADR-0008 não muda — só a cardinalidade.

### Papel para cadastrar ativo (DR-0001, Q7)
Escrita de `assets`/`asset_types`/`clients` permanece **MANAGER+** (`get_manager_membership`). Não
relaxar para INSPECTOR — cadastro é estrutural, não execução de inspeção.

### Excluir tipo de ativo em uso (DR-0001, Q8)
**Soft delete simples** (`is_active = false`), sempre; tipo arquivado bloqueia novas instâncias
(V8); instâncias existentes permanecem. Sem hard delete (ADR-0009) e sem bloqueio/aviso obrigatório.

## Marcadas como evolução futura (não implementadas)

Apenas para evitar retrabalho: `corrective_actions` e storage externo (S3/R2) **não existem**
no código — não há tabela/módulo. Tratar como ausentes, não como parcialmente prontos.

Inspeção por componente (DR-0002 Fases 2–4) está **decidida** (ADR-0016 / SPEC) mas **não
implementada**. Seção repetível inteira (Q4) e peso por componente (Q6) ficaram como evolução
futura.
