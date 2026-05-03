import type { Task } from "../services/api";
import type { ManusPayload } from "../services/manusParser";
import { MARKET_STATUSES, type MarketStatus } from "../services/marketStatus";

interface Props {
  task: Task;
  payload: ManusPayload;
  status: MarketStatus;
  onStatusChange: (taskId: number, status: MarketStatus) => void;
  onMarkCompleted: (taskId: number) => void;
  busy: boolean;
}

export const SIGNAL_LABELS: Record<string, string> = {
  opportunity: "Oportunidade",
  threat: "Ameaça",
  tender: "Edital",
  expansion: "Expansão",
  regulation: "Regulação",
  competitor_move: "Concorrente",
  technology_adoption: "Tecnologia",
  hiring_signal: "Contratação",
  investment: "Investimento",
  operational_pain: "Dor operacional",
};

export const PRIORITY_LABELS: Record<string, string> = {
  low: "Baixa",
  medium: "Média",
  high: "Alta",
  critical: "Crítica",
};

export function MarketCard({
  task,
  payload,
  status,
  onStatusChange,
  onMarkCompleted,
  busy,
}: Props) {
  const signalLabel = SIGNAL_LABELS[payload.signal_type] ?? payload.signal_type;
  const priorityKey = String(payload.commercial_action.priority);
  const priorityLabel = PRIORITY_LABELS[priorityKey] ?? priorityKey;

  return (
    <article
      className={`market-card mc-status-${status} mc-priority-${priorityKey}`}
    >
      <header className="mc-head">
        <span className={`mc-badge mc-signal mc-signal-${payload.signal_type}`}>
          {signalLabel}
        </span>
        <span className={`mc-badge mc-priority-${priorityKey}`}>
          {priorityLabel}
        </span>
        {payload.score?.total != null && (
          <span className="mc-badge mc-score" title="Score CETEM 0-100">
            Score {payload.score.total}/100
          </span>
        )}
        <span className="mc-id">#{task.id}</span>
      </header>

      <div className="mc-meta">
        <strong>{payload.company.name}</strong>
        {payload.company.sector && (
          <>
            <span className="mc-sep"> · </span>
            <span>{payload.company.sector}</span>
          </>
        )}
        {payload.company.region && (
          <>
            <span className="mc-sep"> · </span>
            <span>{payload.company.region}</span>
          </>
        )}
      </div>

      <h3 className="mc-title">{payload.title}</h3>
      <p className="mc-summary">{payload.summary}</p>

      <dl className="mc-detail">
        <dt>Confiança</dt>
        <dd>{payload.evidence.confidence}</dd>

        <dt>Fonte</dt>
        <dd>
          <a
            href={payload.evidence.url}
            target="_blank"
            rel="noreferrer noopener"
          >
            {payload.evidence.source_name}
          </a>
        </dd>

        <dt>Captura</dt>
        <dd>{payload.evidence.captured_at}</dd>

        <dt>Próxima ação</dt>
        <dd>{payload.commercial_action.recommended_next_step}</dd>

        <dt>Owner</dt>
        <dd>
          {payload.commercial_action.suggested_owner} · SLA{" "}
          {payload.commercial_action.suggested_sla_hours} h
        </dd>

        {payload.business_context.related_solutions.length > 0 && (
          <>
            <dt>Soluções CETEM</dt>
            <dd>{payload.business_context.related_solutions.join(", ")}</dd>
          </>
        )}
      </dl>

      <footer className="mc-foot">
        <label className="mc-status-label">
          Status:
          <select
            value={status}
            onChange={(e) =>
              onStatusChange(task.id, e.target.value as MarketStatus)
            }
            disabled={busy}
          >
            {MARKET_STATUSES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        {!task.completed ? (
          <button
            className="mc-mark-completed"
            onClick={() => onMarkCompleted(task.id)}
            disabled={busy}
            title="Marca a Task como completed=true via PATCH /api/v1/tasks/{id}"
          >
            Marcar concluída
          </button>
        ) : (
          <span className="mc-completed-flag">✓ Concluída</span>
        )}
      </footer>
    </article>
  );
}
