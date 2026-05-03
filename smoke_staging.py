#!/usr/bin/env python3
"""
Smoke test do staging da Cowork API.

Roda 7 verificacoes contra o servico de staging no Render, mascara
tokens nos logs e salva um relatorio em smoke_staging_report.txt.

Sem dependencias externas - so a stdlib do Python 3.

Como rodar:
    python smoke_staging.py

Saida no terminal e em smoke_staging_report.txt (mesmo conteudo).
NAO armazena tokens reais nem senhas no relatorio.
"""

import base64
import json
import secrets as secrets_mod
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

BASE_URL = "https://api-de-coworking-staging.onrender.com"
TIMEOUT = 60  # Render free dorme apos 15 min - cold start pode levar ate ~50s
REPORT_PATH = "smoke_staging_report.txt"
# Senha de teste descartavel - so existe na execucao deste script.
TEST_PASSWORD = "smoke-staging-pass-" + secrets_mod.token_hex(4)


def mask_token(t):
    if not t or not isinstance(t, str) or len(t) < 12:
        return "(ausente)"
    return f"{t[:3]}...{t[-4:]}"


def jwt_inspect(t):
    """Decodifica o payload do JWT sem validar assinatura - so para debug."""
    if not t or not isinstance(t, str):
        return {"error": "token vazio"}
    try:
        parts = t.split(".")
        if len(parts) != 3:
            return {"error": "nao parece JWT (3 partes)"}
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        decoded = base64.urlsafe_b64decode(payload).decode()
        data = json.loads(decoded)
        return {
            "type": data.get("type"),
            "sub": data.get("sub"),
            "exp": data.get("exp"),
            "iat": data.get("iat"),
        }
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def call(method, path, body=None, token=None):
    url = BASE_URL + path
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            status = resp.status
            raw = resp.read()
    except urllib.error.HTTPError as e:
        status = e.code
        raw = e.read()
    except (urllib.error.URLError, TimeoutError) as e:
        return None, f"NETWORK_ERROR: {type(e).__name__}: {e}"
    try:
        return status, json.loads(raw) if raw else None
    except Exception:
        return status, raw.decode(errors="replace")


def log(line=""):
    print(line)
    log.buf.append(line)


log.buf = []


def save_report():
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(log.buf) + "\n")


def main():
    started = datetime.now(timezone.utc).isoformat()
    log("=" * 64)
    log(f"Smoke test staging Cowork API - {started}")
    log(f"BASE_URL: {BASE_URL}")
    log("Render free pode demorar no primeiro request (cold start ~30-50s).")
    log("=" * 64)
    log("")

    results = []

    # 1) GET /
    log("[1] GET /")
    s, b = call("GET", "/")
    log(f"    status={s}")
    log(f"    body={b}")
    results.append(("GET /", s == 200))

    # 2) GET /health
    log("[2] GET /health")
    s, b = call("GET", "/health")
    log(f"    status={s}")
    log(f"    body={b}")
    health_ok = s == 200 and isinstance(b, dict) and b.get("status") == "ok"
    if isinstance(b, dict):
        log(f"    environment={b.get('environment')!r} database={b.get('database')!r}")
    results.append(("GET /health", health_ok))

    # 3) GET /docs
    log("[3] GET /docs")
    s, _ = call("GET", "/docs")
    log(f"    status={s}")
    results.append(("GET /docs", s == 200))

    # 4) POST /api/v1/users
    suffix = secrets_mod.token_hex(4)
    email = f"smoke-{suffix}@example.com"
    log(f"[4] POST /api/v1/users  email={email}  (senha gerada localmente, nao salva)")
    s, b = call(
        "POST",
        "/api/v1/users",
        {"name": "smoke", "email": email, "password": TEST_PASSWORD},
    )
    log(f"    status={s}")
    log(f"    body={b}")
    user_id = b.get("id") if isinstance(b, dict) else None
    results.append(("POST /api/v1/users", s == 201 and user_id is not None))
    if not user_id:
        log("ERRO: cadastro falhou - abortando smoke.")
        save_report()
        sys.exit(1)
    log(f"    USER_ID={user_id}")
    log("")

    # 5) POST /api/v1/auth/login
    log(f"[5] POST /api/v1/auth/login  email={email}")
    s, b = call(
        "POST", "/api/v1/auth/login", {"email": email, "password": TEST_PASSWORD}
    )
    log(f"    status={s}")
    if isinstance(b, dict):
        # Mascara apenas chaves que TERMINAM com "_token" (access_token,
        # refresh_token). Nao mascara token_type (que termina em _type).
        b_masked = {
            k: (mask_token(v) if k.endswith("_token") else v) for k, v in b.items()
        }
    else:
        b_masked = b
    log(f"    body (mascarado)={b_masked}")
    access = b.get("access_token") if isinstance(b, dict) else None
    refresh = b.get("refresh_token") if isinstance(b, dict) else None
    log(f"    access_token: {mask_token(access)}")
    log(f"    refresh_token: {mask_token(refresh)}")
    if access:
        log(f"    access  payload (claims): {jwt_inspect(access)}")
    if refresh:
        log(f"    refresh payload (claims): {jwt_inspect(refresh)}")
    results.append(("POST /api/v1/auth/login", s == 200 and access is not None))
    if not access:
        log("ERRO: login nao retornou access_token - abortando smoke.")
        save_report()
        sys.exit(1)
    log("")

    # 6) GET /api/v1/users/{id}/tasks  SEM token  (espera 401)
    log(f"[6] GET /api/v1/users/{user_id}/tasks  SEM token (espera 401)")
    s, b = call("GET", f"/api/v1/users/{user_id}/tasks")
    log(f"    status={s}")
    log(f"    body={b}")
    results.append(("GET tasks sem token = 401", s == 401))
    log("")

    # 7) POST /api/v1/users/{id}/tasks  COM Bearer access_token
    log(f"[7] POST /api/v1/users/{user_id}/tasks  COM Bearer (access_token)")
    s, b = call(
        "POST",
        f"/api/v1/users/{user_id}/tasks",
        {"title": "smoke task em staging"},
        token=access,
    )
    log(f"    status={s}")
    log(f"    body={b}")
    results.append(("POST task com token", s == 201))
    log("")

    # 8) GET /api/v1/users/{id}/tasks  COM Bearer access_token
    log(f"[8] GET /api/v1/users/{user_id}/tasks  COM Bearer (access_token)")
    s, b = call("GET", f"/api/v1/users/{user_id}/tasks", token=access)
    log(f"    status={s}")
    log(f"    body={b}")
    list_ok = s == 200 and (
        isinstance(b, list) or (isinstance(b, dict) and "items" in b)
    )
    results.append(("GET tasks com token", list_ok))
    log("")

    # Diagnostico - se 7 ou 8 falharam, tentar rota legada e refresh-as-access
    last_two_ok = results[-2][1] and results[-1][1]
    if not last_two_ok:
        log("")
        log("=" * 64)
        log("DIAGNOSTICO - tentativas adicionais")
        log("=" * 64)

        log(f"[D1] POST /users/{user_id}/tasks  rota LEGADA com access_token")
        s, b = call(
            "POST",
            f"/users/{user_id}/tasks",
            {"title": "smoke legada"},
            token=access,
        )
        log(f"     status={s}  body={b}")

        log(f"[D2] GET /users/{user_id}/tasks  rota LEGADA com access_token")
        s, b = call("GET", f"/users/{user_id}/tasks", token=access)
        log(f"     status={s}  body={b}")

        if refresh:
            log(f"[D3] GET /api/v1/users/{user_id}/tasks  COM REFRESH (espera 401)")
            s, b = call("GET", f"/api/v1/users/{user_id}/tasks", token=refresh)
            log(f"     status={s}  body={b}  (refresh nao deve servir como access)")

        log("")
        log("Pistas:")
        log("- 401 'Could not validate credentials' = SECRET_KEY divergente, "
            "tipo de token errado, ou JWT malformado.")
        log("- Se /users/{id}/tasks legada funciona mas /api/v1/... nao, "
            "ha discrepancia de mount no main.py.")
        log("- jwt_inspect mostra 'type': 'access' para access_token. "
            "Se vier 'refresh', troca de variavel.")
        log("- Conferir Render -> Environment -> SECRET_KEY existe e nao mudou "
            "entre login e POST de task.")

    log("")
    log("=" * 64)
    log("RESUMO")
    log("=" * 64)
    all_ok = True
    for name, ok in results:
        marker = "OK  " if ok else "FAIL"
        log(f"  [{marker}] {name}")
        all_ok = all_ok and ok
    log("")
    log("VEREDITO: " + ("STAGING VALIDADO" if all_ok else "STAGING COM FALHAS"))
    save_report()
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
