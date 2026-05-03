# manus_inbox/ — caixa de entrada do pipeline Manus (Padrão A)

Esta pasta é a **caixa de entrada operacional** do pipeline Padrão A descrito em `docs/manus-integration/README.md` (seção "Operação diária").

## Como funciona

```
manus_inbox/                      <- esta pasta (versionada vazia, com .gitkeep)
├── .gitkeep                      <- versionado para a pasta existir no repo
├── README.md                     <- este arquivo (versionado)
├── *.json                        <- payloads Manus do dia (NUNCA versionados)
├── processed/                    <- arquivos já enviados pra API (NUNCA versionados)
│   └── YYYY-MM-DD/
│       └── arquivo.json
└── reports/                      <- relatórios de cada execução (NUNCA versionados)
    └── YYYY-MM-DDTHHMMSSZ.txt
```

O `.gitignore` no root do projeto ignora `*.json`, `processed/` e `reports/` aqui dentro. **Nunca** commitar dados operacionais por engano.

## Workflow diário (5-10 min)

1. **Manus gera os JSONs** (no UI do Manus, conforme prompt diário documentado em `docs/manus-integration/README.md`)
2. **Você baixa os arquivos** do Manus e cola **nesta pasta** (top-level — não dentro de `processed/`)
3. **Roda o ingest:**
   ```cmd
   cd C:\Users\salim\projetos\cowork-api
   set MANUS_TEST_EMAIL=manus-integration-test+v1@example.com
   set MANUS_TEST_PASSWORD=<senha-do-user-de-integracao>
   python scripts/ingest_manus_inbox.py
   ```
4. **O script:**
   - Valida cada JSON contra `docs/manus-integration/contract.md`
   - Faz login com user de integração
   - POSTa cada um como Task no staging
   - Move processados pra `processed/YYYY-MM-DD/`
   - Salva relatório em `reports/YYYY-MM-DDTHHMMSSZ.txt`
5. **Você abre o frontend** (`http://localhost:5173`) → painel **Inteligência de Mercado** → revisa os cards novos
6. **Para cada card:** atualiza o status (Novo → Em análise → Aprovado / Descartado / Convertido) e marca "concluída" quando a ação foi executada

## Tratamento de erros

| Cenário | O que o script faz | O que você faz |
|---|---|---|
| JSON malformado | Marca `[INVALID]` no relatório | Conserta o arquivo OU descarta |
| Validação falha (campos faltando) | Marca `[INVALID]`, deixa no inbox | Pede pro Manus regenerar com schema correto |
| HTTP 4xx (exceto 401) | Marca `[HTTP 4xx]`, deixa no inbox | Olha o relatório, ajusta o JSON ou abre issue |
| HTTP 401 | **ABORTA o lote inteiro** | Confere senha em `MANUS_TEST_PASSWORD` |
| HTTP 5xx ou network | Marca `[HTTP 5xx]`, deixa no inbox | Espera a API voltar e roda de novo |
| HTTP 201 | Move arquivo pra `processed/YYYY-MM-DD/` | Nada — sucesso |

Arquivos que falham ficam no inbox para retry no próximo run. Após corrigir, basta rodar `python scripts/ingest_manus_inbox.py` de novo.

## Idempotência

A API hoje **não tem dedupe**. Se você rodar o mesmo arquivo duas vezes, ele vira duas Tasks distintas no banco. Como o script **move** o arquivo pra `processed/` após sucesso, o run seguinte não pega o mesmo de novo — desde que você **não copie o mesmo arquivo de volta**.

Quando o piloto evoluir pra `MarketInsight`, vamos adicionar `external_id = hash(payload + url)` com índice unique pra resolver dedupe a nível de banco.

## Limpeza periódica

A pasta `processed/` cresce (1 dia = 1 subpasta). Periodicamente, sem pressa:

```cmd
REM apaga arquivos processados com mais de 30 dias
forfiles /p manus_inbox\processed /s /d -30 /c "cmd /c del @file"
```

A `reports/` pode ser zipada e arquivada quando estiver grande. Não há retenção obrigatória.

## Aviso de segurança

- `manus_inbox/*.json` pode conter URLs de fontes ou textos sensíveis. **Nunca commitar.** Confirme antes do `git add`: rode `git status` e veja se nada de `manus_inbox/` aparece como tracked.
- A senha do user `manus-integration-test+v1@example.com` deve ficar **só** na env `MANUS_TEST_PASSWORD` quando você roda o script. Não escrever em arquivo, não colar no chat.
- O relatório em `reports/` registra **status HTTP e títulos de Task**, sem dados sensíveis. Mas vale revisar antes de compartilhar com terceiros.
