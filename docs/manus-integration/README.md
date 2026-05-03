# Integração Manus — Inteligência de Mercado

> **Princípio do projeto:** IA aponta o alvo; time comercial valida o tiro.
> Não queremos volume cego. Queremos **sinais com evidência, prioridade, contexto e próxima ação**.

## Objetivo

Transformar análises geradas pelo **Manus** (a partir de sites, notícias, LinkedIn, editais, movimentos de concorrentes, empresas-alvo e sinais de mercado) em **registros estruturados na API**, inicialmente em staging, para apoiar:

- decisões comerciais
- prospecção B2B consultiva
- priorização de contas
- futura integração com LinkedIn / Sales Navigator / CRM / Lessie IA

## Fluxo

```
Manus detecta sinal de mercado
   │
   ▼
estrutura análise (payload JSON canônico — ver contract.md)
   │
   ▼
serializa em Task (mapping.md): title formatado + description Markdown estruturado
   │
   ▼
POST /api/v1/users/{user_id}/tasks   (autenticado JWT)  na API staging
   │
   ▼
Frontend de validação lista as tasks → time CETEM revisa, prioriza, executa ou descarta
   │
   ▼
quando o piloto provar valor, evolui pra entidade própria MarketInsight (ver § Critérios para evolução)
```

## Documentação relacionada

| Arquivo | Conteúdo |
|---|---|
| [contract.md](./contract.md) | Contrato JSON canônico do payload Manus + glossário de campos |
| [mapping.md](./mapping.md) | Como o payload vira Task (regras de title e description, exemplo curl) |
| [examples/](./examples/) | 5 payloads ficcionais cobrindo expansão, edital, contratação, concorrente, regulação |
| [scripts/smoke_manus_market_intelligence.py](../../scripts/smoke_manus_market_intelligence.py) | Script de smoke que carrega os 5 exemplos, faz login no staging e cria Tasks |

## Fase atual: piloto experimental em staging

- **Por que piloto:** queremos validar o fluxo real (Manus → API → action) antes de modelar uma entidade definitiva. Modelar cedo demais causa retrabalho quando a equipe descobre que precisa de campos diferentes do imaginado.
- **Por que staging:** banco isolado de produção; deploy manual; nenhuma exposição de cliente real.
- **Por que Task:** entidade já existe, já tem CRUD autenticado, já é exibida no frontend. Custo zero pra começar.

## Princípios de governança

Estas regras são **obrigatórias** para qualquer payload Manus que vire Task na API:

1. **Cada sinal precisa ter fonte.** `evidence.url` e `evidence.source_name` são obrigatórios. Sem fonte, não vira Task.
2. **Cada sinal precisa ter data de captura.** `evidence.captured_at` ISO 8601.
3. **Cada sinal precisa ter nível de confiança.** `evidence.confidence ∈ {low, medium, high}`. `low` ainda pode virar Task, mas owner sugerido deve ser `inteligencia` (não SDR), porque ainda precisa enriquecimento.
4. **Cada Task precisa ter próxima ação clara.** `commercial_action.recommended_next_step` deve ser **concreto** ("agendar reunião com Diretor de Operações da empresa X", não "estudar oportunidade").
5. **Não criar oportunidade comercial sem evidência.** Se o Manus não conseguiu capturar URL pública, não emitir o payload.
6. **Não registrar dados pessoais sensíveis** (CPF, dados de saúde, dados financeiros pessoais). Decisores aparecem por **cargo + área**, não por nome próprio.
7. **Não coletar dados fora de finalidade B2B legítima.** Foco em sinais públicos de empresas. Nada de scraping de perfis privados.
8. **Não automatizar abordagem externa sem revisão humana.** A Task vira ação só quando um humano da CETEM marca prioridade e confirma o passo seguinte.
9. **Não enviar dados desta fase para produção.** Banco staging é descartável e isolado.
10. **Não criar registro sem responsável e sem recomendação.** `commercial_action.suggested_owner` é obrigatório.

## LGPD e uso de dados B2B

- Foco do piloto: **dados públicos de empresas** (releases corporativos, editais, vagas no LinkedIn corporativo, releases de concorrentes, normas regulatórias).
- Decisores são representados por **cargo + área**, sem nome próprio. Mesmo nos exemplos ficcionais aqui, evita-se padronizar nomes pessoais.
- Não armazenar e-mails pessoais, telefones pessoais, dados de saúde, dados financeiros, opiniões políticas, dados de menores.
- Quando o piloto evoluir para `MarketInsight` e/ou integração com LinkedIn, fazer revisão de DPO antes de coletar dados de pessoas físicas, mesmo em contexto B2B.
- Toda Task gerada por Manus deve ter `tags` incluindo `manus` — facilita auditoria e expurgo se necessário.

## Critérios para evolução: Task → entidade própria

Hoje a `Task` carrega o payload inteiro dentro de `description` como Markdown + JSON. Funciona para o piloto, mas vira gargalo quando precisarmos de qualquer um destes:

### Gatilhos para criar `MarketInsight` (entidade própria, schema fixo, migration nova)

1. **Filtragem por empresa, setor, tipo de sinal, score ou fonte** — hoje exige full-text na description, sem índice
2. **Histórico de sinais por empresa** — ver todos os Manus que tocaram em "Saneamento Norte Brasil" no último ano
3. **Dashboards de inteligência de mercado** — agregações por setor / período / score / owner
4. **Integração formal com CRM** — sinal precisa de campos estáveis com nome canônico, não Markdown livre
5. **Relatórios executivos para diretoria** — pivot por setor × prioridade × score × tempo
6. **Score estruturado por oportunidade/ameaça** — comparar e ranquear via SQL
7. **Funil de inteligência de mercado** — quantos sinais por estágio, taxa de conversão sinal → oportunidade real
8. **Status do insight** — ciclo de vida: `novo → em_analise → aprovado → descartado → convertido_em_oportunidade`
9. **Vínculo com empresa/conta-alvo** — relacionamento N:N entre `MarketInsight` e `Account` (entidade ainda não existente)
10. **Histórico por fonte** — quantos sinais o Manus já gerou com `evidence.source_name = "DOU"` em 30 dias e qual taxa de aproveitamento
11. **Integração com LinkedIn / Sales Navigator** — payload de sinal precisa de campos canônicos (não pesquisar texto livre)
12. **Integração com CRM** — IDs estáveis e mapeamento bidirecional
13. **Integração com Lessie IA** — Lessie precisa consumir API tipada, não fazer extração de texto livre

### O que `MarketInsight` provavelmente vai precisar (rascunho — NÃO implementar agora)

```python
class MarketInsight(Base):
    __tablename__ = "market_insights"

    id = Column(Integer, primary_key=True)
    external_id = Column(String, unique=True, index=True)   # hash de payload + url evidência
    source = Column(String, index=True)                     # "manus", "manual", outros
    signal_type = Column(String, index=True)                # opportunity, threat, ...
    title = Column(String, nullable=False)
    summary = Column(Text)

    # Empresa (denormalizada por enquanto; mais tarde FK pra Account)
    company_name = Column(String, index=True)
    company_sector = Column(String, index=True)
    company_region = Column(String)
    company_website = Column(String)

    # Evidência
    evidence_url = Column(String)
    evidence_source_name = Column(String)
    evidence_published_at = Column(Date)
    evidence_captured_at = Column(DateTime, nullable=False)
    evidence_confidence = Column(String)                    # low/medium/high

    # Contexto + ação (estruturado mas com texto)
    pain_detected = Column(Text)
    trigger = Column(Text)
    relevance_to_cetem = Column(Text)
    related_solutions = Column(JSON)                        # ["SCADA", ...]
    decision_makers = Column(JSON)                          # array de objetos

    # Score
    score_fit = Column(Integer)
    score_urgency = Column(Integer)
    score_business_value = Column(Integer)
    score_evidence = Column(Integer)
    score_accessibility = Column(Integer)
    score_total = Column(Integer, index=True)

    # Workflow
    status = Column(String, default="novo", index=True)     # novo, em_analise, aprovado, descartado, convertido
    priority = Column(String, index=True)                   # low, medium, high, critical
    suggested_owner = Column(String)
    suggested_sla_hours = Column(Integer)
    recommended_next_step = Column(Text)

    # Multi-tenant / pessoas
    owner_user_id = Column(Integer, ForeignKey("users.id"), index=True)
    converted_to_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tags = Column(JSON)                                     # ["manus", ...]
```

Esse rascunho **não** está no código. Ele só serve como **âncora de design** para quando você decidir criar o ticket de implementação. Endpoints prováveis:

- `POST /api/v1/market-insights` — Manus envia direto, sem passar por Task
- `GET /api/v1/market-insights?sector=...&signal_type=...&score_min=...` — paginação, filtros indexados
- `GET /api/v1/market-insights/{id}`
- `PATCH /api/v1/market-insights/{id}` — workflow status + owner + priority
- `POST /api/v1/market-insights/{id}/convert-to-task` — gera Task a partir do insight

## O que **não** está sendo feito nesta fase

- nenhuma alteração no backend (sem novo model, sem novo endpoint, sem migration)
- nenhuma alteração em produção
- nenhum deploy disparado
- nenhuma integração direta com LinkedIn ou CRM
- nenhuma automação de disparo comercial externo
- nenhum dado pessoal sensível persistido
- nenhum nome real de cliente, prospect ou concorrente da CETEM nos exemplos

Tudo isso vira tarefa nova quando o piloto provar valor.

## Operação diária — Padrão A (atual)

> Este é o padrão **manual humano-no-loop** que o piloto usa por padrão. Quando estabilizar, a evolução natural é o Padrão B (Manus chama API direto) ou o Padrão C (cron + GitHub Actions). Ambos vivem futuramente; nada precisa ser construído pra eles agora.

### Fluxo do dia

```
┌─────────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌────────────┐
│ Manus (UI)      │───►│ Você baixa JSONs │───►│ ingest script    │───►│ Painel MI  │
│ scheduler diário│    │ → manus_inbox/   │    │ valida + POSTa   │    │ frontend   │
└─────────────────┘    └──────────────────┘    └──────────────────┘    └────────────┘
```

### Setup uma vez

1. **Criar/escolher user de integração no staging** — atualmente é `manus-integration-test+v1@example.com` (user_id `1`). Pra produção do piloto, recomendado registrar `manus-integration@cetem.com.br` via cadastro no frontend ou `POST /api/v1/users`. Depois trocar a senha pra um valor que só você sabe.

2. **Anotar a senha em local seguro** (gerenciador de senhas, não em arquivo). Vai ser exportada como env var no início de cada execução.

3. **Configurar o prompt diário do Manus** com diretiva detalhada — exemplo no fim desta seção.

4. **Garantir que `manus_inbox/` existe no projeto local** — já vem versionada vazia com `.gitkeep`.

### Rotina diária do analista CETEM (5-10 min)

```cmd
REM 1. Pegar os JSONs que o Manus gerou hoje, copiar pra:
REM    C:\Users\salim\projetos\cowork-api\manus_inbox\
REM    (pode ser drag-and-drop, robocopy, gh release dl, etc)

REM 2. Rodar o ingest:
cd C:\Users\salim\projetos\cowork-api
set MANUS_TEST_EMAIL=manus-integration-test+v1@example.com
set MANUS_TEST_PASSWORD=<sua-senha-do-user-de-integracao>
python scripts/ingest_manus_inbox.py
```

Saída esperada:

```
Encontrados N arquivo(s) JSON em manus_inbox
[auth] login como manus-integration-test+v1@example.com
[auth] OK token=eyJ...XXXX user_id=1
--- 2026-05-04-001.json ---
  [OK 201] task_id=42 title='[OPORTUNIDADE] ...'
--- 2026-05-04-002.json ---
  [OK 201] task_id=43 title='[EDITAL] ...'
...
============================================================
RESUMO
============================================================
  Total processado: N
  Sucesso (201): N
  Invalidos (validacao): 0
  Falhas 4xx: 0
  Falhas 5xx/network: 0
  Pendentes no inbox: 0
  Relatorio: manus_inbox/reports/2026-05-04T091203Z.txt
```

Depois, abrir `http://localhost:5173` → painel **Inteligência de Mercado** → revisar cards novos → atualizar status → marcar concluídos quando agir.

### Tratamento de falhas no ingest

| Cenário | O que o script faz | Você faz |
|---|---|---|
| JSON malformado | Marca `[INVALID]`, deixa no inbox | Conserta o JSON ou descarta o arquivo |
| Validação contra `contract.md` falha | `[INVALID]`, deixa no inbox | Pede pro Manus regenerar com schema correto |
| `HTTP 4xx` (não-401) | Deixa no inbox, marca no relatório | Investiga (validação backend, dado inválido), corrige |
| `HTTP 401` | **ABORTA o lote** | Confirma que `MANUS_TEST_PASSWORD` está com a senha certa |
| `HTTP 5xx` ou network | Deixa no inbox pra retry | Espera Render voltar (free dorme) e roda de novo |
| `HTTP 201` (sucesso) | Move arquivo pra `processed/YYYY-MM-DD/` | Nada — sucesso |

Re-rodar o script é seguro: arquivos com sucesso já saíram do inbox; só os que falharam serão re-tentados.

### Sobre idempotência

A API hoje **não dedupe**. Se um arquivo for processado por engano duas vezes (você reabriu de `processed/`, por exemplo), vai criar duas Tasks. Mitigação atual:

- O script **move** os arquivos após 201 — não há como o mesmo run duplicar
- Se você quiser re-importar manualmente, copia DE VOLTA pra `manus_inbox/` e roda — vai criar nova task
- Quando virar `MarketInsight`, vamos adicionar `external_id = hash(evidence.url + signal_type + captured_at)` com índice unique no banco

### Prompt diário sugerido pro Manus (uma vez, persistente)

```
Tarefa: Pesquisa diária de inteligência de mercado para a CETEM Tecnologia.

Frequência: 1x ao dia, manhã (horário a definir).

Setores prioritários (ajustar conforme estratégia):
- Saneamento
- Energia (cooperativas, distribuidoras, geração)

Fontes-alvo (pesquise em todas, mas priorize as primeiras):
1. Sala de imprensa de empresas-alvo (releases corporativos)
2. Diários oficiais (federal, estaduais dos estados-foco) com filtros: SCADA,
   automação, supervisão, monitoramento, telemetria
3. Portais de licitação (ComprasNet, BLL, BEC)
4. LinkedIn Jobs (filtrar por: "automação industrial", "SCADA", "TI/OT",
   "data engineer industrial", senioridade pleno+ ou sênior)
5. Sala de imprensa de concorrentes diretos (releases de novos contratos)

Para cada sinal encontrado:
1. Capture URL pública (sem login required)
2. Estruture conforme docs/manus-integration/contract.md
   (use os arquivos em docs/manus-integration/examples/ como referência)
3. Salve como arquivo JSON em ~/manus_inbox/YYYY-MM-DD-NNN.json
   onde NNN é sequencial 001, 002, ...

Regras obrigatórias:
- evidence.url é PÚBLICA (sem login)
- company.name + company.sector preenchidos
- evidence.confidence em {low, medium, high}
- commercial_action.recommended_next_step é CONCRETO
  (ex: "agendar reunião com Diretor X", não "estudar oportunidade")
- decision_makers: pelo menos 1 perfil por cargo+área
- score.total entre 0 e 100, somando 5 dimensões (fit, urgency, business_value,
  evidence_strength, accessibility), pesos máximos 25/25/20/15/15

Não faça:
- Não inclua nome próprio de pessoas físicas (decisores por cargo + área)
- Não colete CPF, telefone pessoal, dados de saúde, dados financeiros pessoais
- Não envie a API diretamente — apenas gere os arquivos JSON
- Não duplique sinais (mesma URL + mesmo signal_type) já enviados em dias anteriores

Volume alvo: 5 a 20 sinais/dia. Se for ficar acima de 20, pare e me avise
antes de continuar — pode estar com filtro muito largo.

Quando terminar, me avise quantos arquivos gerou e em qual pasta.
```

Esse prompt vai junto na configuração do agente Manus uma vez. O scheduler dele dispara diariamente. Os arquivos ficam disponíveis pra você baixar e colocar em `manus_inbox/`.

## Rotina operacional sugerida

Ciclo de uso, do sinal ao primeiro contato comercial:

| Passo | Quem | O que faz |
|---|---|---|
| 1 | Manus (automatizado) | Rastreia fontes definidas (sites de empresas-alvo, portais de licitação, LinkedIn, sala de imprensa de concorrentes, diários oficiais com filtros regulatórios) |
| 2 | Manus | Estrutura a análise no contrato JSON canônico (ver `contract.md`) |
| 3 | Script/integração | Valida payload → faz `POST /api/v1/users/{user_id}/tasks` no staging com payload serializado em `description` (ver `mapping.md`) |
| 4 | Time CETEM (analista de inteligência) | Abre o frontend → aba **Inteligência de Mercado** → revisa cards do dia |
| 5 | Analista | Para cada card, classifica status (`em_análise`, `aprovado`, `descartado`) — overlay client-side persiste em localStorage |
| 6 | Analista (se útil) | Aprova → vira ação comercial: pesquisa decisores no LinkedIn/Sales Navigator, valida contas via canais privados, prepara abordagem consultiva |
| 7 | SDR / pré-vendas | Executa próxima ação recomendada (`commercial_action.recommended_next_step`) dentro do SLA sugerido |
| 8 | Analista | Marca `convertido` quando vira oportunidade real de negócio; ou `descartado` quando não for útil |
| 9 | (futuro, fora do piloto) | Sinais convertidos viram oportunidades em CRM; dados retornam pra Manus pra fechar o loop e calibrar score |

> **Princípio operacional:** IA aponta o alvo, time comercial valida o tiro. Nenhuma abordagem externa (e-mail, mensagem, ligação) sai sem que um humano da CETEM tenha aprovado o sinal e a próxima ação.

### Como o frontend ajuda nessa rotina

- **Painel resumo no topo** mostra contagem por tipo, alta prioridade, e pendentes — visão de fluxo do dia
- **Filtros** por tipo, prioridade, setor e busca livre — para focar num segmento
- **Cards** com badges de tipo + prioridade + score — leitura visual rápida sem precisar abrir cada Markdown
- **Status dropdown** por card — workflow operacional sem precisar de backend MarketInsight ainda
- **Botão "Marcar concluída"** — aciona `PATCH /api/v1/tasks/{id}` com `completed=true` quando a ação foi executada

## Piloto CETEM — Inteligência de Mercado

### Duração e foco

- **Duração sugerida:** 1 a 2 semanas de uso real
- **Segmentos prioritários** (escolher 1 ou 2 pra começar — não mais que isso, pra evitar dispersão):
  - saneamento
  - energia
  - mineração
  - infraestrutura
  - manufatura
  - utilities (operação 24/7)

Recomendação: começar com **2 segmentos** que tenham maior aderência ao portfólio CETEM no momento. Mais segmentos significa mais sinais por dia, e o time precisa conseguir revisar todos sem deixar fila se acumular (se isso virar problema, é um gatilho pra `MarketInsight` com priorização automática).

### Critérios mínimos de qualidade do sinal

Cada sinal Manus que chega na API precisa ter, sem exceção (validado por `validate_payload` em `scripts/smoke_manus_market_intelligence.py`):

| Campo | Por quê |
|---|---|
| `evidence.url` + `evidence.source_name` | Sem fonte, não é sinal — é boato |
| `evidence.captured_at` (ISO 8601) | Para auditoria temporal e SLA |
| `company.name` + `company.sector` | Sem empresa-alvo, não vira ação |
| `signal_type` | Define a tag e o tratamento operacional |
| `evidence.confidence` (`low`/`medium`/`high`) | Separar conjectura de fato |
| `business_context.relevance_to_cetem` | Justifica por que esse sinal é nosso |
| `commercial_action.recommended_next_step` (concreto) | "Agendar reunião com Diretor X de Y" — não "estudar oportunidade" |
| `commercial_action.suggested_owner` | Inteligência / SDR / pré-vendas / executivo / diretoria |
| `commercial_action.suggested_sla_hours` | Janela máxima pra reagir (24h críticos, 96h normal) |
| `decision_makers` (≥ 1) | Ao menos um perfil-decisor mapeado |

Sinais sem qualquer um desses **não devem** virar Task. O script de smoke valida e rejeita antes de enviar.

### Métricas do piloto

Ao final das 1-2 semanas, avaliar:

| Métrica | Como medir | Sucesso |
|---|---|---|
| Volume diário de sinais | Total Manus criados / dia | Entre 5 e 20/dia (≤5 = Manus calibrar; ≥20 = analista satura) |
| Taxa de aprovação | `aprovado` / total de revisados | ≥ 30% (se < 10%, sinal muito ruidoso) |
| Taxa de conversão em oportunidade | `convertido` / `aprovado` | ≥ 20% (sinal aprovado vira oportunidade real) |
| Tempo médio até primeira ação | `aprovado` → `convertido` ou contato | Idealmente dentro do SLA sugerido |
| Falsos positivos | `descartado` por motivo "não relevante" | Idealmente < 30% |
| Cobertura de fontes | Diversidade em `evidence.source_name` | ≥ 5 fontes distintas |

Esses números viram input pra calibrar o Manus E pra justificar (ou não) a evolução pra `MarketInsight`.

### Gatilhos pra encerrar o piloto e evoluir

Se durante o piloto aparecer qualquer um destes, é hora de criar `MarketInsight`:

- Time pede "filtra por empresa X" — Task não suporta com performance
- Diretoria pede "relatório de sinais por setor no mês" — agregação inviável em texto livre
- CRM precisa receber sinais aprovados via API — formato Markdown não conversa
- Analista precisa ver histórico de sinais de uma mesma empresa — sem `company_id` indexado, não rola
- Score começa a ser questionado e demanda recálculo automático — campo precisa ser estruturado

Lista completa em § Critérios para evolução acima.
