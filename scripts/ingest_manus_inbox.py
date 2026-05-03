#!/usr/bin/env python3
"""
Ingestão Padrão A — pega JSONs do Manus em manus_inbox/, valida,
faz POST em /api/v1/users/{id}/tasks no staging, move processados.

USO (Windows CMD):

    cd C:\\Users\\salim\\projetos\\cowork-api
    set MANUS_TEST_EMAIL=manus-integration-test+v1@example.com
    set MANUS_TEST_PASSWORD=<senha-do-user-de-integracao>
    python scripts/ingest_manus_inbox.py

USO (PowerShell):

    cd C:\\Users\\salim\\projetos\\cowork-api
    $env:MANUS_TEST_EMAIL = "manus-integration-test+v1@example.com"
    $env:MANUS_TEST_PASSWORD = "<senha>"
    python scripts/ingest_manus_inbox.py

REGRAS:

- Lê APENAS *.json no top-level de manus_inbox/ (NAO desce em processed/ ou reports/)
- Reusa validate_payload + manus_to_task de smoke_manus_market_intelligence.py,
  que sao a implementacao canonica do contrato (ver docs/manus-integration/contract.md)
- 201 -> move arquivo para manus_inbox/processed/YYYY-MM-DD/
- 4xx (excluindo 401) -> deixa no inbox (analista decide se conserta ou descarta)
- 401 -> ABORTA o lote (token invalido / senha errada)
- 5xx ou network -> deixa no inbox para retry no proximo run
- Senha lida de env (MANUS_TEST_PASSWORD) ou prompt interativo
- Token mascarado nos logs; senha nunca aparece
- Idempotencia: a API hoje NAO dedupe. Cada run que ache o mesmo JSON cria
  uma task nova. Cuide pra nao colocar o mesmo arquivo duas vezes (move-se
  pra processed/ apos 201, entao se voce nao copiar dois iguais, nao duplica).

NAO armazena tokens, senhas ou DATABASE_URL em arquivo.
"""

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from smoke_manus_market_intelligence import (  # noqa: E402
    BASE_URL,
    TEST_EMAIL,
    call,
    get_password,
    manus_to_task,
    mask_token,
    parse_jwt_sub,
    validate_payload,
)

PROJECT_ROOT = SCRIPTS_DIR.parent
INBOX = PROJECT_ROOT / "manus_inbox"
PROCESSED_ROOT = INBOX / "processed"
REPORT_DIR = INBOX / "reports"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def main() -> int:
    # Salvaguarda: nunca apontar pra producao
    if "production" in BASE_URL or "api-de-coworking.onrender.com" in BASE_URL:
        print(
            "ERRO: BASE_URL parece producao. Aborta para nao poluir banco real.",
            file=sys.stderr,
        )
        return 2

    if not INBOX.exists():
        print(f"ERRO: pasta {INBOX} nao existe. Crie a pasta antes.", file=sys.stderr)
        return 1

    files = sorted([p for p in INBOX.glob("*.json") if p.is_file()])
    if not files:
        print(f"Nada a processar em {INBOX}/*.json")
        return 0
    print(f"Encontrados {len(files)} arquivo(s) JSON em {INBOX}")

    # Auth
    print(f"[auth] login como {TEST_EMAIL}")
    password = get_password()
    s, b = call(
        "POST",
        "/api/v1/auth/login",
        {"email": TEST_EMAIL, "password": password},
    )
    if s != 200 or not isinstance(b, dict) or not b.get("access_token"):
        print(f"[auth] FALHA: status={s} body={b}", file=sys.stderr)
        print(
            "Confira email e senha. O user de integracao precisa existir "
            "no staging com a senha que esta na env MANUS_TEST_PASSWORD.",
            file=sys.stderr,
        )
        return 1
    token = b["access_token"]
    user_id = parse_jwt_sub(token)
    if not user_id:
        print("[auth] FALHA: nao consegui extrair user_id do token", file=sys.stderr)
        return 1
    print(f"[auth] OK token={mask_token(token)} user_id={user_id}")

    # Setup pastas
    today_dir = PROCESSED_ROOT / _utc_today()
    today_dir.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Processa
    log: list[str] = []
    log.append(f"=== Ingest Manus inbox {_utc_now_iso()} ===")
    log.append(f"BASE_URL: {BASE_URL}")
    log.append(f"USER_ID: {user_id}")
    log.append(f"Inbox: {INBOX}")
    log.append(f"Arquivos encontrados: {len(files)}")
    log.append("")

    success = 0
    invalid = 0
    failed_4xx = 0
    failed_5xx = 0
    aborted = False

    for path in files:
        log.append(f"--- {path.name} ---")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            log.append(f"  [INVALID] JSON malformado: {e}")
            invalid += 1
            continue
        try:
            validate_payload(payload)
            body = manus_to_task(payload)
        except (ValueError, KeyError, TypeError) as e:
            log.append(f"  [INVALID] payload nao bate com contract.md: {e}")
            invalid += 1
            continue

        s, resp = call(
            "POST",
            f"/api/v1/users/{user_id}/tasks",
            body,
            token=token,
        )
        if s == 201 and isinstance(resp, dict):
            tid = resp.get("id")
            t_title = str(resp.get("title", ""))[:80]
            log.append(f"  [OK 201] task_id={tid} title={t_title!r}")
            try:
                shutil.move(str(path), str(today_dir / path.name))
            except OSError as e:
                log.append(f"  [WARN] Task criada mas falhou ao mover arquivo: {e}")
            success += 1
        elif s == 401:
            log.append("  [AUTH 401] token rejeitado. Abortando o lote.")
            log.append(f"  body: {resp}")
            aborted = True
            break
        elif 400 <= s < 500:
            log.append(
                f"  [HTTP {s}] body: {resp} -- arquivo permanece no inbox"
            )
            failed_4xx += 1
        else:
            log.append(
                f"  [HTTP {s}] (5xx/network) body: {resp} -- "
                f"mantido para retry no proximo run"
            )
            failed_5xx += 1

    log.append("")
    log.append("=" * 60)
    log.append("RESUMO")
    log.append("=" * 60)
    log.append(f"  Total processado: {len(files)}")
    log.append(f"  Sucesso (201): {success}")
    log.append(f"  Invalidos (validacao): {invalid}")
    log.append(f"  Falhas 4xx: {failed_4xx}")
    log.append(f"  Falhas 5xx/network: {failed_5xx}")
    if aborted:
        log.append("  ABORTADO no meio do lote (auth)")
    log.append(
        f"  Pendentes no inbox: {invalid + failed_4xx + failed_5xx}"
    )

    report_path = REPORT_DIR / f"{_utc_compact()}.txt"
    report_path.write_text("\n".join(log) + "\n", encoding="utf-8")
    log.append(f"  Relatorio: {report_path}")

    for line in log:
        print(line)

    if invalid + failed_4xx + failed_5xx > 0 or aborted:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
