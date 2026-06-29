/**
 * TokenManager - Handles token storage, retrieval, and refresh.
 */

import type { QooBotAuthConfig, TokenResponse } from './types.js';

const STORAGE_KEY_PREFIX = 'qooauth_';

export class TokenManager {
  private storage: Storage | null;
  private readonly accessTokenKey: string;
  private readonly refreshTokenKey: string;
  private readonly expiresAtKey: string;
  private readonly idTokenKey: string;

  constructor(private config: QooBotAuthConfig) {
    this.storage = this.resolveStorage();
    this.accessTokenKey = `${STORAGE_KEY_PREFIX}${config.clientId}_access_token`;
    this.refreshTokenKey = `${STORAGE_KEY_PREFIX}${config.clientId}_refresh_token`;
    this.expiresAtKey = `${STORAGE_KEY_PREFIX}${config.clientId}_expires_at`;
    this.idTokenKey = `${STORAGE_KEY_PREFIX}${config.clientId}_id_token`;
  }

  /** Save tokens received from the authorization server. */
  saveTokens(response: TokenResponse): void {
    this.setItem(this.accessTokenKey, response.access_token);
    this.setItem(this.idTokenKey, response.id_token || '');

    if (response.refresh_token) {
      this.setItem(this.refreshTokenKey, response.refresh_token);
    }

    const expiresAt = Date.now() + response.expires_in * 1000;
    this.setItem(this.expiresAtKey, expiresAt.toString());

    this.log('Tokens saved successfully');
  }

  /** Get the current access token. */
  getAccessToken(): string | null {
    return this.getItem(this.accessTokenKey);
  }

  /** Get the current refresh token. */
  getRefreshToken(): string | null {
    return this.getItem(this.refreshTokenKey);
  }

  /** Get the access token expiry timestamp (ms). */
  getExpiresAt(): number | null {
    const val = this.getItem(this.expiresAtKey);
    return val ? parseInt(val, 10) : null;
  }

  /** Get the ID token if available. */
  getIdToken(): string | null {
    return this.getItem(this.idTokenKey);
  }

  /** Check if the current access token is expired or about to expire. */
  isTokenExpired(thresholdSeconds: number = 60): boolean {
    const expiresAt = this.getExpiresAt();
    if (!expiresAt) return true;
    return Date.now() > expiresAt - thresholdSeconds * 1000;
  }

  /** Clear all stored tokens. */
  clearTokens(): void {
    this.removeItem(this.accessTokenKey);
    this.removeItem(this.refreshTokenKey);
    this.removeItem(this.expiresAtKey);
    this.removeItem(this.idTokenKey);
    this.log('Tokens cleared');
  }

  /** Check if we have a valid (non-expired) access token. */
  hasValidToken(): boolean {
    const token = this.getAccessToken();
    if (!token) return false;
    return !this.isTokenExpired(0);
  }

  private resolveStorage(): Storage | null {
    switch (this.config.storage) {
      case 'sessionStorage':
        return typeof sessionStorage !== 'undefined' ? sessionStorage : null;
      case 'memory':
        return null; // In-memory storage (tokens only live in JS)
      case 'localStorage':
      default:
        return typeof localStorage !== 'undefined' ? localStorage : null;
    }
  }

  private getItem(key: string): string | null {
    if (this.storage) {
      return this.storage.getItem(key);
    }
    // Memory storage
    return (this as unknown as Record<string, string | null>)[key] || null;
  }

  private setItem(key: string, value: string): void {
    if (this.storage) {
      this.storage.setItem(key, value);
    } else {
      (this as unknown as Record<string, string>)[key] = value;
    }
  }

  private removeItem(key: string): void {
    if (this.storage) {
      this.storage.removeItem(key);
    } else {
      delete (this as unknown as Record<string, string | undefined>)[key];
    }
  }

  private log(message: string): void {
    if (this.config.debug) {
      console.log(`[QooBotAuth:TokenManager] ${message}`);
    }
  }
}
