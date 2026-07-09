/**
 * Email Templates API - manage workspace email templates
 */

import { apiClient } from './client';

export interface EmailTemplateSummary {
  id: string;
  template_type: string;
  group_id: string | null;
  name: string;
  description?: string;
  enabled: boolean;
  created_at: string;
  update_at: string;
}

export interface EmailTemplateRead {
  id: string;
  template_type: string;
  group_id: string | null;
  name: string;
  description?: string;
  subject: string;
  header_text?: string;
  message_top?: string;
  message_bottom?: string;
  button_text?: string;
  custom_html?: string;
  available_variables?: Record<string, string>;
  enabled: boolean;
  created_at: string;
  update_at: string;
}

export interface EmailTemplateCreate {
  template_type: string;
  group_id?: string;
  name: string;
  description?: string;
  subject: string;
  header_text?: string;
  message_top?: string;
  message_bottom?: string;
  button_text?: string;
  custom_html?: string;
  available_variables?: Record<string, string>;
  enabled?: boolean;
}

export interface EmailTemplateUpdate {
  name?: string;
  description?: string;
  subject?: string;
  header_text?: string;
  message_top?: string;
  message_bottom?: string;
  button_text?: string;
  custom_html?: string;
  available_variables?: Record<string, string>;
  enabled?: boolean;
}

/**
 * List all email templates for the workspace
 */
export async function listEmailTemplates(
  groupId: string,
  authToken?: string
): Promise<EmailTemplateSummary[]> {
  const response = await apiClient(`/groups/${groupId}/email-templates`, {
    method: 'GET',
    authToken,
  });
  return response.json();
}

/**
 * Get a specific email template
 */
export async function getEmailTemplate(
  groupId: string,
  templateId: string,
  authToken?: string
): Promise<EmailTemplateRead> {
  const response = await apiClient(`/groups/${groupId}/email-templates/${templateId}`, {
    method: 'GET',
    authToken,
  });
  return response.json();
}

/**
 * Create a new email template
 */
export async function createEmailTemplate(
  groupId: string,
  data: EmailTemplateCreate,
  authToken?: string
): Promise<EmailTemplateRead> {
  const response = await apiClient(`/groups/${groupId}/email-templates`, {
    method: 'POST',
    authToken,
    body: JSON.stringify(data),
  });
  return response.json();
}

/**
 * Update an email template
 */
export async function updateEmailTemplate(
  groupId: string,
  templateId: string,
  data: EmailTemplateUpdate,
  authToken?: string
): Promise<EmailTemplateRead> {
  const response = await apiClient(`/groups/${groupId}/email-templates/${templateId}`, {
    method: 'PATCH',
    authToken,
    body: JSON.stringify(data),
  });
  return response.json();
}

/**
 * Delete an email template
 */
export async function deleteEmailTemplate(
  groupId: string,
  templateId: string,
  authToken?: string
): Promise<void> {
  await apiClient(`/groups/${groupId}/email-templates/${templateId}`, {
    method: 'DELETE',
    authToken,
  });
}
