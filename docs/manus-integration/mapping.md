# Mapeamento Manus → Task

Esta página descreve **como** um payload Manus (ver `contract.md`) é convertido em uma `Task` na API durante o piloto.

> **Por que serializar dentro de Task?** A entidade `Task` atual tem `title`, `description`, `completed`, `user_id`. Não há campos próprios para `signal_type`, `score`, `company`, etc. Em vez de criar `MarketInsight` agora (e arrastar migration + schema antes de validar valor), entramos com texto estruturado na `description`. Critérios para evoluir estão em `README.md` § Critérios para evolução.

## Regra de transformação

### `Task.title`

Composição (com fallback anti-duplicação):

```
se company.name já aparece no payload.title:
    [TAG] {payload.title}
caso contrário:
    [TAG] {company.name truncado} — {payload.title}
```

- `[TAG]` é o mapeamento de `signal_type` (ver `contract.md` § signal_type) — sempre uppercase, sempre entre colchetes
- `company.name` é truncado a ~40 chars; se vier `"Multiplas (segmento: ...)"` (sinal de regulação que afeta múltiplas), usa `Multiplas` apenas
- a regra anti-duplicação evita títulos como `[CONTRATACAO] Mineradora Aurora Ltda. — Mineradora Aurora abre vaga...` (a primeira palavra do nome da empresa, em lowercase, é buscada no `payload.title`)
- separador é o em-dash `—` para ficar legível
- limite total ~180 chars; trunca com `...` se passar

Exemplos reais (gerados pelo script a partir dos 5 payloads em `examples/`):

```
[OPORTUNIDADE] Saneamento Norte Brasil anuncia nova ETA de 600 L/s
[EDITAL] Prefeitura Metropolitana abre PE para sistema de monitoramento de bombas
[CONTRATACAO] Mineradora Aurora abre vaga de Coordenador de Automacao Industrial
[CONCORRENTE] Cooperativa Energia Sul (CES) — Concorrente NorthAuto fecha contrato com cooperativa de energia em SC
[REGULACAO] Multiplas — Nova IN obriga monitoramento continuo de emissoes em plantas industriais SP
```

### `Task.description`

Bloco Markdown estruturado. Ordem fixa, sempre na mesma sequência (facilita parsing futuro):

```markdown
## Resumo
{summary}

## Empresa
- Nome: {company.name}
- Setor: {company.sector}
- Região: {company.region}
- Website: {company.website ou "—"}

## Evidência
- Tipo de sinal: {signal_type}
- Fonte: {evidence.source_name}
- URL: {evidence.url}
- Publicado em: {evidence.published_at ou "—"}
- Capturado em: {evidence.captured_at}
- Confiança: {evidence.confidence}

## Contexto comercial
- Dor provável: {business_context.pain_detected}
- Gatilho: {business_context.trigger}
- Relevância para a CETEM: {business_context.relevance_to_cetem}
- Soluções CETEM relacionadas: {related_solutions joined ", "}

## Decisores prováveis
- {role 1} ({area 1}) — {reason 1}
- {role 2} ({area 2}) — {reason 2}
...

## Score
- Fit: {fit}/25
- Urgência: {urgency}/25
- Valor: {business_value}/20
- Evidência: {evidence_strength}/15
- Acessibilidade: {accessibility}/15
- **Total: {total}/100**

## Próxima ação
- Prioridade: {priority}
- Owner sugerido: {suggested_owner}
- SLA: {suggested_sla_hours} h
- Recomendação: {recommended_next_step}

## Tags
{tags joined " · "}

---
<!-- payload-manus-v0 -->
```json
{json indentado}
```
```

> O bloco final ` ```json ... ``` ` carrega o **payload Manus original**. Isso permite que, quando criarmos `MarketInsight`, um script de migração leia cada Task com tag `manus`, parseie o JSON e converta no novo schema sem perda de informação.

### `Task.completed`

Sempre `false` na criação. Time comercial faz `PATCH /api/v1/tasks/{id}` com `{"completed": true}` quando a ação foi executada (ou descartada).

### Campos não usados

`Task` atual não tem campos para `priority`, `score`, `tags`, `metadata`. Tudo isso vive **dentro** do texto da `description`. Para filtrar por prioridade ou score, hoje seria full-text search ou parsing — gargalo claro, motivador para evoluir pra `MarketInsight`.

## Implementação de referência

A função `manus_to_task(payload: dict) -> dict` em `scripts/smoke_manus_market_intelligence.py` é a implementação canônica do mapeamento. Use-a como referência para qualquer outro cliente (worker do Manus, importador, etc.).

## Exemplo curl ponta a ponta

```bash
# Pré-requisito: ter um access_token JWT do user de integração Manus
export TOKEN="eyJ..."          # NUNCA versionar este valor
export USER_ID=42              # id do user de integração Manus
export BASE_URL="https://api-de-coworking-staging.onrender.com"

# 1) carrega um payload Manus de exemplo
PAYLOAD=$(cat docs/manus-integration/examples/01_expansao_industrial.json)

# 2) converte localmente para {title, description} via script
TASK_BODY=$(python3 -c "
import json, sys
sys.path.insert(0, 'scripts')
from smoke_manus_market_intelligence import manus_to_task
print(json.dumps(manus_to_task(json.loads(open('docs/manus-integration/examples/01_expansao_industrial.json').read()))))
")

# 3) envia para API
curl -s -X POST "$BASE_URL/api/v1/users/$USER_ID/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$TASK_BODY"
```

Resposta esperada: `201 Created` com o objeto Task incluindo `id`, `user_id`, `title`, `description`, `completed: false`.

## Idempotência (não há nesta fase)

A API hoje **não** dedupe por título nem por hash de payload — duas execuções do mesmo payload geram duas Tasks. Para o piloto, está ok (volume baixo, time comercial filtra). Quando virar `MarketInsight`, adicionar campo `external_id` (hash do payload + url da evidência) com índice único.
