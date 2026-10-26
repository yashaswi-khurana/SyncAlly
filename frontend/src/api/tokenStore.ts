import type { TokenResponse } from "./types";

const ACCESS_TOKEN_KEY = "syncally.accessToken";

export function getAccessToken(): string | null {
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setAccessToken(token: string): void {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function setTokens(tokens: TokenResponse): void {
  // Refresh tokens stay out of browser storage until the app uses a server-managed
  // HttpOnly cookie flow. Persisting one here would expose a long-lived credential to JS.
  window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
}

export function clearAccessToken(): void {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
}
