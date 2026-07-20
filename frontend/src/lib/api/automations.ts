/**
 * Automations (Flavor B workflows) — SDK wrapper (platform.automations).
 * Pass authToken in SSR (from Astro.cookies); omit it in the browser to use the HttpOnly cookie.
 */

import { createSdkClient } from '../sdk';
import type {
  Automation,
  AutomationCreate,
  AutomationUpdate,
  AutomationOptions,
  AutomationDefinition,
  AutomationValidateResult,
  AutomationPreviewResult,
} from '@inneropen/marvin-sdk/platform';

export type { Automation, AutomationCreate, AutomationUpdate, AutomationOptions };

/** Advisory coherence check for a definition (warnings, non-blocking). */
export async function validateAutomation(definition: AutomationDefinition, authToken?: string): Promise<AutomationValidateResult> {
  return createSdkClient(authToken).automations.validate(definition);
}

/** Dry-run a target selector — which entities it would act on, without running anything. */
export async function previewAutomation(definition: AutomationDefinition, payload: Record<string, unknown> = {}, authToken?: string): Promise<AutomationPreviewResult> {
  return createSdkClient(authToken).automations.preview(definition, payload);
}

export async function listAutomations(authToken?: string): Promise<Automation[]> {
  return createSdkClient(authToken).automations.list();
}

export async function getAutomationOptions(authToken?: string): Promise<AutomationOptions> {
  return createSdkClient(authToken).automations.options();
}

export async function createAutomation(data: AutomationCreate, authToken?: string): Promise<Automation> {
  return createSdkClient(authToken).automations.create(data);
}

export async function updateAutomation(id: string, data: AutomationUpdate, authToken?: string): Promise<Automation> {
  return createSdkClient(authToken).automations.update(id, data);
}

export async function deleteAutomation(id: string, authToken?: string): Promise<void> {
  return createSdkClient(authToken).automations.delete(id);
}

/** Run an automation now (the Manual trigger). */
export async function runAutomation(id: string, authToken?: string) {
  return createSdkClient(authToken).automations.run(id);
}

/** Dry-run an automation: resolve target + inputs, execute nothing, return the plan. */
export async function dryRunAutomation(id: string, authToken?: string) {
  return createSdkClient(authToken).automations.dryRun(id);
}

/** Recent runs of an automation (history list). */
export async function listAutomationExecutions(id: string, limit = 25, authToken?: string) {
  return createSdkClient(authToken).automations.executions(id, limit);
}

/** One run + its per-step records. */
export async function getAutomationExecution(id: string, executionId: string, authToken?: string) {
  return createSdkClient(authToken).automations.execution(id, executionId);
}
