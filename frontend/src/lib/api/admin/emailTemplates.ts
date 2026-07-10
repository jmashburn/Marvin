/**
 * Admin Email Templates API - manage system-wide email templates
 */

import { apiClient } from '../client';
import type {
  EmailTemplateSummary,
  EmailTemplateRead,
  EmailTemplateCreate,
  EmailTemplateUpdate,
} from '../emailTemplates';

/**
 * List all system-wide email templates
 */
export async function listSystemEmailTemplates(
  authToken?: string
): Promise<EmailTemplateSummary[]> {
  const response = await apiClient(`/admin/email/templates`, {
    method: 'GET',
    authToken,
  });
  return response.json();
}

/**
 * Get a specific system email template
 */
export async function getSystemEmailTemplate(
  templateId: string,
  authToken?: string
): Promise<EmailTemplateRead> {
  const response = await apiClient(`/admin/email/templates/${templateId}`, {
    method: 'GET',
    authToken,
  });
  return response.json();
}

/**
 * Create a new system email template
 */
export async function createSystemEmailTemplate(
  data: EmailTemplateCreate,
  authToken?: string
): Promise<EmailTemplateRead> {
  const response = await apiClient(`/admin/email/templates`, {
    method: 'POST',
    authToken,
    body: JSON.stringify(data),
  });
  return response.json();
}

/**
 * Update a system email template
 */
export async function updateSystemEmailTemplate(
  templateId: string,
  data: EmailTemplateUpdate,
  authToken?: string
): Promise<EmailTemplateRead> {
  const response = await apiClient(`/admin/email/templates/${templateId}`, {
    method: 'PATCH',
    authToken,
    body: JSON.stringify(data),
  });
  return response.json();
}

/**
 * Delete a system email template
 */
export async function deleteSystemEmailTemplate(
  templateId: string,
  authToken?: string
): Promise<void> {
  await apiClient(`/admin/email/templates/${templateId}`, {
    method: 'DELETE',
    authToken,
  });
}

/**
 * Send a test email using a system template
 */
export async function sendSystemTemplateTestEmail(
  templateId: string,
  recipientEmail: string,
  authToken?: string
): Promise<{ message: string }> {
  const response = await apiClient(`/admin/email/templates/${templateId}/test`, {
    method: 'POST',
    authToken,
    body: JSON.stringify({ recipient_email: recipientEmail }),
  });
  return response.json();
}
