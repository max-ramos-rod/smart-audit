# Deploy - Smart Audit

Este documento descreve a topologia de produção do Smart Audit e as decisoes de
infraestrutura que sustentam o deploy em Docker atras de um proxy reverso.

## Visao geral da topologia

O Smart Audit roda em containers Docker. Em producao, ele compartilha o servidor
com outros projetos (ex.: `financas`, `sentinelfi`), todos atras de um unico
proxy reverso Nginx que termina o trafego vindo de um Cloudflare Tunnel.

```text
Internet (HTTPS)
      |
      v
Cloudflare Tunnel  (SSL termination, sem porta aberta no servidor)
      |
      v
nginx_proxy (container, rede app_network)
  |-- smartaudit.goevolux.com.br/        -> landing/index.html (estatico, volume)
  |-- smartaudit.goevolux.com.br/app/    -> smart_audit_frontend:80
  |-- smartaudit.goevolux.com.br/api/    -> smart_audit_backend:8003
  |-- (outros dominios -> outros projetos)
            |
            v
   smart_audit_frontend (Nginx interno, redes internal + app_network)
     |-- /app/      -> SPA Vue (arquivos estaticos)
     |-- /api/      -> smart_audit_backend:8003
     |-- /uploads/  -> smart_audit_backend:8003
            |
            v
   smart_audit_backend (FastAPI, redes internal + app_network)
            |
            v
   smart_audit_db (PostgreSQL, rede internal apenas)
```

## Base `/app/` do frontend

A landing page institucional ocupa a raiz `/` do dominio. O SPA opera sob o
prefixo `/app/`. Isso esta configurado em tres pontos que precisam ficar em sincronia:

- `frontend/vite.config.ts` -> `base: '/app/'` (prefixo dos assets no build)
- `frontend/src/router/index.ts` -> `createWebHistory('/app/')` (base do Vue Router)
- `frontend/nginx.conf` -> `location /app/` com `rewrite ^/app/(.*)$ /$1 break`

O `rewrite` remove o prefixo `/app/` antes do `try_files`, porque o Vite grava o
`index.html` e a pasta `assets/` na raiz do `dist/` (servido em
`/usr/share/nginx/smart-audit/`), nao sob `app/`. Sem o rewrite, os assets
(`/app/assets/*.js`) cairiam no fallback `index.html` e o browser receberia
`text/html` no lugar do JavaScript.

Os links da landing (`landing/index.html`) e os testes E2E (`page.goto`,
`toHaveURL`) usam o prefixo `/app/`.

## Redes Docker e colisao de nomes (decisao importante)

O `docker-compose.yml` define duas redes:

- `internal` - rede privada do projeto, criada pelo compose
- `app_network` - rede externa compartilhada com os outros projetos e com o `nginx_proxy`

Distribuicao dos servicos:

| Servico | container_name | Redes | Motivo |
|---|---|---|---|
| `db` | `smart_audit_db` | `internal` | Isolado; so o backend precisa alcancar |
| `backend` | `smart_audit_backend` | `internal` + `app_network` | Fala com o db (internal) e e alcancado pelo nginx_proxy (app_network) |
| `frontend` | `smart_audit_frontend` | `internal` + `app_network` | Fala com o backend (internal) e e alcancado pelo nginx_proxy (app_network) |

**Por que o db fica fora da app_network:** os tres projetos do servidor usavam
o mesmo nome de servico `db` na `app_network` compartilhada. O DNS do Docker
resolvia `db` por round-robin entre os tres PostgreSQL, e quando a resolucao
apontava para o banco de outro projeto a autenticacao falhava de forma
intermitente (`asyncpg.exceptions.InvalidPasswordError`). Mover o `db` para uma
rede `internal` privada elimina a colisao - o nome `db` volta a ser unico e
deterministico dentro do projeto.

**Referencia por nome unico de container:** qualquer servico que precise
atravessar a `app_network` (ex.: o `nginx_proxy` externo alcancando a API, ou o
Nginx interno do frontend chamando o backend) deve usar o `container_name`
unico - `smart_audit_backend`, nao o nome de servico `backend`. O nome de
servico `backend` tambem colide com os backends dos outros projetos na
`app_network`. Por isso o `frontend/nginx.conf` usa
`proxy_pass http://smart_audit_backend:8003`.

## Configuracao do nginx_proxy (externo)

O `nginx_proxy` vive em um projeto separado (`~/nginx-proxy`), fora do
`docker-compose.yml` do Smart Audit. Ele monta a landing como volume e roteia
os tres caminhos do dominio:

```nginx
server {
    server_name smartaudit.goevolux.com.br;

    # Landing na raiz (arquivo estatico via volume)
    location = / {
        root /var/www/smartaudit;     # volume: ../smart-audit/landing
        try_files /index.html =404;
    }

    # SPA
    location /app/ {
        proxy_pass http://smart_audit_frontend:80;
        proxy_set_header Host $host;
    }

    # API e uploads (nome unico do container)
    location /api/ {
        proxy_pass http://smart_audit_backend:8003;
        proxy_set_header Host $host;
    }
    location /uploads/ {
        proxy_pass http://smart_audit_backend:8003;
    }
}
```

O `nginx_proxy` resolve os nomes dos upstreams na inicializacao. Quando um
container e recriado e ganha novo IP na `app_network`, o proxy precisa ser
recarregado (`docker exec nginx_proxy nginx -s reload`) ou reiniciado para
re-resolver o nome.

## Volumes

- `smart_audit_pgdata` - dados do PostgreSQL. **Nunca** removido por
  `docker compose down` sozinho; apenas por `docker compose down -v`. Use `-v`
  somente para resetar o banco intencionalmente.
- `smart_audit_uploads` - arquivos de evidencia em disco
  (`/app/uploads/<company_id>/<uuid>.<ext>`). Sera substituido por storage
  externo (S3/R2) no futuro.

## Variaveis de ambiente

- `.env` (raiz do repo) - lido pelo backend. Contem `DATABASE_URL`,
  `JWT_SECRET_KEY`, etc. O `DATABASE_URL` usa o driver `asyncpg` e aponta para o
  host `db` (rede internal) ou `smart_audit_db` (container unico) na porta 5432.
- `.env.db` - lido pelo container PostgreSQL (`POSTGRES_USER`,
  `POSTGRES_PASSWORD`, `POSTGRES_DB`). A senha aqui deve ser identica a do
  `DATABASE_URL`.

**Atencao a senhas com caracteres especiais:** caracteres como `^`, `*`, `#` e
`%` na senha do `DATABASE_URL` quebram o parser de URL do asyncpg e/ou o
`configparser` do Alembic. Use senhas alfanumericas para o usuario do banco.

## Fluxo de deploy

```bash
# No servidor, dentro de ~/smart-audit
git pull

# Rebuild quando frontend/nginx.conf, Dockerfile ou codigo mudam
docker compose build frontend   # ou backend
docker compose up -d             # recria apenas o que mudou

# Quando containers sao recriados e ganham novo IP, recarregue o proxy
docker exec nginx_proxy nginx -s reload
```

O `nginx.conf` do frontend e embutido na imagem (`COPY` no Dockerfile), entao
mudancas nele exigem `docker compose build frontend`, nao apenas `up`.

## Onboarding de cliente (provisionamento manual)

Nao existe cadastro self-service ainda. Cada empresa e provisionada por scripts
executados no container do backend:

```bash
# 1. Criar o usuario admin
docker compose exec backend python backend/scripts/create_user.py \
  --name "Nome" --email admin@empresa.com --password senhaAlfanumerica

# 2. Criar a empresa e vincular o usuario
docker compose exec backend python backend/scripts/link_user_company.py \
  --email admin@empresa.com \
  --company-name "Empresa" --company-slug empresa --role OWNER
```

Os scripts criam o engine async dentro do event loop e leem `DATABASE_URL` do
ambiente. O admin entao cria os demais usuarios pelo painel (`/app/users`).

## Diagnostico rapido

```bash
# Estado dos containers
docker compose ps

# O nome do db resolve para um unico IP? (deve ser 1 linha)
docker compose exec backend getent hosts db

# O frontend alcanca o backend?
docker compose exec frontend wget -qO- http://smart_audit_backend:8003/api/v1/health

# Logs
docker compose logs backend --tail 20
docker logs nginx_proxy --tail 20
```

Sintomas comuns ja observados:

- **502 Bad Gateway (Cloudflare, Host Error)** - nginx_proxy nao alcanca o
  upstream. Verifique se o container alvo esta na `app_network` e se o proxy foi
  recarregado apos recriacao.
- **`host not found in upstream` no nginx_proxy** - o upstream referenciado
  (ex.: `smart_audit_backend`) nao esta na `app_network`.
- **`InvalidPasswordError` intermitente** - colisao de nome `db`/`backend` na
  `app_network`; confirme com `getent hosts db` retornando multiplos IPs.
- **`Failed to load module script ... MIME type text/html`** - o `/app/` nao
  esta fazendo o rewrite corretamente; os assets caem no fallback `index.html`.
