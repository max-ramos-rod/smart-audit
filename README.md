# Smart Audit

Smart Audit é uma plataforma web para execução de checklists, auditorias e inspeções operacionais, com foco em padronização, histórico, evidências e operação multiempresa.

## Estado atual

O projeto já passou da fundação inicial. Hoje ele possui:

- backend assinado por FastAPI + SQLAlchemy async + PostgreSQL
- frontend SPA em Vue 3 + Pinia + Vue Router + Tailwind CSS v4, servido sob a base `/app/`
- landing page institucional estática na raiz `/` do domínio
- autenticação JWT + recuperação de senha completa (forgot + reset com token TTL 1h)
- contexto de empresa ativa com GET + PATCH `/companies/me`
- CRUD de usuários com desativação e revogação de acesso
- formulários versionados com seções, instruções e config por campo
- inspeções com respostas tipadas, score ponderado e avaliação de conformidade
- anexos e uploads locais
- equipes e membros com soft delete
- exportação PDF de inspeções (Unicode via DejaVu Sans) e exportação CSV
- dashboard, busca, notificações derivadas, auditoria e telas administrativas
- deploy em Docker Compose atrás de proxy reverso Nginx + Cloudflare Tunnel

Baseline validado em `2026-06-17`:

- backend: `296 passed`
- frontend Vitest: `185 passed`
- frontend build: `npm run build` OK
- E2E Playwright: `74 testes` (mockados)

Leitura de status:

- consolidado: autenticação, recuperação de senha, contexto multiempresa, usuários, equipes, formulários, inspeções, conformidade, evidências, uploads, PDF, auditoria e configurações da empresa
- parcial: busca (local, sem índice dedicado no backend), notificações (derivadas do estado das inspeções)
- pendente: storage externo (S3/R2), cadastro self-service de clientes

## Stack principal

- Backend: FastAPI, SQLAlchemy 2.x async, Alembic, PostgreSQL
- Frontend: Vue 3, Pinia, Vue Router, Tailwind CSS v4, Axios, Vitest, Playwright
- Uploads: armazenamento local em disco, com desenho compatível para migração futura a S3/R2
- Deploy: Docker Compose (db + backend + frontend), proxy reverso Nginx, Cloudflare Tunnel — ver `docs/Deploy_Smart_Audit.md`

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
- handoff visual: pasta [redesign-handoff/](redesign-handoff/) (mockups HTML de referência: Form Builder, Inspeção, Inspeção Lista, landing)

## Observação importante

A pasta `redesign-handoff/` hoje é uma referência de design e migração incremental. Parte dela já foi absorvida pelo frontend real, então ela não deve mais ser aplicada de forma cega por substituição integral.
