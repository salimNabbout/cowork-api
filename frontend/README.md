# Cowork API — frontend de validação

Interface mínima em React + Vite + TypeScript para validar o fluxo real da API antes de qualquer uso em produção.

> ⚠️ **Aponta apenas para staging.** O `.env.example` deste projeto preenche `VITE_API_BASE_URL` com a URL do Render staging. Não trocar para produção sem autorização explícita.

## Stack

- React 18
- Vite 5
- TypeScript 5 (strict)
- CSS plain, sem framework

## Pré-requisitos

- Node.js 18+ (testado com 20)
- npm (vem com Node)

## Setup

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Por padrão o Vite sobe em `http://localhost:5173`. A API Cowork (config default em `app/core/config.py`) já libera essa origem no `CORS_ORIGINS`, então o navegador deve aceitar as respostas.

Se aparecer erro de CORS no console:

1. Verifique se o Render staging tem `CORS_ORIGINS` setado e se inclui `http://localhost:5173`. Se a env var não estiver setada, o backend usa o default que **inclui** essa URL.
2. Se quiser usar outra porta, edite `vite.config.ts` e adicione a nova URL no `CORS_ORIGINS` do Render staging.

## Variáveis de ambiente

| Var | Default em `.env.example` | Função |
|---|---|---|
| `VITE_API_BASE_URL` | `https://api-de-coworking-staging.onrender.com` | Base da API consumida |

`.env` real fica fora do git (`.gitignore`). Apenas `.env.example` é versionado.

## Fluxos para validar

Depois que `npm run dev` estiver rodando, abra `http://localhost:5173`:

1. **Status da API** carrega automaticamente: `GET /` e `GET /health` aparecem no topo.
2. **Cadastro**: aba "Cadastrar" → preencha nome / email único / senha → "Cadastrar e entrar" faz `POST /api/v1/users` seguido de `POST /api/v1/auth/login` (auto-login).
3. **Login direto**: aba "Login" → email / senha de um usuário já cadastrado → `POST /api/v1/auth/login`.
4. **Criar task**: depois de logado, "Criar task" faz `POST /api/v1/users/{user_id}/tasks` com Bearer.
5. **Listar tasks**: `GET /api/v1/users/{user_id}/tasks` é chamado automaticamente após login e quando você clica "Recarregar".
6. **Logout**: limpa o `localStorage` (token + user id).

Erros HTTP (401/403/404/422/429/500/503) aparecem em vermelho com mensagem amigável + o `detail` do backend quando vier.

## Estrutura

```
frontend/
├── .env.example
├── .gitignore
├── README.md
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── index.html
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── App.css
    ├── vite-env.d.ts
    ├── services/
    │   └── api.ts          # cliente HTTP, tipos, friendlyMessage, parseJwtSub
    └── components/
        ├── ApiStatus.tsx   # GET / + GET /health
        ├── AuthForm.tsx    # cadastro / login
        └── TasksPanel.tsx  # criar / listar tasks
```

## Decisões importantes

### Persistência do `access_token`: `localStorage`

Escolhi `localStorage` porque:

- sobrevive a reload (UX melhor para validar)
- simples, sem state global externo, sem cookies
- token expira em 30 min (`ACCESS_TOKEN_EXPIRE_MINUTES` no backend), o que limita o blast radius

**Risco conhecido (XSS)**: se algum script malicioso conseguir rodar JS nesta origin (ex: stored XSS via `task.title` mal sanitizado), ele consegue ler o token. Mitigações nesta versão:

- todos os textos são renderizados via React (auto-escape)
- **nenhum** `dangerouslySetInnerHTML`
- nenhum script de terceiros importado

**O que seria melhor (fora do escopo)**: o backend setar um cookie `httpOnly + Secure + SameSite=Strict` no login, e o frontend nunca tocar no token. Isso exige mudança no `POST /api/v1/auth/login` — explicitamente fora do escopo desta etapa.

### Refresh token

A versão deployada em staging hoje (commit `44cef55`) **não retorna** `refresh_token` no login — o app antigo só emite access. O cliente declara `refresh_token` como opcional na resposta, e o `App.tsx` ignora se vier ausente. Quando a branch atual for promovida para staging, podemos passar a guardar o refresh com os mesmos cuidados de segurança do access (idealmente também via httpOnly cookie).

### `user_id` após login

A API atual não tem `/users/me` e o login só retorna `access_token`. Para descobrir o `user_id` no caminho de login, decodificamos o claim `sub` do JWT (sem validar a assinatura — só para ler o id). Função em `services/api.ts → parseJwtSub`. No caminho de cadastro, usamos o `id` que vem direto da resposta do `POST /users`.

## O que o frontend NÃO faz (intencionalmente)

- não tem deploy
- não aponta para produção
- não tem painel admin
- não implementa roles
- não muda nada no backend
- não tem build pipeline em CI ainda

Quando algum desses for desejado, vira etapa nova.
