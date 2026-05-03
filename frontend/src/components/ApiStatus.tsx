import { useCallback, useEffect, useState } from "react";
import {
  getHealth,
  getRoot,
  type HealthInfo,
  type RootInfo,
} from "../services/api";

export function ApiStatus() {
  const [root, setRoot] = useState<RootInfo | null>(null);
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [r, h] = await Promise.all([getRoot(), getHealth()]);
      setRoot(r);
      setHealth(h);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <section>
      <div className="row">
        <h2>Status da API</h2>
        <button onClick={refresh} disabled={loading}>
          {loading ? "Carregando..." : "Recarregar"}
        </button>
      </div>

      {error && <p className="error">Erro: {error}</p>}

      <dl className="status">
        <dt>GET /</dt>
        <dd>
          {root
            ? `${root.name} — status: ${root.status}`
            : loading
              ? "..."
              : "(sem dados)"}
        </dd>

        <dt>GET /health</dt>
        <dd>
          {health
            ? `status: ${health.status}` +
              (health.environment ? ` · environment: ${health.environment}` : "") +
              (health.database ? ` · database: ${health.database}` : "")
            : loading
              ? "..."
              : "(sem dados)"}
        </dd>
      </dl>
    </section>
  );
}
