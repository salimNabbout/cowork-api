import { useCallback, useEffect, useState } from "react";
import { ApiStatus } from "./components/ApiStatus";
import { AuthForm } from "./components/AuthForm";
import { TasksPanel } from "./components/TasksPanel";
import {
  ApiError,
  BASE_URL,
  createTask,
  createUser,
  listTasks,
  login,
  parseJwtSub,
  type Task,
} from "./services/api";

/**
 * Persistencia do access_token: localStorage.
 *
 * Por que localStorage e nao memoria:
 *   - sobrevive a F5/recarregar a aba (UX melhor para validar staging)
 *   - simples, sem state global, sem cookies
 *
 * Risco conhecido (XSS):
 *   - se um script malicioso conseguir rodar JS nesta origin (ex: stored
 *     XSS via task.title nao sanitizada), ele consegue ler o token e
 *     fazer requests em nome do usuario.
 *   - mitigacoes nesta versao: todos os textos sao renderizados via
 *     React (auto-escape), nenhum dangerouslySetInnerHTML, nenhum
 *     script de terceiros.
 *   - blast radius: token expira em 30 min (ACCESS_TOKEN_EXPIRE_MINUTES
 *     do backend), entao o roubo tem janela curta.
 *
 * O que seria melhor (fora do escopo desta etapa):
 *   - backend setar httpOnly + Secure + SameSite=Strict cookie no login,
 *     frontend nao toca no token, browser anexa em todo request.
 *   - exige mudanca no backend (criar endpoint que set-cookie em vez de
 *     retornar token no body) - explicitamente fora do escopo agora.
 *
 * Refresh token: a versao atual do staging (commit 44cef55) nao retorna
 * refresh_token no /api/v1/auth/login, entao nao salvamos. Quando a
 * branch atual for promovida para staging, podemos guardar o refresh
 * token tambem - com os mesmos cuidados.
 */
const TOKEN_KEY = "cowork_access_token";
const USER_ID_KEY = "cowork_user_id";

function loadSession(): { token: string | null; userId: number | null } {
  return {
    token: localStorage.getItem(TOKEN_KEY),
    userId: localStorage.getItem(USER_ID_KEY)
      ? Number(localStorage.getItem(USER_ID_KEY))
      : null,
  };
}
function saveSession(token: string, userId: number) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_ID_KEY, String(userId));
}
function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_ID_KEY);
}

export default function App() {
  const initial = loadSession();
  const [token, setToken] = useState<string | null>(initial.token);
  const [userId, setUserId] = useState<number | null>(initial.userId);

  const [tasks, setTasks] = useState<Task[]>([]);
  const [tasksError, setTasksError] = useState<string | null>(null);
  const [tasksBusy, setTasksBusy] = useState(false);

  const [authError, setAuthError] = useState<string | null>(null);
  const [authBusy, setAuthBusy] = useState(false);

  const handleLogout = useCallback(() => {
    clearSession();
    setToken(null);
    setUserId(null);
    setTasks([]);
    setTasksError(null);
    setAuthError(null);
  }, []);

  const refreshTasks = useCallback(async () => {
    if (!token || !userId) return;
    setTasksBusy(true);
    setTasksError(null);
    try {
      const list = await listTasks(userId, token);
      setTasks(list);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setTasksError(msg);
      if (e instanceof ApiError && e.status === 401) {
        // token expirou ou invalido - desloga
        handleLogout();
      }
    } finally {
      setTasksBusy(false);
    }
  }, [token, userId, handleLogout]);

  useEffect(() => {
    if (token && userId) refreshTasks();
  }, [token, userId, refreshTasks]);

  async function handleRegister(payload: {
    name: string;
    email: string;
    password: string;
  }) {
    setAuthError(null);
    setAuthBusy(true);
    try {
      const user = await createUser(payload);
      // Auto-login depois do cadastro - menos clique no fluxo de validacao
      const lr = await login({
        email: payload.email,
        password: payload.password,
      });
      saveSession(lr.access_token, user.id);
      setToken(lr.access_token);
      setUserId(user.id);
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : String(e));
    } finally {
      setAuthBusy(false);
    }
  }

  async function handleLogin(payload: { email: string; password: string }) {
    setAuthError(null);
    setAuthBusy(true);
    try {
      const lr = await login(payload);
      const sub = parseJwtSub(lr.access_token);
      if (sub === null) {
        throw new Error(
          "Login OK mas nao consegui extrair user id do token (sub ausente).",
        );
      }
      saveSession(lr.access_token, sub);
      setToken(lr.access_token);
      setUserId(sub);
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : String(e));
    } finally {
      setAuthBusy(false);
    }
  }

  async function handleCreateTask(payload: {
    title: string;
    description?: string;
  }) {
    if (!token || !userId) return;
    setTasksError(null);
    setTasksBusy(true);
    try {
      const t = await createTask(userId, payload, token);
      setTasks((prev) => [...prev, t]);
    } catch (e) {
      setTasksError(e instanceof Error ? e.message : String(e));
      if (e instanceof ApiError && e.status === 401) handleLogout();
    } finally {
      setTasksBusy(false);
    }
  }

  return (
    <div className="container">
      <header>
        <h1>Cowork API — frontend de validacao</h1>
        <p className="env-note">
          Apontando para <code>{BASE_URL || "(VITE_API_BASE_URL nao definida)"}</code>
        </p>
      </header>

      <ApiStatus />

      <section>
        <h2>Autenticacao</h2>
        {token && userId ? (
          <div className="auth-logged">
            <p>
              Logado como <strong>user id {userId}</strong> · token salvo em
              localStorage (token expira em ~30 min).
            </p>
            <button onClick={handleLogout}>Logout</button>
          </div>
        ) : (
          <AuthForm
            busy={authBusy}
            error={authError}
            onLogin={handleLogin}
            onRegister={handleRegister}
          />
        )}
      </section>

      {token && userId && (
        <TasksPanel
          tasks={tasks}
          busy={tasksBusy}
          error={tasksError}
          onCreate={handleCreateTask}
          onRefresh={refreshTasks}
        />
      )}

      <footer>
        <p>
          Frontend de validacao apontando <strong>somente para staging</strong>.
          Nao usar contra producao.
        </p>
      </footer>
    </div>
  );
}
