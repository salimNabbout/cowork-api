# Contrato de payload — Manus → API Cowork

Este é o **contrato canônico** que o Manus deve produzir para que a API consiga registrar uma análise de inteligência de mercado.

> Fase atual do projeto: **piloto em staging**. O payload é serializado dentro de uma `Task` (ver `mapping.md`). Quando a entidade `MarketInsight` existir (ver gatilhos de evolução em `README.md`), o mesmo payload será aceito direto sem serialização.

## Estrutura JSON

```json
{
  "source": "manus",
  "signal_type": "opportunity",
  "title": "string curta",
  "summary": "resumo executivo da análise",
  "company": {
    "name": "Nome da empresa analisada",
    "website": "https://...",
    "sector": "saneamento | energia | mineracao | oleo-e-gas | infraestrutura | manufatura | tecnologia | outro",
    "region": "Brasil / estado / cidade"
  },
  "evidence": {
    "url": "link da fonte",
    "source_name": "nome legível da fonte",
    "published_at": "YYYY-MM-DD",
    "captured_at": "YYYY-MM-DDTHH:MM:SS",
    "confidence": "low | medium | high"
  },
  "business_context": {
    "pain_detected": "dor provável identificada",
    "trigger": "gatilho comercial (anúncio, edital, contratação...)",
    "relevance_to_cetem": "por que isso importa para a CETEM",
    "related_solutions": ["SCADA", "..."]
  },
  "commercial_action": {
    "priority": "low | medium | high | critical",
    "recommended_next_step": "ação recomendada concreta",
    "suggested_owner": "inteligência | SDR | pré-vendas | executivo | diretoria",
    "suggested_sla_hours": 24
  },
  "decision_makers": [
    {"role": "Diretor Industrial", "area": "Operações", "reason": "..."},
    {"role": "Gerente de Automação", "area": "Engenharia", "reason": "..."}
  ],
  "score": {
    "fit": 0,
    "urgency": 0,
    "business_value": 0,
    "evidence_strength": 0,
    "accessibility": 0,
    "total": 0
  },
  "tags": ["manus", "inteligencia-mercado", "..."]
}
```

## Campos — descrição e valores válidos

### Top-level

| Campo | Obrigatório | Tipo | Notas |
|---|---|---|---|
| `source` | sim | string | sempre `"manus"` nesta integração |
| `signal_type` | sim | enum | ver tabela abaixo |
| `title` | sim | string | ≤ 120 caracteres; vira parte do `Task.title` (ver `mapping.md`) |
| `summary` | sim | string | resumo executivo, 2-5 frases |

#### `signal_type` — valores aceitos

| Valor | Significado | Tag de Task |
|---|---|---|
| `opportunity` | oportunidade comercial geral | `[OPORTUNIDADE]` |
| `threat` | ameaça comercial / competitiva | `[AMEACA]` |
| `tender` | edital / licitação | `[EDITAL]` |
| `expansion` | expansão / novo CAPEX | `[EXPANSAO]` |
| `regulation` | mudança regulatória / ESG | `[REGULACAO]` |
| `competitor_move` | concorrente fechou contrato / lançou produto | `[CONCORRENTE]` |
| `technology_adoption` | empresa adota nova tecnologia | `[TECNOLOGIA]` |
| `hiring_signal` | vaga indica iniciativa em curso | `[CONTRATACAO]` |
| `investment` | rodada / aporte / captação relevante | `[INVESTIMENTO]` |
| `operational_pain` | dor operacional pública (incidente, denúncia) | `[DOR]` |

### `company`

| Campo | Obrigatório | Tipo | Notas |
|---|---|---|---|
| `name` | sim | string | razão social ou marca |
| `website` | recomendado | string ou `null` | url canônica; `null` se desconhecido |
| `sector` | sim | enum | ver lista abaixo |
| `region` | recomendado | string | "Brasil / estado / cidade" quando possível |

`sector`: `saneamento`, `energia`, `mineracao`, `oleo-e-gas`, `infraestrutura`, `manufatura`, `tecnologia`, `industrial` (genérico), `outro`.

### `evidence`

| Campo | Obrigatório | Tipo | Notas |
|---|---|---|---|
| `url` | sim | string | link público para a fonte |
| `source_name` | sim | string | nome legível ("Sala de imprensa X", "DOU", "LinkedIn Jobs") |
| `published_at` | recomendado | `YYYY-MM-DD` | data da publicação original |
| `captured_at` | sim | ISO 8601 | quando o Manus coletou |
| `confidence` | sim | enum | `low`, `medium`, `high` |

**Regra de governança:** `evidence.url` ausente → o sinal **não pode** virar Task (sem evidência, não vira oportunidade). Ver `README.md` § Governança.

### `business_context`

| Campo | Obrigatório | Tipo | Notas |
|---|---|---|---|
| `pain_detected` | sim | string | dor provável; uma frase |
| `trigger` | sim | string | gatilho comercial concreto |
| `relevance_to_cetem` | sim | string | por que importa pra CETEM, em prosa |
| `related_solutions` | sim | array de strings | catálogo CETEM (SCADA, IIoT, manutenção preditiva, integração TI/OT, data science, IA Agêntica, BMS, eficiência energética, dashboards regulatórios...) |

### `commercial_action`

| Campo | Obrigatório | Tipo | Notas |
|---|---|---|---|
| `priority` | sim | enum | `low`, `medium`, `high`, `critical` |
| `recommended_next_step` | sim | string | ação **concreta**, não genérica ("agendar reunião com Diretor X") |
| `suggested_owner` | sim | enum | `inteligencia`, `SDR`, `pre-vendas`, `executivo`, `diretoria` |
| `suggested_sla_hours` | sim | int | janela máxima recomendada para reagir |

### `decision_makers`

Array de objetos. Cada objeto:

| Campo | Obrigatório | Tipo | Notas |
|---|---|---|---|
| `role` | sim | string | cargo (Diretor Industrial, Gerente de Engenharia...) |
| `area` | sim | string | área (Operações, Engenharia, ESG...) |
| `reason` | sim | string | por que esse perfil importa pra esse sinal |

Mínimo recomendado: **2 decisores** (decisor econômico + validador técnico).

### `score`

Convenção CETEM (soma máxima 100):

| Critério | Peso máximo | O que mede |
|---|---|---|
| `fit` | 25 | encaixe técnico/portfólio CETEM |
| `urgency` | 25 | prazo, gatilho, janela |
| `business_value` | 20 | tamanho potencial / valor de referência |
| `evidence_strength` | 15 | qualidade da fonte |
| `accessibility` | 15 | probabilidade real de chegar nos decisores |
| `total` | 100 | soma das 5 dimensões |

> Score **não é** verdade absoluta — é prioridade sugerida pra o time. Time pode reranquear.

### `tags`

Array de strings curtas (lowercase, kebab-case). **Sempre** incluir:
- `manus` (rastreia origem)
- `inteligencia-mercado` (categoria)

Tags adicionais úteis: setor, signal_type, nome de concorrente envolvido, palavra-chave do gatilho. Ex: `["manus", "inteligencia-mercado", "saneamento", "scada", "expansao-industrial"]`.

## Validação mínima antes de virar Task

Um payload é **inválido** se faltar qualquer um destes:

- `source`, `signal_type`, `title`, `summary`
- `company.name`, `company.sector`
- `evidence.url`, `evidence.source_name`, `evidence.captured_at`, `evidence.confidence`
- `business_context.pain_detected`, `business_context.trigger`, `business_context.relevance_to_cetem`
- `commercial_action.priority`, `commercial_action.recommended_next_step`, `commercial_action.suggested_owner`
- pelo menos 1 item em `decision_makers`
- `score.total` (mesmo que estimativa)

Implementação dessa validação: ver `scripts/smoke_manus_market_intelligence.py` → função `validate_payload`.

## Versionamento do contrato

Versão atual: **`v0` (piloto)**. Mudanças no contrato durante o piloto não exigem migration porque a API não persiste o JSON em campos próprios — tudo entra na `Task.description` como texto. Quando o contrato estabilizar e migrarmos pra `MarketInsight`, criamos `v1` com schema fixo no banco.
