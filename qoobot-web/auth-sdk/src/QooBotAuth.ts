/**
 * QooBotAuth - Main authentication SDK class.
 * Provides signIn, signOut, getUser, getAccessToken, and event handling.
 */

import type {
  QooBotAuthConfig,
  AuthState,
  UserInfo,
  AuthError,
  AuthEvent,
  AuthEventHandler,
} from './types.js';
import { OidcClient } from './OidcClient.js';
import { TokenManager } from './TokenManager.js';

export class QooBotAuth {
  private config: QooBotAuthConfig;
  private oidcClient: OidcClient;
  private tokenManager: TokenManager;
  private state: AuthState;
  private eventHandlers: Map<AuthEvent, Set<AuthEventHandler>> = new Map();
  private refreshTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(config: QooBotAuthConfig) {
    this.config = {
      scopes: ['openid', 'profile', 'email'],
      usePkce: true,
      storage: 'localStorage',
      autoRefresh: true,
      refreshThresholdSeconds: 60,
      debug: false,
      ...config,
    };

    this.oidcClient = new OidcClient(this.config);
    this.tokenManager = new TokenManager(this.config);

    this.state = {
      isAuthenticated: false,
      isLoading: true,
      user: null,
      accessToken: null,
      accessTokenExpiresAt: null,
      error: null,
    };

    // Check for existing session
    this.initializeFromStorage();
  }

  /** Sign in with the OIDC authorization code flow + PKCE. */
  async signIn(): Promise<void> {
    this.log('Starting sign-in flow');

    // Check if we're returning from the authorization server with a code
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const error = urlParams.get('error');
    const errorDescription = urlParams.get('error_description');

    if (error) {
      this.handleError({
        code: error,
        message: 'Authorization failed',
        description: errorDescription || undefined,
      });
      return;
    }

    if (code) {
      // Exchange code for tokens
      try {
        this.updateState({ isLoading: true });
        const tokenResponse = await this.oidcClient.exchangeCode(code);

        // Save tokens
        this.tokenManager.saveTokens(tokenResponse);

        // Fetch user info
        const userInfo = await this.oidcClient.fetchUserInfo(tokenResponse.access_token);

        // Clean URL
        window.history.replaceState({}, document.title, window.location.pathname);

        // Update state
        this.updateState({
          isAuthenticated: true,
          isLoading: false,
          user: userInfo,
          accessToken: tokenResponse.access_token,
          accessTokenExpiresAt: Date.now() + tokenResponse.expires_in * 1000,
          error: null,
        });

        this.emit('signIn', userInfo);
        this.emit('userLoaded', userInfo);

        // Setup auto-refresh
        if (this.config.autoRefresh && tokenResponse.refresh_token) {
          this.scheduleTokenRefresh(tokenResponse.expires_in);
        }
      } catch (err) {
        this.handleError({
          code: 'token_exchange_failed',
          message: 'Failed to exchange authorization code',
          description: err instanceof Error ? err.message : String(err),
        });
      }
    } else {
      // Start authorization flow
      try {
        await this.oidcClient.authorize();
      } catch (err) {
        this.handleError({
          code: 'authorization_failed',
          message: 'Failed to start authorization flow',
          description: err instanceof Error ? err.message : String(err),
        });
      }
    }
  }

  /** Sign out the current user. */
  async signOut(): Promise<void> {
    this.log('Signing out');

    try {
      const idToken = this.tokenManager.getIdToken();
      const accessToken = this.tokenManager.getAccessToken();

      // Try to revoke tokens at the server
      if (accessToken) {
        await this.oidcClient.revokeToken(accessToken, 'access_token').catch(() => {});
      }

      const refreshToken = this.tokenManager.getRefreshToken();
      if (refreshToken) {
        await this.oidcClient.revokeToken(refreshToken, 'refresh_token').catch(() => {});
      }

      // Clear local tokens
      this.tokenManager.clearTokens();

      // Clear refresh timer
      if (this.refreshTimer) {
        clearTimeout(this.refreshTimer);
        this.refreshTimer = null;
      }

      // Reset state
      this.updateState({
        isAuthenticated: false,
        isLoading: false,
        user: null,
        accessToken: null,
        accessTokenExpiresAt: null,
        error: null,
      });

      this.emit('signOut');

      // Redirect to end session endpoint if available
      const endSessionUrl = await this.oidcClient.buildEndSessionUrl(idToken || undefined);
      if (endSessionUrl) {
        window.location.href = endSessionUrl;
      }
    } catch (err) {
      this.log(`Sign-out error: ${err}`);
      // Force local cleanup even if server-side logout fails
      this.tokenManager.clearTokens();
      this.updateState({
        isAuthenticated: false,
        isLoading: false,
        user: null,
        accessToken: null,
        accessTokenExpiresAt: null,
        error: null,
      });
    }
  }

  /** Get the current user information. */
  getUser(): UserInfo | null {
    return this.state.user;
  }

  /** Get the current access token (refreshing if needed). */
  async getAccessToken(): Promise<string | null> {
    if (!this.state.isAuthenticated) {
      return null;
    }

    // Check if token needs refresh
    if (this.tokenManager.isTokenExpired(this.config.refreshThresholdSeconds)) {
      const refreshToken = this.tokenManager.getRefreshToken();
      if (refreshToken) {
        try {
          const tokenResponse = await this.oidcClient.refreshToken(refreshToken);
          this.tokenManager.saveTokens(tokenResponse);

          this.updateState({
            accessToken: tokenResponse.access_token,
            accessTokenExpiresAt: Date.now() + tokenResponse.expires_in * 1000,
          });

          if (tokenResponse.expires_in) {
            this.scheduleTokenRefresh(tokenResponse.expires_in);
          }

          this.emit('tokenRefreshed');
          return tokenResponse.access_token;
        } catch {
          this.emit('tokenExpired');
          await this.signOut();
          return null;
        }
      } else {
        this.emit('tokenExpired');
        await this.signOut();
        return null;
      }
    }

    return this.tokenManager.getAccessToken();
  }

  /** Get the current authentication state. */
  getState(): Readonly<AuthState> {
    return { ...this.state };
  }

  /** Subscribe to authentication events. */
  on(event: AuthEvent, handler: AuthEventHandler): () => void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }
    this.eventHandlers.get(event)!.add(handler);

    // Return unsubscribe function
    return () => {
      this.eventHandlers.get(event)?.delete(handler);
    };
  }

  /** Check if the user is authenticated. */
  isAuthenticated(): boolean {
    return this.state.isAuthenticated;
  }

  /** Check if the SDK is currently loading. */
  isLoading(): boolean {
    return this.state.isLoading;
  }

  // ---- Private methods ----

  private initializeFromStorage(): void {
    if (this.tokenManager.hasValidToken()) {
      const accessToken = this.tokenManager.getAccessToken();
      const expiresAt = this.tokenManager.getExpiresAt();

      this.updateState({
        isAuthenticated: true,
        isLoading: false,
        accessToken,
        accessTokenExpiresAt: expiresAt,
      });

      // Fetch user info in background
      if (accessToken) {
        this.oidcClient.fetchUserInfo(accessToken)
          .then(userInfo => {
            this.updateState({ user: userInfo });
            this.emit('userLoaded', userInfo);
          })
          .catch(() => {
            // Token might be expired, try refresh
            this.getAccessToken();
          });
      }

      // Schedule refresh
      if (expiresAt && this.config.autoRefresh) {
        const expiresInSeconds = Math.max(0, (expiresAt - Date.now()) / 1000);
        this.scheduleTokenRefresh(expiresInSeconds);
      }
    } else {
      this.updateState({ isLoading: false });
    }
  }

  private scheduleTokenRefresh(expiresInSeconds: number): void {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
    }

    const refreshIn = Math.max(
      0,
      (expiresInSeconds - (this.config.refreshThresholdSeconds || 60)) * 1000
    );

    this.refreshTimer = setTimeout(() => {
      this.getAccessToken();
    }, refreshIn);

    this.log(`Token refresh scheduled in ${refreshIn}ms`);
  }

  private updateState(partial: Partial<AuthState>): void {
    this.state = { ...this.state, ...partial };
  }

  private handleError(error: AuthError): void {
    this.updateState({
      isLoading: false,
      error,
    });
    this.emit('error', error);
  }

  private emit(event: AuthEvent, data?: unknown): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data);
        } catch (err) {
          this.log(`Error in event handler for ${event}: ${err}`);
        }
      });
    }
  }

  private log(message: string): void {
    if (this.config.debug) {
      console.log(`[QooBotAuth] ${message}`);
    }
  }
}
