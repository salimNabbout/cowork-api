/**
 * Status operacional do sinal Manus, por enquanto armazenado em
 * localStorage do browser (client-side overlay sobre Task).
 *
 * Quando a entidade MarketInsight for criada no backend, este arquivo
 * vira um wrapper de chamadas a API e pode ser removido. Por hora, o
 * piloto opera com este overlay para nao bloquear o fluxo na ausencia
 * de campos estruturados no Task.
 *
 * Trade-off conhecido: status nao trafega entre maquinas/usuarios.
 * Cada usuario CETEM tem sua propria visao de status. Aceitavel para
 * o piloto enquanto o time alinha workflow.
 */

export type MarketStatus =
  | "novo"
  | "em_analise"
  | "aprovado"
  | "descartado"
  | "convertido";

export const MARKET_STATUSES: { value: MarketStatus; label: string }[] = [
  { value: "novo", label: "Novo" },
  { value: "em_analise", label: "Em análise" },
  { value: "aprovado", label: "Aprovado" },
  { value: "descartado", label: "Descartado" },
  { value: "convertido", label: "Convertido em oportunidade" },
];

const STORAGE_KEY = "cowork_market_status_v1";

export function loadAllStatuses(): Record<number, MarketStatus> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (typeof parsed === "object" && parsed !== null) {
      return parsed as Record<number, MarketStatus>;
    }
    return {};
  } catch {
    return {};
  }
}

export function saveAllStatuses(map: Record<number, MarketStatus>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  } catch {
    // localStorage cheio ou bloqueado - degrada silenciosamente
  }
}

export function statusFor(
  map: Record<number, MarketStatus>,
  taskId: number,
): MarketStatus {
  return map[taskId] ?? "novo";
}
