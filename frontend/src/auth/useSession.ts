import { useCallback, useState } from "react";

import { clearAccessToken, getAccessToken, setTokens } from "../api/tokenStore";
import type { TokenResponse } from "../api/types";

export interface Session {
  accessToken: string | null;
  signIn: (tokens: TokenResponse) => void;
  signOut: () => void;
}

export function useSession(): Session {
  const [accessToken, setAccessTokenState] = useState<string | null>(() => getAccessToken());

  const signIn = useCallback((tokens: TokenResponse) => {
    setTokens(tokens);
    setAccessTokenState(tokens.access_token);
  }, []);

  const signOut = useCallback(() => {
    clearAccessToken();
    setAccessTokenState(null);
  }, []);

  return { accessToken, signIn, signOut };
}
