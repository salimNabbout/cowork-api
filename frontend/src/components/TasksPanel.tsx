import { useState } from "react";
import type { Task } from "../services/api";

interface Props {
  tasks: Task[];
  busy: boolean;
  error: string | null;
  onCreate: (p: { title: string; description?: string }) => void | Promise<void>;
  onRefresh: () => void | Promise<void>;
}

export function TasksPanel({ tasks, busy, error, onCreate, onRefresh }: Props) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    await onCreate({
      title: title.trim(),
      description: description.trim() || undefined,
    });
    setTitle("");
    setDescription("");
  }

  return (
    <section>
      <div className="row">
        <h2>Tasks</h2>
        <button onClick={onRefresh} disabled={busy}>
          {busy ? "Carregando..." : "Recarregar"}
        </button>
      </div>

      <form onSubmit={submit}>
        <label>
          Titulo
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            disabled={busy}
            placeholder="Ex.: validar staging"
          />
        </label>
        <label>
          Descricao (opcional)
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={busy}
          />
        </label>
        <button type="submit" disabled={busy || !title.trim()}>
          Criar task
        </button>
      </form>

      {error && <p className="error">Erro: {error}</p>}

      {tasks.length === 0 ? (
        <p className="muted">Nenhuma task ainda.</p>
      ) : (
        <ul className="tasks">
          {tasks.map((t) => (
            <li key={t.id}>
              <strong>#{t.id}</strong> {t.title}
              {t.description ? ` — ${t.description}` : ""}
              {t.completed ? " ✓" : ""}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
