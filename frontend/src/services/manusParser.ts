/**
 * Reconstroi o payload Manus original a partir do Task.description que
 * foi serializado por scripts/smoke_manus_market_intelligence.py.
 *
 * Formato esperado da description (ver docs/manus-integration/mapping.md):
 *
 *   ## Resumo
 *   ...
 *   ## Tags
 *   ...
 *
 *   ---
 *   <!-- payload-manus-v0 -->
 *   ```json
 *   { "source": "manus", ... }
 *   ```
 *
 * Retorna null se a task NAO for um sinal Manus (sem o marcador) ou
 * se o JSON estiver malformado.
 */

export type ManusSignalType =
  | "opportunity"
  | "threat"
  | "tender"
  | "expansion"
  | "regulation"
  | "competitor_move"
  | "technology_adoption"
  | "hiring_signal"
  | "investment"
  | "operational_pain"
  | string; // permite tipos novos sem quebrar o cliente

export type ManusPriority = "low" | "medium" | "high" | "critical" | string;

export type ManusConfidence = "low" | "medium" | "high" | string;

export interface ManusCompany {
  name: string;
  website: string | null;
  sector: string;
  region: string | null;
}

export interface ManusEvidence {
  url: string;
  source_name: string;
  published_at: string | null;
  captured_at: string;
  confidence: ManusConfidence;
}

export interface ManusBusinessContext {
  pain_detected: string;
  trigger: string;
  relevance_to_cetem: string;
  related_solutions: string[];
}

export interface ManusCommercialAction {
  priority: ManusPriority;
  recommended_next_step: string;
  suggested_owner: string;
  suggested_sla_hours: number;
}

export interface ManusDecisionMaker {
  role: string;
  area: string;
  reason: string;
}

export interface ManusScore {
  fit?: number;
  urgency?: number;
  business_value?: number;
  evidence_strength?: number;
  accessibility?: number;
  total?: number;
}

export interface ManusPayload {
  source: string;
  signal_type: ManusSignalType;
  title: string;
  summary: string;
  company: ManusCompany;
  evidence: ManusEvidence;
  business_context: ManusBusinessContext;
  commercial_action: ManusCommercialAction;
  decision_makers: ManusDecisionMaker[];
  score?: ManusScore;
  tags: string[];
}

const MARKER = "<!-- payload-manus-v0 -->";
const JSON_BLOCK_RE = /```json\s*([\s\S]*?)\s*```/;

export function parseManusPayload(
  description: string | null | undefined,
): ManusPayload | null {
  if (!description) return null;
  const idx = description.indexOf(MARKER);
  if (idx === -1) return null;
  const after = description.slice(idx + MARKER.length);
  const match = after.match(JSON_BLOCK_RE);
  if (!match) return null;
  try {
    const parsed = JSON.parse(match[1]) as Partial<ManusPayload>;
    if (parsed.source !== "manus") return null;
    if (!parsed.signal_type || !parsed.title || !parsed.company) return null;
    return parsed as ManusPayload;
  } catch {
    return null;
  }
}
