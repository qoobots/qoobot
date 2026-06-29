/**
 * QooBot Auth SDK - TypeScript type definitions.
 */

/** Configuration options for the QooBot Auth SDK. */
export interface QooBotAuthConfig {
  /** OIDC issuer URL (e.g., https://auth.qoobot.io) */
  issuer: string;

  /** OAuth2 client ID */
  clientId: string;

  /** Redirect URI after authentication */
  redirectUri: string;

  /** OAuth2 scopes to request */
  scopes?: string[];

  /** Whether to use PKCE (recommended, default: true) */
  usePkce?: boolean;

  /** Token storage mechanism (default: localStorage) */
  storage?: 'localStorage' | 'sessionStorage' | 'memory';

  /** Whether to automatically refresh tokens */
  autoRefresh?: boolean;

  /** Refresh token before expiry (seconds before expiry, default: 60) */
  refreshThresholdSeconds?: number;

  /** Whether to enable debug logging */
  debug?: boolean;
}

/** OIDC Discovery Document (partial). */
export interface OidcDiscovery {
  issuer: string;
  authorization_endpoint: string;
  token_endpoint: string;
  userinfo_endpoint: string;
  end_session_endpoint?: string;
  jwks_uri: string;
  revocation_endpoint?: string;
  introspection_endpoint?: string;
  scopes_supported: string[];
  response_types_supported: string[];
  grant_types_supported: string[];
  code_challenge_methods_supported?: string[];
}

/** Token response from the OAuth2 token endpoint. */
export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token?: string;
  id_token?: string;
  scope?: string;
}

/** User information from the OIDC userinfo endpoint. */
export interface UserInfo {
  sub: string;
  name?: string;
  given_name?: string;
  family_name?: string;
  email?: string;
  email_verified?: boolean;
  picture?: string;
  preferred_username?: string;
  roles?: string[];
  [key: string]: unknown;
}

/** Authentication state for the SDK. */
export interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: UserInfo | null;
  accessToken: string | null;
  accessTokenExpiresAt: number | null;
  error: AuthError | null;
}

/** Authentication error. */
export interface AuthError {
  code: string;
  message: string;
  description?: string;
}

/** PKCE code verifier and challenge pair. */
export interface PkcePair {
  codeVerifier: string;
  codeChallenge: string;
}

/** Events emitted by the SDK. */
export type AuthEvent =
  | 'signIn'
  | 'signOut'
  | 'tokenRefreshed'
  | 'tokenExpired'
  | 'userLoaded'
  | 'error';

export type AuthEventHandler = (data?: unknown) => void;
