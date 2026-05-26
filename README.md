# Smart Audit

Smart Audit e uma plataforma web para execucao de checklists, auditorias e inspecoes operacionais com foco em padronizacao, historico e evidencias.

## Objetivo inicial

Construir um MVP solido para:

- autenticacao basica
- contexto de empresa
- criacao de templates de inspecao
- versionamento de formularios
- execucao de inspecoes
- coleta de respostas por item
- anexos de evidencias
- dashboard inicial

## Decisoes iniciais

- Backend: FastAPI
- Frontend: Vue 3
- Banco: PostgreSQL
- Estilo arquitetural: `api -> service -> repository`
- Escopo do MVP: online-first
- Offline sync: fase futura

## Documentacao

- Arquitetura principal: [docs/Arquitetura_Smart_Audit.md](docs/Arquitetura_Smart_Audit.md)

## Principios do projeto

- modularizacao por dominio
- contratos HTTP consistentes
- regras de negocio fora dos endpoints
- persistencia encapsulada em repositories
- crescimento sustentavel sem overengineering
