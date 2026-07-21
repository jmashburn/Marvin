/**
 * Workspace Integrations — SDK wrapper (platform.integrations).
 * Pass authToken in SSR (from Astro.cookies); omit it in the browser to use the HttpOnly cookie.
 */

import { createSdkClient } from '../sdk';
import type {
  Integration,
  IntegrationCreate,
  IntegrationUpdate,
  IntegrationProviderInfo,
  IntegrationActionResult,
  IntegrationCheckResult,
} from '@inneropen/marvin-sdk/platform';

export type {
  Integration,
  IntegrationCreate,
  IntegrationUpdate,
  IntegrationProviderInfo,
  IntegrationActionResult,
  IntegrationCheckResult,
};

export async function listProviders(authToken?: string): Promise<IntegrationProviderInfo[]> {
  return createSdkClient(authToken).integrations.listProviders();
}

export async function listIntegrations(authToken?: string): Promise<Integration[]> {
  return createSdkClient(authToken).integrations.list();
}

export async function createIntegration(data: IntegrationCreate, authToken?: string): Promise<Integration> {
  return createSdkClient(authToken).integrations.create(data);
}

export async function updateIntegration(id: string, data: IntegrationUpdate, authToken?: string): Promise<Integration> {
  return createSdkClient(authToken).integrations.update(id, data);
}

export async function deleteIntegration(id: string, authToken?: string): Promise<void> {
  return createSdkClient(authToken).integrations.delete(id);
}

export async function checkIntegration(id: string, authToken?: string): Promise<IntegrationCheckResult> {
  return createSdkClient(authToken).integrations.check(id);
}

export async function runIntegrationAction(
  id: string,
  actionKey: string,
  args: Record<string, unknown> = {},
  authToken?: string,
): Promise<IntegrationActionResult> {
  return createSdkClient(authToken).integrations.runAction(id, actionKey, args);
}
