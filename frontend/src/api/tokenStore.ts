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

export function getCurrentUserId(): string | null {
  const token = getAccessToken();
  if (!token) return null;
  try {
    const parts = token.split(".");
    if (parts.length < 2) return null;
    const base64 = parts[1].replaceAll("-", "+").replaceAll("_", "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const payload = JSON.parse(atob(padded));
    return typeof payload.sub === "string" ? payload.sub : null;
  } catch {
    return null;
  }
}
