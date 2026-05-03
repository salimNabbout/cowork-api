import { useMemo, useState } from "react";
import type { Task } from "../services/api";
import { parseManusPayload, type ManusPayload } from "../services/manusParser";
import type { MarketStatus } from "../services/marketStatus";
import { MarketCard, SIGNAL_LABELS, PRIORITY_LABELS } from "./MarketCard";

interface Parsed {
  task: Task;
  payload: ManusPayload;
}

interface Props {
  tasks: Task[];
  statuses: Record<number, MarketStatus>;
  onStatusChange: (taskId: number, status: MarketStatus) => void;
  onMarkCompleted: (taskId: number) => void;
  onRefresh: () => void;
  busy: boolean;
  error: string | null;
}

export function MarketIntelligencePanel({
  tasks,
  statuses,
  onStatusChange,
  onMarkCompleted,
  onRefresh,
  busy,
  error,
}: Props) {
  const parsed = useMemo<Parsed[]>(
    () =>
      tasks
        .map((t) => ({ task: t, payload: parseManusPayload(t.description) }))
        .filter((x): x is Parsed => x.payload !== null),
    [tasks],
  );

  const [signalType, setSignalType] = useState<string>("all");
  const [priority, setPriority] = useState<string>("all");
  const [sector, setSector] = useState<string>("all");
  const [text, setText] = useState<string>("");

  const sectors = useMemo(() => {
    const set = new Set<string>();
    parsed.forEach(
      (p) => p.payload.company.sector && set.add(p.payload.company.sector),
    );
    return Array.from(set).sort();
  }, [parsed]);

  const filtered = useMemo(() => {
    const q = text.trim().toLowerCase();
    return parsed.filter(({ payload }) => {
      if (signalType !== "all" && payload.signal_type !== signalType)
        return false;
      if (priority !== "all" && payload.commercial_action.priority !== priority)
        return false;
      if (sector !== "all" && payload.company.sector !== sector) return false;
      if (q) {
        const hay = (
          payload.title +
          " " +
          payload.summary +
          " " +
          payload.company.name +
          " " +
          (payload.tags || []).join(" ")
        ).toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [parsed, signalType, priority, sector, text]);

  const counts = useMemo(() => {
    const out = {
      total: parsed.length,
      opportunity: 0,
      threat: 0,
      regulatory: 0,
      high_priority: 0,
      pendentes: 0,
    };
    parsed.forEach(({ payload, task }) => {
      if (payload.signal_type === "opportunity") out.opportunity++;
      if (payload.signal_type === "threat" || payload.signal_type === "competitor_move")
        out.threat++;
      if (payload.signal_type === "tender" || payload.signal_type === "regulation")
        out.regulatory++;
      const prio = payload.commercial_action.priority;
      if (prio === "high" || prio === "critical") out.high_priority++;
      const st = statuses[task.id] ?? "novo";
      if (st === "novo" || st === "em_analise") out.pendentes++;
    });
    return out;
  }, [parsed, statuses]);

  return (
    <section className="mi-panel">
      <div className="row">
        <h2>Inteligência de Mercado</h2>
        <button onClick={onRefresh} disabled={busy}>
          {busy ? "Carregando..." : "Recarregar"}
        </button>
      </div>

      <div className="mi-summary">
        <div className="mi-stat">
          <span className="mi-stat-num">{counts.total}</span>
          <span className="mi-stat-lbl">sinais Manus</span>
        </div>
        <div className="mi-stat">
          <span className="mi-stat-num">{counts.opportunity}</span>
          <span className="mi-stat-lbl">oportunidades</span>
        </div>
        <div className="mi-stat">
          <span className="mi-stat-num">{counts.threat}</span>
          <span className="mi-stat-lbl">ameaças/concorrentes</span>
        </div>
        <div className="mi-stat">
          <span className="mi-stat-num">{counts.regulatory}</span>
          <span className="mi-stat-lbl">editais/regulações</span>
        </div>
        <div className="mi-stat mi-stat-warn">
          <span className="mi-stat-num">{counts.high_priority}</span>
          <span className="mi-stat-lbl">alta prioridade</span>
        </div>
        <div className="mi-stat mi-stat-warn">
          <span className="mi-stat-num">{counts.pendentes}</span>
          <span className="mi-stat-lbl">pendentes de análise</span>
        </div>
      </div>

      <div className="mi-filters">
        <label>
          <span>Tipo</span>
          <select
            value={signalType}
            onChange={(e) => setSignalType(e.target.value)}
          >
            <option value="all">Todos</option>
            {Object.entries(SIGNAL_LABELS).map(([k, l]) => (
              <option key={k} value={k}>
                {l}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Prioridade</span>
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
          >
            <option value="all">Todas</option>
            {Object.entries(PRIORITY_LABELS).map(([k, l]) => (
              <option key={k} value={k}>
                {l}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Setor</span>
          <select value={sector} onChange={(e) => setSector(e.target.value)}>
            <option value="all">Todos</option>
            {sectors.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="mi-search">
          <span>Buscar</span>
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="empresa, palavra-chave, tag..."
          />
        </label>
      </div>

      {error && <p className="error">Erro: {error}</p>}

      {filtered.length === 0 ? (
        <p className="muted">
          {parsed.length === 0
            ? "Nenhum sinal Manus encontrado. Crie tasks via scripts/smoke_manus_market_intelligence.py ou via POST /api/v1/users/{id}/tasks com payload Manus serializado."
            : "Nenhum sinal corresponde aos filtros aplicados."}
        </p>
      ) : (
        <div className="market-cards">
          {filtered.map(({ task, payload }) => (
            <MarketCard
              key={task.id}
              task={task}
              payload={payload}
              status={statuses[task.id] ?? "novo"}
              onStatusChange={onStatusChange}
              onMarkCompleted={onMarkCompleted}
              busy={busy}
            />
          ))}
        </div>
      )}
    </section>
  );
}
