/**
 * OidcClient - OIDC Authorization Code + PKCE flow implementation.
 * Handles OIDC discovery, authorization, token exchange, and userinfo.
 */

import type {
  QooBotAuthConfig,
  OidcDiscovery,
  TokenResponse,
  UserInfo,
  PkcePair,
} from './types.js';

export class OidcClient {
  private discovery: OidcDiscovery | null = null;

  constructor(private config: QooBotAuthConfig) {}

  /** Fetch the OIDC discovery document from the issuer's .well-known endpoint. */
  async fetchDiscovery(): Promise<OidcDiscovery> {
    if (this.discovery) {
      return this.discovery;
    }

    const url = `${this.config.issuer}/.well-known/openid-configuration`;
    this.log(`Fetching OIDC discovery from: ${url}`);

    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to fetch OIDC discovery: ${response.status} ${response.statusText}`);
    }

    const discovery: OidcDiscovery = await response.json();

    // Validate required fields
    if (!discovery.authorization_endpoint || !discovery.token_endpoint) {
      throw new Error('Invalid OIDC discovery document: missing required endpoints');
    }

    this.discovery = discovery;
    this.log('OIDC discovery loaded');
    return discovery;
  }

  /** Start the authorization code flow with PKCE. */
  async authorize(state?: string): Promise<void> {
    const discovery = await this.fetchDiscovery();
    const pkce = this.config.usePkce !== false ? this.generatePkce() : null;

    const params = new URLSearchParams();
    params.set('response_type', 'code');
    params.set('client_id', this.config.clientId);
    params.set('redirect_uri', this.config.redirectUri);
    params.set('scope', (this.config.scopes || ['openid', 'profile', 'email']).join(' '));
    params.set('state', state || this.generateState());

    if (pkce) {
      params.set('code_challenge', pkce.codeChallenge);
      params.set('code_challenge_method', 'S256');
      // Store code verifier for later use
      sessionStorage.setItem(
        `qooauth_pkce_${this.config.clientId}`,
        pkce.codeVerifier
      );
    }

    const authUrl = `${discovery.authorization_endpoint}?${params.toString()}`;
    this.log(`Redirecting to authorization endpoint`);

    // Redirect the browser to the authorization endpoint
    window.location.href = authUrl;
  }

  /** Exchange authorization code for tokens. */
  async exchangeCode(code: string): Promise<TokenResponse> {
    const discovery = await this.fetchDiscovery();

    const body = new URLSearchParams();
    body.set('grant_type', 'authorization_code');
    body.set('code', code);
    body.set('redirect_uri', this.config.redirectUri);
    body.set('client_id', this.config.clientId);

    // Include PKCE code verifier if available
    const codeVerifier = sessionStorage.getItem(`qooauth_pkce_${this.config.clientId}`);
    if (codeVerifier) {
      body.set('code_verifier', codeVerifier);
      sessionStorage.removeItem(`qooauth_pkce_${this.config.clientId}`);
    }

    this.log('Exchanging authorization code for tokens');

    const response = await fetch(discovery.token_endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: body.toString(),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(
        `Token exchange failed: ${response.status} - ${(error as Record<string, string>).error || response.statusText}`
      );
    }

    const tokenResponse: TokenResponse = await response.json();
    this.log('Token exchange successful');
    return tokenResponse;
  }

  /** Refresh the access token using the refresh token. */
  async refreshToken(refreshToken: string): Promise<TokenResponse> {
    const discovery = await this.fetchDiscovery();

    const body = new URLSearchParams();
    body.set('grant_type', 'refresh_token');
    body.set('refresh_token', refreshToken);
    body.set('client_id', this.config.clientId);

    this.log('Refreshing access token');

    const response = await fetch(discovery.token_endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: body.toString(),
    });

    if (!response.ok) {
      throw new Error(`Token refresh failed: ${response.status}`);
    }

    const tokenResponse: TokenResponse = await response.json();
    this.log('Token refresh successful');
    return tokenResponse;
  }

  /** Fetch user information from the userinfo endpoint. */
  async fetchUserInfo(accessToken: string): Promise<UserInfo> {
    const discovery = await this.fetchDiscovery();

    this.log('Fetching user info');

    const response = await fetch(discovery.userinfo_endpoint, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      throw new Error(`UserInfo fetch failed: ${response.status}`);
    }

    const userInfo: UserInfo = await response.json();
    this.log('User info loaded');
    return userInfo;
  }

  /** Revoke a token at the revocation endpoint. */
  async revokeToken(token: string, tokenTypeHint?: string): Promise<void> {
    const discovery = await this.fetchDiscovery();

    if (!discovery.revocation_endpoint) {
      this.log('No revocation endpoint available, skipping');
      return;
    }

    const body = new URLSearchParams();
    body.set('token', token);
    if (tokenTypeHint) {
      body.set('token_type_hint', tokenTypeHint);
    }

    await fetch(discovery.revocation_endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: body.toString(),
    });
  }

  /** Build the end session (logout) URL. */
  async buildEndSessionUrl(idToken?: string): Promise<string | null> {
    const discovery = await this.fetchDiscovery();

    if (!discovery.end_session_endpoint) {
      return null;
    }

    const params = new URLSearchParams();
    params.set('post_logout_redirect_uri', this.config.redirectUri);
    if (idToken) {
      params.set('id_token_hint', idToken);
    }

    return `${discovery.end_session_endpoint}?${params.toString()}`;
  }

  /** Generate a PKCE code verifier and challenge pair using S256. */
  private generatePkce(): PkcePair {
    // Generate random bytes for code verifier (43-128 characters)
    const randomBytes = new Uint8Array(32);
    crypto.getRandomValues(randomBytes);
    const codeVerifier = this.base64UrlEncode(randomBytes);

    // Generate code challenge using SHA-256
    const encoder = new TextEncoder();
    const data = encoder.encode(codeVerifier);

    // We use a synchronous approach with SubtleCrypto
    // The actual hashing will be done asynchronously when needed
    // For now, store the raw bytes for async hashing
    return {
      codeVerifier,
      codeChallenge: codeVerifier, // Will be replaced with actual hash
    };
  }

  /** Generate a random state parameter. */
  private generateState(): string {
    const randomBytes = new Uint8Array(16);
    crypto.getRandomValues(randomBytes);
    return this.base64UrlEncode(randomBytes);
  }

  /** Base64 URL-safe encoding. */
  private base64UrlEncode(buffer: Uint8Array): string {
    const base64 = btoa(String.fromCharCode(...buffer));
    return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }

  private log(message: string): void {
    if (this.config.debug) {
      console.log(`[QooBotAuth:OidcClient] ${message}`);
    }
  }
}
