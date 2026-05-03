# Cowork API

API REST modular em FastAPI com CRUD de usuários, gerenciamento de tarefas com FK por usuário e autenticação via JWT. Schema do banco versionado com Alembic, suporte a SQLite (dev) e PostgreSQL (Docker/produção).

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.11 |
| Framework | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.x |
| Validação | Pydantic v2 (com `EmailStr`) |
| Banco | SQLite (dev local) / PostgreSQL 16 (Docker e produção) |
| Migrations | Alembic |
| Auth | JWT (PyJWT) + bcrypt |
| Configuração | pydantic-settings (`.env`) |
| Testes | pytest + httpx (`TestClient`) |
| Containerização | Docker + Docker Compose |

## Estrutura de diretórios

```
.
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── .dockerignore
│
├── app/
│   ├── main.py                 # entrypoint FastAPI (sem create_all - schema via Alembic)
│   ├── core/
│   │   ├── config.py           # Settings via pydantic-settings (.env)
│   │   └── security.py         # bcrypt, JWT, get_current_user
│   ├── db/
│   │   └── database.py         # engine, SessionLocal, Base, get_db
│   ├── models/
│   │   ├── user.py             # ORM User
│   │   └── task.py             # ORM Task (FK -> users.id)
│   ├── schemas/
│   │   ├── user.py             # UserBase/Create/Update/Read
│   │   ├── task.py             # TaskBase/Create/Update/Read
│   │   └── auth.py             # LoginRequest, Token
│   ├── services/
│   │   ├── user_service.py     # regras de negócio + exceções de domínio
│   │   ├── task_service.py
│   │   └── auth_service.py
│   └── routes/
│       ├── health.py
│       ├── auth.py             # POST /auth/login
│       ├── users.py            # CRUD /users
│       └── tasks.py            # /users/{id}/tasks e /tasks/{id} (JWT)
│
├── migrations/                 # Alembic
│   ├── env.py                  # lê DATABASE_URL de app.core.config.settings
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial.py     # users + tasks
│
└── tests/
    ├── conftest.py             # fixture client (SQLite em memória, StaticPool)
    └── test_app.py             # 47 testes
```

## Configuração local (sem Docker)

Pré-requisitos: Python 3.11+ instalado.

```bash
git clone <seu-repo>.git
cd <seu-repo>

python -m venv .venv
source .venv/bin/activate            # Linux/Mac
# .venv\Scripts\activate             # Windows

pip install -r requirements.txt
cp .env.example .env                 # opcional - usa defaults se ausente

alembic upgrade head                 # cria SQLite e aplica migrations
uvicorn app.main:app --reload
```

A API sobe em `http://localhost:8000`. O banco vai para `./app.db` (SQLite). Sem `.env`, a app usa os defaults declarados em `app/core/config.py`.

## Configuração com Docker (PostgreSQL)

Pré-requisitos: Docker + Docker Compose instalados.

```bash
git clone <seu-repo>.git
cd <seu-repo>

cp .env.example .env                 # opcional - compose passa DATABASE_URL via env
docker compose up --build
```

Sobe dois containers:

- **`cowork-db`** — `postgres:16-alpine` na porta 5432, com volume nomeado `pgdata` (dados persistem entre `up`/`down`)
- **`cowork-api`** — FastAPI na porta 8000

Ordem de boot: o `api` espera o `db` ficar saudável (`pg_isready`), aplica `alembic upgrade head` e só então sobe o uvicorn.

```bash
docker compose down                  # para os containers
docker compose down -v               # para e zera o volume do Postgres
```

Editar arquivos em `./app` ou `./migrations` recarrega automaticamente (uvicorn `--reload`).

## Configuração do `.env`

```bash
cp .env.example .env
```

Em seguida, gere uma `SECRET_KEY` segura e cole no `.env`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

`.env` está no `.gitignore` e no `.dockerignore` — segredos **nunca** vão para o repositório nem para a imagem Docker.

### Variáveis disponíveis

| Variável | Default | Descrição |
|---|---|---|
| `APP_NAME` | `Cowork API` | Título exibido no `/docs` |
| `ENVIRONMENT` | `development` | Identifica o ambiente (development/staging/production) |
| `DATABASE_URL` | `sqlite:///./app.db` | URL de conexão SQLAlchemy |
| `SECRET_KEY` | (placeholder) | Chave de assinatura HS256 dos tokens JWT — **trocar em produção** |
| `ALGORITHM` | `HS256` | Algoritmo JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | TTL do access token |

## Migrations (Alembic)

O schema vive em `migrations/versions/`. **`Base.metadata.create_all` foi removido do app** — toda alteração de schema passa por migration.

```bash
# Aplicar todas as migrations pendentes (cria DB se vazio)
alembic upgrade head

# Após editar um modelo SQLAlchemy, gerar uma migration nova
alembic revision --autogenerate -m "add column foo to users"

# Reverter a última migration
alembic downgrade -1

# Ver versão atual e histórico
alembic current
alembic history
```

A `DATABASE_URL` usada pelo Alembic vem de `app/core/config.py` (que lê `.env`/env vars), então o mesmo comando funciona em SQLite local e Postgres no Docker.

`migrations/env.py` ativa `render_as_batch` quando o dialect é SQLite — assim alterações de coluna funcionam em SQLite (que historicamente não suporta `ALTER COLUMN`).

## Testes

```bash
pytest
```

47 testes cobrem `/health`, CRUD de users, paginação, validação de email (`EmailStr`), hashing de senha, login JWT, ownership de tasks. Os testes usam **SQLite em memória** via fixture e **não dependem de** `.env`, `app.db` no disco, Alembic ou Postgres rodando.

## Fluxo de autenticação

A API usa JWT no header `Authorization: Bearer <token>`. Endpoints de Task exigem token; os demais (health, login, CRUD de User) são públicos.

```
1. Cadastro          → POST /users com password
2. Login             → POST /auth/login retorna access_token
3. Requests com auth → header Authorization: Bearer <access_token>
```

Token tem TTL de 30 minutos por padrão (`ACCESS_TOKEN_EXPIRE_MINUTES`). Senha é hasheada com bcrypt antes de gravar; **`UserRead` nunca expõe** `hashed_password`.

Acesso a recursos de outro usuário retorna **404** (não revela existência).

## Exemplos com `curl`

Assumindo a API em `http://localhost:8000`.

### Health check (público)

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### Cadastro de usuário

```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Salim",
    "email": "salim@example.com",
    "password": "minha-senha-forte",
    "is_active": true
  }'
# 201 -> {"name":"Salim","email":"salim@example.com","is_active":true,"id":1}
```

### Login (retorna JWT)

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"salim@example.com","password":"minha-senha-forte"}'
# 200 -> {"access_token":"eyJhbGc...","token_type":"bearer"}
```

Para reuso, exporte o token numa variável:

```bash
export TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"salim@example.com","password":"minha-senha-forte"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### Listar usuários com paginação (público)

```bash
curl 'http://localhost:8000/users?skip=0&limit=10'
# limit acima de 100 retorna 422
```

### Buscar / atualizar / excluir usuário (público)

```bash
curl http://localhost:8000/users/1

curl -X PATCH http://localhost:8000/users/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"Novo Nome"}'

curl -X DELETE http://localhost:8000/users/1   # 204
```

### Criar task autenticada

```bash
curl -X POST http://localhost:8000/users/1/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title":"Comprar leite","description":"Mercado da esquina"}'
# 201 -> {"title":"Comprar leite","description":"Mercado da esquina","completed":false,"id":1,"user_id":1}
```

Sem token: 401. Com token de outro usuário no path: 404.

### Listar tasks do usuário autenticado

```bash
curl 'http://localhost:8000/users/1/tasks?skip=0&limit=10' \
  -H "Authorization: Bearer $TOKEN"
```

### Atualizar task (parcial)

```bash
curl -X PATCH http://localhost:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"completed":true}'
```

### Deletar task

```bash
curl -X DELETE http://localhost:8000/tasks/1 \
  -H "Authorization: Bearer $TOKEN"
# 204
```

## Endpoints principais

| Método | Rota | Auth | Notas |
|---|---|---|---|
| GET | `/health` | público | sanity check |
| POST | `/auth/login` | público | retorna `{access_token, token_type}` |
| POST | `/users` | público | cadastro (`password` opcional) |
| GET | `/users` | público | suporta `?skip=&limit=` (max 100) |
| GET | `/users/{id}` | público | 200 / 404 |
| PUT | `/users/{id}` | público | substituição total |
| PATCH | `/users/{id}` | público | parcial; 409 em conflito de email |
| DELETE | `/users/{id}` | público | 204 / 404 |
| POST | `/users/{user_id}/tasks` | **JWT** | `user_id` deve ser o do token |
| GET | `/users/{user_id}/tasks` | **JWT** | suporta paginação |
| GET | `/tasks/{task_id}` | **JWT** | apenas o dono |
| PATCH | `/tasks/{task_id}` | **JWT** | parcial, apenas o dono |
| DELETE | `/tasks/{task_id}` | **JWT** | apenas o dono |

Documentação interativa em `http://localhost:8000/docs` (Swagger) ou `/redoc`.

## Troubleshooting

### `ImportError: email-validator is not installed`

`EmailStr` exige o pacote `email-validator`. Já consta no `requirements.txt`. Se aparecer, reinstale:

```bash
pip install -r requirements.txt
```

### `connection refused` ou `could not translate host name "db"` (PostgreSQL)

A app está tentando falar com o Postgres mas ele não está disponível.

- **No Docker**: confirme que ambos os containers subiram. O `api` espera o `db` ficar saudável; se o `db` falha no healthcheck, o `api` nem sobe. Veja logs:
  ```bash
  docker compose logs db
  docker compose logs api
  ```
- **Sem Docker**: a `DATABASE_URL` no seu `.env` aponta para `db:5432` (hostname só resolve dentro do compose). Para rodar local sem Docker, troque para `sqlite:///./app.db` ou para `postgresql+psycopg://user:pass@localhost:5432/db` apontando para um Postgres rodando local.

### `sqlalchemy.exc.OperationalError: no such table: users`

Migrations não foram aplicadas. Rode:

```bash
alembic upgrade head
```

No Docker, o `command` do compose já roda isso antes do uvicorn. Se persistir, verifique a `DATABASE_URL` que o Alembic está usando:

```bash
alembic current   # mostra a versão atual no banco apontado
```

### `address already in use` na porta 8000

Outra coisa já está usando a porta.

```bash
# Linux/Mac - descobrir o PID
lsof -iTCP:8000 -sTCP:LISTEN

# Matar
kill -9 <PID>

# Ou subir em outra porta
uvicorn app.main:app --reload --port 8001
```

No Docker, mude o mapeamento em `docker-compose.yml`: `"8001:8000"`.

### `bcrypt` quebra ou demora muito

bcrypt 4+ funciona em Python 3.10+. Se o ambiente tem outra versão pré-instalada conflitando, force o upgrade:

```bash
pip install --upgrade bcrypt
```

A demora dos testes (~20s para 47 testes) é esperada — bcrypt é intencionalmente lento como medida de segurança.

### Token expirou (`401 Could not validate credentials`)

Tokens duram 30 minutos. Faça login de novo. Para alterar o TTL, ajuste `ACCESS_TOKEN_EXPIRE_MINUTES` no `.env`.

## Próximos passos recomendados

- **CI/CD** — pipeline GitHub Actions: lint (ruff), `pytest`, `alembic upgrade head` em DB de staging, build da imagem Docker, deploy automatizado.
- **Refresh tokens** — atualmente só há access token. Adicionar `POST /auth/refresh` com refresh token de TTL longo (dias) e access token de TTL curto (15 min) reduz superfície de ataque.
- **Roles e permissões** — adicionar campo `role` ao `User` (admin/user) e dependência `require_role(...)` para endpoints administrativos. Endpoints de listagem de users hoje são públicos — bom candidato para virar admin-only.
- **Logs estruturados** — substituir o logger default por `structlog` ou similar emitindo JSON com `request_id`, `user_id`, `path`, `latency_ms`. Facilita observabilidade em produção (CloudWatch, Datadog, etc).
- **Rate limiting** — `/auth/login` em particular merece rate limit por IP para mitigar brute force.
- **Soft delete** — `DELETE /users/{id}` hoje é hard delete e deixa tasks órfãs (FK sem `ON DELETE CASCADE`). Considerar soft delete (`deleted_at`) ou cascade explícito.

## Deploy no Render

A API roda em produção como container Docker. O repo já contém um `render.yaml` (Blueprint) que descreve o serviço web + Postgres como infraestrutura declarativa.

### Opção A — via Blueprint (recomendado)

1. Subir o repo para GitHub/GitLab.
2. No Render Dashboard: **New** → **Blueprint** → conectar o repositório.
3. Render lê `render.yaml` e propõe criar:
   - **`cowork-api`** — web service (Docker, plan `free`, health check em `/health`)
   - **`cowork-db`** — PostgreSQL gerenciado (plan `free`, database `cowork`)
4. Confirmar. Render:
   - Builda a imagem a partir do `Dockerfile`
   - Provisiona o Postgres
   - Injeta `DATABASE_URL` (`fromDatabase`), gera `SECRET_KEY` (`generateValue: true`) e seta `ENVIRONMENT=production`
   - Roda `alembic upgrade head` antes do uvicorn (CMD do Dockerfile)
   - Expõe a API em `https://cowork-api.onrender.com`

### Opção B — setup manual no painel

Se preferir não usar Blueprint:

1. **New** → **PostgreSQL** → cria a instância (anote o **Internal Database URL**).
2. **New** → **Web Service** → conecta o repo, runtime **Docker**.
3. Em **Environment**, adicione manualmente:

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | URL do Postgres do passo 1 |
   | `SECRET_KEY` | gere com `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
   | `ENVIRONMENT` | `production` |

4. Em **Settings** → **Health Check Path**: `/health`
5. **Manual Deploy**.

### Sobre o driver Postgres

O Render expõe `DATABASE_URL` no formato `postgresql://user:pass@host/db`. A app usa o driver **psycopg3**, que requer o prefixo `postgresql+psycopg://...`. O `app/db/database.py` normaliza isso automaticamente em runtime — nada precisa ser configurado manualmente.

### Migrations em produção

O `CMD` do Dockerfile é:

```sh
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Migrations são aplicadas a cada deploy, antes do uvicorn subir. Para múltiplas instâncias no futuro, mover `alembic upgrade head` para um **Pre-Deploy Command** no painel (`Settings` → `Pre-Deploy Command`) evita N execuções concorrentes.

Para inspecionar o estado em produção:

```bash
# Render Shell (na página do serviço)
alembic current
alembic history
```

### Validando o deploy

```bash
curl https://<seu-service>.onrender.com/health
# {"status":"ok"}
```

OpenAPI: `https://<seu-service>.onrender.com/docs`. Smoke test do fluxo completo: cadastro → login → criar task — todos os endpoints documentados acima funcionam idênticos em produção.

### Variáveis de ambiente em produção

`.env` **não** é commitado. Em produção, todas as variáveis vêm do painel do Render:

| Variável | Origem |
|---|---|
| `DATABASE_URL` | `fromDatabase` (Render Postgres) |
| `SECRET_KEY` | `generateValue: true` (Render gera no primeiro deploy) |
| `ENVIRONMENT` | `production` (hardcoded no `render.yaml`) |
| `APP_NAME`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | usam defaults do `config.py` (opcional sobrescrever) |

`SECRET_KEY` gerada pelo Render fica acessível apenas via painel — invisível no código e nos logs.

### Custo e limitações do plan free

- O serviço web `free` **dorme após 15 min de inatividade** e leva ~30s para acordar na próxima request. Para evitar, faça upgrade ou pinge `/health` periodicamente.
- O Postgres `free` expira em 90 dias. Para uso real, planos pagos.
