/**
 * Cliente HTTP da API Cowork (staging).
 *
 * - Base URL via VITE_API_BASE_URL (frontend/.env)
 * - Token JWT injetado via parametro `token`, nunca lido daqui de localStorage
 *   (a camada de UI decide como persiste; ver App.tsx)
 * - Erros virao como ApiError com status + mensagem amigavel + body original
 */

const RAW_BASE = import.meta.env.VITE_API_BASE_URL;
const BASE_URL = (RAW_BASE ?? "").replace(/\/+$/, "");

if (!BASE_URL) {
  // Aparece no console do browser. Nao quebra silenciosamente.
  // eslint-disable-next-line no-console
  console.error(
    "[api] VITE_API_BASE_URL nao definida. Crie frontend/.env a partir de frontend/.env.example.",
  );
}

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, message: string, body: unknown) {
    super(message);
    this.status = status;
    this.body = body;
    this.name = "ApiError";
  }
}

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
interface RequestOptions {
  method?: Method;
  body?: unknown;
  token?: string | null;
}

async function request<T = unknown>(
  path: string,
  opts: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, token } = opts;
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    // Falha de rede (CORS, DNS, offline). fetch lanca TypeError.
    const msg =
      err instanceof Error ? err.message : "Falha de rede desconhecida.";
    throw new ApiError(
      0,
      `Sem resposta da API: ${msg}. Confira VITE_API_BASE_URL e CORS no Render staging.`,
      null,
    );
  }

  const text = await res.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    throw new ApiError(res.status, friendlyMessage(res.status, data), data);
  }
  return data as T;
}

function friendlyMessage(status: number, body: unknown): string {
  const detail =
    body && typeof body === "object" && body !== null && "detail" in body
      ? String((body as { detail: unknown }).detail)
      : null;
  switch (status) {
    case 401:
      return detail ?? "Nao autenticado. Faca login novamente.";
    case 403:
      return detail ?? "Acesso negado para esta operacao.";
    case 404:
      return detail ?? "Recurso nao encontrado.";
    case 409:
      return detail ?? "Conflito (provavelmente email ja cadastrado).";
    case 422:
      return detail ?? "Dados invalidos.";
    case 429:
      return detail ?? "Muitas requisicoes. Espere alguns segundos.";
    case 500:
      return detail ?? "Erro interno na API.";
    case 502:
    case 503:
    case 504:
      return (
        detail ??
        "API indisponivel. Render free pode estar dormindo - aguarde ~30s e tente de novo."
      );
    default:
      return detail ?? `Erro HTTP ${status}.`;
  }
}

// =============================================================
// Tipos do dominio
// =============================================================

export interface RootInfo {
  name: string;
  status: string;
  health: string;
  docs: string;
}

export interface HealthInfo {
  status: string;
  app?: string;
  environment?: string;
  database?: string;
}

export interface User {
  id: number;
  name: string;
  email: string;
  is_active: boolean;
  role?: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token?: string; // staging atual (commit 44cef55) nao retorna isso
  token_type: string;
}

export interface Task {
  id: number;
  title: string;
  description: string | null;
  completed: boolean;
  user_id: number;
}

// =============================================================
// Endpoints
// =============================================================

export const getRoot = () => request<RootInfo>("/");

export const getHealth = () => request<HealthInfo>("/health");

export const createUser = (payload: {
  name: string;
  email: string;
  password: string;
}) => request<User>("/api/v1/users", { method: "POST", body: payload });

export const login = (payload: { email: string; password: string }) =>
  request<LoginResponse>("/api/v1/auth/login", {
    method: "POST",
    body: payload,
  });

export const refresh = (refreshToken: string) =>
  request<LoginResponse>("/api/v1/auth/refresh", {
    method: "POST",
    body: { refresh_token: refreshToken },
  });

/**
 * Retorna o user autenticado pelo JWT enviado em Authorization: Bearer.
 * Substitui o caminho antigo de decodificar o claim 'sub' do JWT manualmente.
 */
export const getMe = (token: string) =>
  request<User>("/api/v1/users/me", { token });

export const listTasks = (userId: number, token: string) =>
  request<Task[]>(`/api/v1/users/${userId}/tasks`, { token });

export const createTask = (
  userId: number,
  payload: { title: string; description?: string },
  token: string,
) =>
  request<Task>(`/api/v1/users/${userId}/tasks`, {
    method: "POST",
    body: payload,
    token,
  });

// =============================================================
// Util: extrai 'sub' do JWT (id do user) sem validar assinatura.
//
// @deprecated O App.tsx agora usa getMe() (GET /api/v1/users/me) em vez
// de decodificar o JWT manualmente. Mantida exportada para debug e
// para clientes externos que ainda nao migraram.
// =============================================================

export function parseJwtSub(token: string): number | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = payload + "=".repeat((4 - (payload.length % 4)) % 4);
    const json = atob(padded);
    const data = JSON.parse(json) as { sub?: string | number };
    if (data.sub == null) return null;
    const n = typeof data.sub === "number" ? data.sub : Number(data.sub);
    return Number.isFinite(n) ? n : null;
  } catch {
    return null;
  }
}

export { BASE_URL };
