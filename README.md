# Smart Audit

Smart Audit é uma plataforma web para execução de checklists, auditorias e inspeções operacionais, com foco em padronização, histórico, evidências e operação multiempresa.

## Estado atual

O projeto já passou da fundação inicial. Hoje ele possui:

- backend assinado por FastAPI + SQLAlchemy async + PostgreSQL
- frontend SPA em Vue 3 + Pinia + Vue Router + Tailwind CSS v4
- autenticação JWT
- contexto de empresa ativa com GET + PATCH `/companies/me`
- CRUD de usuários
- formulários versionados
- inspeções com respostas tipadas e score
- anexos e uploads locais
- equipes e membros
- exportação PDF de inspeções
- dashboard, busca, notificações derivadas e telas administrativas
- recuperação de acesso com rota placeholder segura

Baseline validado em `2026-05-27`:

- backend: `97 passed, 3 skipped`
- frontend: `68 passed`
- frontend build: `npm run build` OK

Leitura de status:

- consolidado: autenticação, contexto multiempresa, usuários, equipes, formulários, inspeções, evidências, uploads, PDF e configurações da empresa
- parcial: busca (local, sem índice dedicado no backend), notificações (derivadas do estado das inspeções)
- placeholder intencional: `forgot-password`, ainda sem fluxo transacional completo

## Stack principal

- Backend: FastAPI, SQLAlchemy 2.x async, Alembic, PostgreSQL
- Frontend: Vue 3, Pinia, Vue Router, Tailwind CSS v4, Axios, Vitest
- Uploads: armazenamento local em disco, com desenho compatível para migração futura a S3/R2

## Princípios do projeto

- arquitetura em camadas: `api -> service -> repository -> db`
- modularização por domínio
- regras de negócio fora dos endpoints
- persistência encapsulada em repositories
- multiempresa desde o core
- contratos HTTP consistentes
- erros padronizados em RFC 7807
- crescimento sustentável, evitando acoplamento prematuro

## Documentação

- arquitetura principal: [docs/Arquitetura_Smart_Audit.md](docs/Arquitetura_Smart_Audit.md)
- modelo de dados: [docs/DER_Smart_Audit.md](docs/DER_Smart_Audit.md)
- handoff visual: [redesign-handoff/README.md](redesign-handoff/README.md)

## Observação importante

A pasta `redesign-handoff/` hoje é uma referência de design e migração incremental. Parte dela já foi absorvida pelo frontend real, então ela não deve mais ser aplicada de forma cega por substituição integral.
