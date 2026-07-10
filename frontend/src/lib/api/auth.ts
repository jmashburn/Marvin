/**
 * Authentication API
 * Migrated to use @inneropen/marvin-sdk
 */

import { createAuthClient } from '@inneropen/marvin-sdk';
import { createSdkClient } from '../sdk';
import type {
  LoginRequest,
  AuthToken,
  UserRegistration,
  ForgotPasswordRequest,
  ResetPasswordRequest,
} from '@inneropen/marvin-sdk';

export type { LoginRequest, AuthToken, UserRegistration, ForgotPasswordRequest, ResetPasswordRequest };

/**
 * Login with username and password
 */
export async function login(data: LoginRequest): Promise<AuthToken> {
  const authClient = createAuthClient(import.meta.env.VITE_API_URL || 'http://localhost:8080');
  return authClient.login(data);
}

/**
 * Register a new user
 */
export async function register(data: UserRegistration): Promise<{ message: string; userId: string }> {
  const authClient = createAuthClient(import.meta.env.VITE_API_URL || 'http://localhost:8080');
  return authClient.register(data);
}

/**
 * Request password reset
 */
export async function forgotPassword(data: ForgotPasswordRequest): Promise<{ message: string }> {
  const authClient = createAuthClient(import.meta.env.VITE_API_URL || 'http://localhost:8080');
  return authClient.forgotPassword(data);
}

/**
 * Reset password with token
 */
export async function resetPassword(data: ResetPasswordRequest): Promise<{ message: string }> {
  const authClient = createAuthClient(import.meta.env.VITE_API_URL || 'http://localhost:8080');
  return authClient.resetPassword(data);
}

/**
 * Refresh access token
 */
export async function refreshToken(authToken: string): Promise<AuthToken> {
  const sdk = createSdkClient(authToken);
  return sdk.session.refresh();
}

/**
 * Logout current user
 */
export async function logout(authToken: string): Promise<void> {
  const sdk = createSdkClient(authToken);
  return sdk.session.logout();
}
