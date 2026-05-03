#!/usr/bin/env python3
"""
Smoke test da integracao Manus -> API Cowork.

Carrega os 5 payloads de inteligencia de mercado em
docs/manus-integration/examples/, transforma em Task via manus_to_task(),
faz login no staging com o user de integracao Manus e envia tudo.

USO:

    # Senha do user de integracao via env var (recomendado):
    set MANUS_TEST_PASSWORD=valor_local_aleatorio
    python scripts/smoke_manus_market_intelligence.py

    # Ou prompt interativo (sem env var):
    python scripts/smoke_manus_market_intelligence.py

REGRAS:

- NUNCA armazena tokens nem senhas em arquivo.
- Tokens nos logs aparecem mascarados.
- Funciona contra staging por default. NAO mude para producao.
"""

import base64
import getpass
import json
import os
import secrets
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = os.environ.get(
    "BASE_URL", "https://api-de-coworking-staging.onrender.com"
).rstrip("/")
TIMEOUT = 60
TEST_EMAIL = os.environ.get("MANUS_TEST_EMAIL", "manus-integration-test@example.com")
EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "docs" / "manus-integration" / "examples"
REPORT_PATH = Path(__file__).resolve().parent / "smoke_manus_report.txt"

# Mapeamento signal_type -> tag uppercase usada no Task.title.
# Espelha contract.md.
SIGNAL_TYPE_TAGS = {
    "opportunity": "OPORTUNIDADE",
    "threat": "AMEACA",
    "tender": "EDITAL",
    "expansion": "EXPANSAO",
    "regulation": "REGULACAO",
    "competitor_move": "CONCORRENTE",
    "technology_adoption": "TECNOLOGIA",
    "hiring_signal": "CONTRATACAO",
    "investment": "INVESTIMENTO",
    "operational_pain": "DOR",
}


# =============================================================
# HTTP utilitario
# =============================================================


class ApiError(Exception):
    def __init__(self, status, body):
        super().__init__(f"HTTP {status}: {body!r}")
        self.status = status
        self.body = body


def call(method, path, body=None, token=None):
    url = BASE_URL + path
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, _parse(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, _parse(e.read())
    except (urllib.error.URLError, TimeoutError) as e:
        raise ApiError(0, f"NETWORK_ERROR: {type(e).__name__}: {e}") from e


def _parse(raw):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return raw.decode(errors="replace")


def mask_token(t):
    if not t or not isinstance(t, str) or len(t) < 12:
        return "(ausente)"
    return f"{t[:3]}...{t[-4:]}"


# =============================================================
# Mapeamento Manus -> Task
# =============================================================


def validate_payload(p):
    """Valida campos minimos. Lanca ValueError se invalido. Ver contract.md."""
    required = [
        ("source", p),
        ("signal_type", p),
        ("title", p),
        ("summary", p),
    ]
    for k, obj in required:
        if not obj.get(k):
            raise ValueError(f"campo obrigatorio ausente: {k}")
    company = p.get("company") or {}
    if not company.get("name") or not company.get("sector"):
        raise ValueError("company.name e company.sector sao obrigatorios")
    evidence = p.get("evidence") or {}
    for k in ("url", "source_name", "captured_at", "confidence"):
        if not evidence.get(k):
            raise ValueError(f"evidence.{k} e obrigatorio")
    bc = p.get("business_context") or {}
    for k in ("pain_detected", "trigger", "relevance_to_cetem"):
        if not bc.get(k):
            raise ValueError(f"business_context.{k} e obrigatorio")
    ca = p.get("commercial_action") or {}
    for k in ("priority", "recommended_next_step", "suggested_owner"):
        if not ca.get(k):
            raise ValueError(f"commercial_action.{k} e obrigatorio")
    if not (p.get("decision_makers") or []):
        raise ValueError("decision_makers precisa de pelo menos 1 item")


def manus_to_task(payload):
    """Converte payload Manus em {title, description} para a API.

    Implementacao canonica do mapeamento descrito em mapping.md.
    """
    validate_payload(payload)

    tag = SIGNAL_TYPE_TAGS.get(payload["signal_type"], payload["signal_type"].upper())
    company_name = payload["company"]["name"]
    if "(" in company_name and "Multiplas" in company_name:
        company_short = "Multiplas"
    else:
        company_short = company_name[:40]

    manus_title = payload["title"].strip()
    title_max = 180
    # Se o titulo Manus ja menciona a empresa, evita duplicacao
    if company_short and company_short.split()[0].lower() in manus_title.lower():
        title = f"[{tag}] {manus_title}"
    else:
        title = f"[{tag}] {company_short} — {manus_title}"
    if len(title) > title_max:
        title = title[: title_max - 3] + "..."

    company = payload["company"]
    evidence = payload["evidence"]
    bc = payload["business_context"]
    ca = payload["commercial_action"]
    score = payload.get("score") or {}
    tags = payload.get("tags") or []

    decisores_md = "\n".join(
        f"- {dm.get('role', '?')} ({dm.get('area', '?')}) — {dm.get('reason', '')}"
        for dm in payload["decision_makers"]
    )

    description = f"""## Resumo
{payload["summary"]}

## Empresa
- Nome: {company.get("name")}
- Setor: {company.get("sector")}
- Região: {company.get("region") or "—"}
- Website: {company.get("website") or "—"}

## Evidência
- Tipo de sinal: {payload["signal_type"]}
- Fonte: {evidence.get("source_name")}
- URL: {evidence.get("url")}
- Publicado em: {evidence.get("published_at") or "—"}
- Capturado em: {evidence.get("captured_at")}
- Confiança: {evidence.get("confidence")}

## Contexto comercial
- Dor provável: {bc.get("pain_detected")}
- Gatilho: {bc.get("trigger")}
- Relevância para a CETEM: {bc.get("relevance_to_cetem")}
- Soluções CETEM relacionadas: {", ".join(bc.get("related_solutions") or [])}

## Decisores prováveis
{decisores_md}

## Score
- Fit: {score.get("fit", 0)}/25
- Urgência: {score.get("urgency", 0)}/25
- Valor: {score.get("business_value", 0)}/20
- Evidência: {score.get("evidence_strength", 0)}/15
- Acessibilidade: {score.get("accessibility", 0)}/15
- **Total: {score.get("total", 0)}/100**

## Próxima ação
- Prioridade: {ca.get("priority")}
- Owner sugerido: {ca.get("suggested_owner")}
- SLA: {ca.get("suggested_sla_hours", "?")} h
- Recomendação: {ca.get("recommended_next_step")}

## Tags
{" · ".join(tags)}

---
<!-- payload-manus-v0 -->
```json
{json.dumps(payload, indent=2, ensure_ascii=False)}
```
"""
    return {"title": title, "description": description}


# =============================================================
# Auth flow
# =============================================================


def get_password():
    """Le senha de env var; caso contrario, prompt interativo."""
    pw = os.environ.get("MANUS_TEST_PASSWORD")
    if pw:
        return pw
    if sys.stdin.isatty():
        return getpass.getpass(
            f"Senha do user {TEST_EMAIL} no staging "
            "(define MANUS_TEST_PASSWORD para evitar prompt): "
        )
    sys.exit(
        "ERRO: defina MANUS_TEST_PASSWORD no env ou rode em terminal interativo."
    )


def parse_jwt_sub(token):
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        decoded = base64.urlsafe_b64decode(payload_b64).decode()
        sub = json.loads(decoded).get("sub")
        return int(sub) if sub is not None else None
    except Exception:
        return None


def authenticate(log):
    password = get_password()

    log(f"[auth] tentando login como {TEST_EMAIL}")
    s, b = call("POST", "/api/v1/auth/login", {"email": TEST_EMAIL, "password": password})
    if s == 200 and isinstance(b, dict) and b.get("access_token"):
        token = b["access_token"]
        user_id = parse_jwt_sub(token)
        log(f"[auth] login OK (token: {mask_token(token)} | user_id: {user_id})")
        return token, user_id

    if s == 401:
        log("[auth] login retornou 401. Tentando cadastrar usuario novo no staging.")
        s2, b2 = call(
            "POST",
            "/api/v1/users",
            {"name": "Manus Integration Test", "email": TEST_EMAIL, "password": password},
        )
        if s2 == 201 and isinstance(b2, dict):
            user_id = b2.get("id")
            log(f"[auth] cadastrado (user_id={user_id}). Tentando login de novo.")
            s3, b3 = call(
                "POST",
                "/api/v1/auth/login",
                {"email": TEST_EMAIL, "password": password},
            )
            if s3 == 200 and isinstance(b3, dict) and b3.get("access_token"):
                token = b3["access_token"]
                log(f"[auth] login pos-cadastro OK (token: {mask_token(token)})")
                return token, user_id
            log(f"[auth] FALHA no login pos-cadastro: status={s3} body={b3}")
        elif s2 == 409:
            log(
                "[auth] usuario ja existe no staging mas senha nao bate. "
                "Defina MANUS_TEST_PASSWORD com a senha correta ou rode com email distinto "
                "(MANUS_TEST_EMAIL=manus-integration-test+novo@example.com)."
            )
        else:
            log(f"[auth] cadastro falhou: status={s2} body={b2}")

    sys.exit(1)


# =============================================================
# Main
# =============================================================


def main():
    log_buffer = []

    def log(msg=""):
        print(msg)
        log_buffer.append(msg)

    log("=" * 64)
    log(f"Smoke Manus -> API Cowork — {datetime.now(timezone.utc).isoformat()}")
    log(f"BASE_URL: {BASE_URL}")
    log(f"EXAMPLES_DIR: {EXAMPLES_DIR}")
    log("=" * 64)
    log("")

    # 1) GET / e GET /health
    log("[1] GET /")
    s, b = call("GET", "/")
    log(f"    status={s}  body={b}")

    log("[2] GET /health")
    s, b = call("GET", "/health")
    log(f"    status={s}  body={b}")
    log("")

    # 2) Carrega exemplos
    if not EXAMPLES_DIR.exists():
        log(f"ERRO: diretorio de exemplos nao encontrado: {EXAMPLES_DIR}")
        sys.exit(1)
    examples = sorted(EXAMPLES_DIR.glob("*.json"))
    if not examples:
        log("ERRO: nenhum exemplo .json em docs/manus-integration/examples/")
        sys.exit(1)
    log(f"[3] Carregando {len(examples)} payloads Manus de {EXAMPLES_DIR}")
    payloads = []
    for p in examples:
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
            validate_payload(payload)
            payloads.append((p.name, payload))
            log(f"    OK   {p.name}")
        except Exception as e:
            log(f"    SKIP {p.name}: {type(e).__name__}: {e}")
    if not payloads:
        log("ERRO: nenhum payload valido para enviar.")
        sys.exit(1)
    log("")

    # 3) Auth
    token, user_id = authenticate(log)
    log("")

    # 4) Cria 1 task por payload Manus
    log(f"[5] Criando {len(payloads)} tasks no staging para user_id={user_id}")
    created_titles = []
    for fname, payload in payloads:
        body = manus_to_task(payload)
        s, b = call(
            "POST",
            f"/api/v1/users/{user_id}/tasks",
            body,
            token=token,
        )
        if s == 201 and isinstance(b, dict):
            created_titles.append(b.get("title"))
            log(f"    [OK  ] {fname} -> task id={b.get('id')} title='{b.get('title')[:80]}...'")
        else:
            log(f"    [FAIL] {fname} status={s} body={b}")
    log("")

    # 5) Lista tasks e confirma
    log(f"[6] GET /api/v1/users/{user_id}/tasks")
    s, b = call("GET", f"/api/v1/users/{user_id}/tasks?limit=100", token=token)
    if s != 200 or not isinstance(b, list):
        log(f"    ERRO: status={s} body={b}")
        sys.exit(1)
    log(f"    Total de tasks visiveis: {len(b)}")

    visible_titles = {t.get("title") for t in b}
    confirmed = [t for t in created_titles if t in visible_titles]
    log(f"    Confirmadas {len(confirmed)}/{len(created_titles)} tasks recem-criadas na lista")

    # 6) Resumo
    log("")
    log("=" * 64)
    log("RESUMO")
    log("=" * 64)
    log(f"  Payloads carregados: {len(payloads)}")
    log(f"  Tasks criadas: {len(created_titles)}")
    log(f"  Tasks confirmadas no GET: {len(confirmed)}")
    veredito = (
        "STAGING VALIDADO PARA INTEGRACAO MANUS"
        if len(confirmed) == len(payloads)
        else "STAGING COM FALHAS - revisar log acima"
    )
    log(f"  VEREDITO: {veredito}")

    # Relatorio (a gitignore: ver .gitignore - scripts/smoke_manus_report.txt)
    REPORT_PATH.write_text("\n".join(log_buffer) + "\n", encoding="utf-8")
    log(f"  Relatorio: {REPORT_PATH}")

    sys.exit(0 if len(confirmed) == len(payloads) else 1)


if __name__ == "__main__":
    # Aviso de seguranca no stdout pra deixar explicito
    if "production" in BASE_URL or "api-de-coworking.onrender.com" in BASE_URL:
        print(
            "ERRO: BASE_URL parece apontar para producao. Abortando.",
            file=sys.stderr,
        )
        sys.exit(2)
    # Senha aleatoria local para uso interno se precisar gerar (nao versionado)
    _ = secrets.token_hex(8)  # noqa: F841 - placeholder pra futuras geracoes
    main()
