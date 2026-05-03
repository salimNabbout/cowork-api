import { useState } from "react";

interface Props {
  busy: boolean;
  error: string | null;
  onLogin: (p: { email: string; password: string }) => void | Promise<void>;
  onRegister: (p: {
    name: string;
    email: string;
    password: string;
  }) => void | Promise<void>;
}

export function AuthForm({ busy, error, onLogin, onRegister }: Props) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (mode === "login") onLogin({ email, password });
    else onRegister({ name, email, password });
  }

  return (
    <div>
      <div className="tabs">
        <button
          type="button"
          aria-pressed={mode === "login"}
          onClick={() => setMode("login")}
          disabled={busy}
        >
          Login
        </button>
        <button
          type="button"
          aria-pressed={mode === "register"}
          onClick={() => setMode("register")}
          disabled={busy}
        >
          Cadastrar
        </button>
      </div>

      <form onSubmit={submit}>
        {mode === "register" && (
          <label>
            Nome
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              disabled={busy}
            />
          </label>
        )}

        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={busy}
            autoComplete="email"
          />
        </label>

        <label>
          Senha
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={busy}
            autoComplete={
              mode === "register" ? "new-password" : "current-password"
            }
          />
        </label>

        <button type="submit" disabled={busy}>
          {busy
            ? "Aguarde..."
            : mode === "login"
              ? "Entrar"
              : "Cadastrar e entrar"}
        </button>
      </form>

      {error && <p className="error">Erro: {error}</p>}
    </div>
  );
}
