# Smart Audit

Smart Audit e uma plataforma web para execucao de checklists, auditorias e inspecoes operacionais, com foco em padronizacao, historico, evidencias e operacao multiempresa.

## Estado atual

O projeto ja passou da fundacao inicial. Hoje ele possui:

- backend assinado por FastAPI + SQLAlchemy async + PostgreSQL
- frontend SPA em Vue 3 + Pinia + Vue Router + Tailwind CSS v4
- autenticacao JWT
- contexto de empresa ativa
- CRUD de usuarios
- formularios versionados
- inspecoes com respostas tipadas
- anexos e uploads locais
- equipes e membros
- exportacao PDF de inspecoes
- dashboard, busca, notificacoes derivadas e telas administrativas
- recuperacao de acesso com rota placeholder segura

Baseline validado em `2026-05-27`:

- backend: `90 passed, 3 skipped`
- frontend: `68 passed`
- frontend build: `npm run build` OK

Leitura de status:

- consolidado: autenticacao, contexto multiempresa, usuarios, equipes, formularios, inspecoes, evidencias, uploads e PDF
- parcial: busca, notificacoes, perfil e configuracoes da empresa
- placeholder intencional: `forgot-password`, ainda sem fluxo transacional completo

## Stack principal

- Backend: FastAPI, SQLAlchemy 2.x async, Alembic, PostgreSQL
- Frontend: Vue 3, Pinia, Vue Router, Tailwind CSS v4, Axios, Vitest
- Uploads: armazenamento local em disco, com desenho compativel para migracao futura a S3/R2

## Principios do projeto

- arquitetura em camadas: `api -> service -> repository -> db`
- modularizacao por dominio
- regras de negocio fora dos endpoints
- persistencia encapsulada em repositories
- multiempresa desde o core
- contratos HTTP consistentes
- erros padronizados em RFC 7807
- crescimento sustentavel, evitando acoplamento prematuro

## Documentacao

- arquitetura principal: [docs/Arquitetura_Smart_Audit.md](docs/Arquitetura_Smart_Audit.md)
- modelo de dados: [docs/DER_Smart_Audit.md](docs/DER_Smart_Audit.md)
- handoff visual: [redesign-handoff/README.md](redesign-handoff/README.md)

## Observacao importante

A pasta `redesign-handoff/` hoje e uma referencia de design e migracao incremental. Parte dela ja foi absorvida pelo frontend real, entao ela nao deve mais ser aplicada de forma cega por substituicao integral.
