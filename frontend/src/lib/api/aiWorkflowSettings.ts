import { fetchApi } from "./client";
import { getApiUrl } from "./config";

export interface AIWorkflowSettings {
  id: string;
  group_id: string;
  enabled: boolean;
  credential_mode: "platform" | "workspace" | "disabled";
  provider: string | null;
  model: string | null;
  secret_ref: string | null;
  approval_mode: "suggest-only" | "allow-draft-update" | "allow-automatic-update";
  invocation_sources: Record<string, boolean> | null;
  operation_overrides: Record<string, unknown> | null;
  budget_config: Record<string, unknown> | null;
  logging_config: Record<string, unknown> | null;
  moderation_config: Record<string, unknown> | null;
}

export type AIWorkflowSettingsUpdate = Partial<Omit<AIWorkflowSettings, "id" | "group_id">>;

export async function getAIWorkflowSettings(authToken?: string): Promise<AIWorkflowSettings> {
  return fetchApi<AIWorkflowSettings>(`/api/groups/ai-settings`, {}, authToken);
}

export async function updateAIWorkflowSettings(
  patch: AIWorkflowSettingsUpdate,
  authToken?: string,
): Promise<AIWorkflowSettings> {
  return fetchApi<AIWorkflowSettings>(
    `/api/groups/ai-settings`,
    { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(patch) },
    authToken,
  );
}
