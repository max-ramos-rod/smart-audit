# Frontend Smart Audit

Base inicial do frontend em Vue 3 com Vite, Pinia e Vue Router.

## Stack

- Vue 3
- Vite
- Pinia
- Vue Router
- Axios
- TypeScript

## Estrutura inicial

- `src/router`
- `src/stores/auth`
- `src/stores/context`
- `src/stores/users`
- `src/stores/forms`
- `src/stores/submissions`
- `src/services`
- `src/views`
- `src/components`
- `src/types`

## Pre-requisitos

- Node.js 20+
- npm 10+
- backend Smart Audit rodando em `http://127.0.0.1:8003`

## Configuracao

1. Entre na pasta do frontend:

```powershell
cd c:\Projetos\smart-audit\frontend
```

2. Crie o arquivo `.env` com base no exemplo:

```powershell
Copy-Item .env.example .env
```

Conteudo esperado:

```env
VITE_API_BASE_URL=http://127.0.0.1:8003/api/v1
```

## Instalar dependencias

```powershell
npm install
```

## Rodar em desenvolvimento

```powershell
npm run dev
```

Endereco esperado do Vite:

- `http://127.0.0.1:5174`

## Build de producao

```powershell
npm run build
```

## Preview local do build

```powershell
npm run preview
```

## Fluxo inicial ja preparado

- Login em `/login`
- Bootstrap de sessao com `/me/context`
- Seletor de empresa ativa
- Lista de usuarios
- Lista de formularios
- Lista de inspecoes

## Credenciais de desenvolvimento

Se estiver usando o backend local ja preparado anteriormente:

- `admin@smartaudit.local`
- `admin123456`

## Observacoes

- O frontend usa o header `X-Company-Id` automaticamente quando a empresa ativa esta selecionada.
- O token JWT fica salvo em `localStorage`.
- Os contratos esperados seguem o backend atual com envelopes `data/meta` e erros RFC 7807.
- Esta etapa entrega a fundacao visual e de integracao. Formularios de criacao/edicao ainda sao a proxima camada.
