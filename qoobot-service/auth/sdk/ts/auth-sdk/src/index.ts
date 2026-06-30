/**
 * @qoobot/auth-sdk
 * QooBot Authentication SDK for Web Applications
 *
 * Provides OIDC Authorization Code + PKCE flow with automatic token refresh.
 *
 * @example
 * ```typescript
 * import { QooBotAuth } from '@qoobot/auth-sdk';
 *
 * const auth = new QooBotAuth({
 *   issuer: 'https://auth.qoobot.io',
 *   clientId: 'qoobot-web-portal',
 *   redirectUri: window.location.origin + '/callback',
 * });
 *
 * // Sign in
 * await auth.signIn();
 *
 * // Get access token (auto-refreshes)
 * const token = await auth.getAccessToken();
 *
 * // Get user info
 * const user = auth.getUser();
 *
 * // Sign out
 * await auth.signOut();
 * ```
 */

export { QooBotAuth } from './QooBotAuth.js';
export { OidcClient } from './OidcClient.js';
export { TokenManager } from './TokenManager.js';
export type {
  QooBotAuthConfig,
  OidcDiscovery,
  TokenResponse,
  UserInfo,
  AuthState,
  AuthError,
  PkcePair,
  AuthEvent,
  AuthEventHandler,
} from './types.js';
