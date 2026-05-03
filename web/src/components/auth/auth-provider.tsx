"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "https://tanishq93-deepfake-detection.hf.space";
const SESSION_STORAGE_KEY = "verilens.session-token";

export interface UsageSummary {
  period: string;
  images_used: number;
  videos_used: number;
  image_limit: number;
  video_limit: number;
  image_remaining: number;
  video_remaining: number;
}

export interface AuthUser {
  email: string;
  name: string;
  picture_url: string;
  plan_name: string;
  subscription_status: string | null;
}

interface AuthConfig {
  enabled: boolean;
  google_client_id: string | null;
  free_image_limit: number;
  free_video_limit: number;
}

export interface BillingPlan {
  slug: string;
  name: string;
  price_label: string;
  description: string;
  image_limit: number;
  video_limit: number;
  featured: boolean;
  checkout_available: boolean;
}

interface BillingConfig {
  enabled: boolean;
  provider: string;
  plans: BillingPlan[];
}

interface AuthContextValue {
  apiBase: string;
  config: AuthConfig | null;
  billingConfig: BillingConfig | null;
  user: AuthUser | null;
  usage: UsageSummary | null;
  sessionToken: string | null;
  isLoading: boolean;
  isAuthenticating: boolean;
  isBillingPending: boolean;
  authError: string | null;
  billingError: string | null;
  isAuthenticated: boolean;
  loginWithGoogleCredential: (credential: string) => Promise<void>;
  logout: () => Promise<void>;
  updateUsage: (usage: UsageSummary) => void;
  refreshSession: () => Promise<void>;
  startCheckout: (planSlug: string) => Promise<void>;
  openBillingPortal: () => Promise<void>;
}

interface AuthSessionResponse {
  session_token: string;
  user: AuthUser;
  usage: UsageSummary;
}

interface MeResponse {
  user: AuthUser;
  usage: UsageSummary;
}

interface BillingRedirectResponse {
  url: string;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readStoredToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(SESSION_STORAGE_KEY);
}

function writeStoredToken(token: string | null): void {
  if (typeof window === "undefined") {
    return;
  }
  if (token) {
    window.localStorage.setItem(SESSION_STORAGE_KEY, token);
    return;
  }
  window.localStorage.removeItem(SESSION_STORAGE_KEY);
}

async function parseApiError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    if (payload.detail) {
      return payload.detail;
    }
  } catch {
    return "Unexpected server response.";
  }
  return "Request failed.";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [billingConfig, setBillingConfig] = useState<BillingConfig | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [isBillingPending, setIsBillingPending] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [billingError, setBillingError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const bootstrap = async () => {
      try {
        const configResponse = await fetch(`${API_BASE}/auth/config`);
        const configPayload = (await configResponse.json()) as AuthConfig;
        const billingResponse = await fetch(`${API_BASE}/billing/config`);
        const billingPayload = (await billingResponse.json()) as BillingConfig;
        if (cancelled) {
          return;
        }
        setConfig(configPayload);
        setBillingConfig(billingPayload);

        const storedToken = readStoredToken();
        if (!storedToken) {
          setSessionToken(null);
          return;
        }

        const meResponse = await fetch(`${API_BASE}/me`, {
          headers: {
            Authorization: `Bearer ${storedToken}`,
          },
        });

        if (!meResponse.ok) {
          writeStoredToken(null);
          setSessionToken(null);
          setUser(null);
          setUsage(null);
          return;
        }

        const mePayload = (await meResponse.json()) as MeResponse;
        if (cancelled) {
          return;
        }

        setSessionToken(storedToken);
        setUser(mePayload.user);
        setUsage(mePayload.usage);
      } catch {
        if (!cancelled) {
          setConfig(null);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void bootstrap();

    return () => {
      cancelled = true;
    };
  }, []);

  const refreshSession = async () => {
    const storedToken = readStoredToken();
    if (!storedToken) {
      setSessionToken(null);
      setUser(null);
      setUsage(null);
      return;
    }

    const response = await fetch(`${API_BASE}/me`, {
      headers: {
        Authorization: `Bearer ${storedToken}`,
      },
    });

    if (!response.ok) {
      writeStoredToken(null);
      setSessionToken(null);
      setUser(null);
      setUsage(null);
      return;
    }

    const payload = (await response.json()) as MeResponse;
    setSessionToken(storedToken);
    setUser(payload.user);
    setUsage(payload.usage);
  };

  const loginWithGoogleCredential = async (credential: string) => {
    setIsAuthenticating(true);
    setAuthError(null);

    try {
      const response = await fetch(`${API_BASE}/auth/google`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ id_token: credential }),
      });

      if (!response.ok) {
        throw new Error(await parseApiError(response));
      }

      const payload = (await response.json()) as AuthSessionResponse;
      writeStoredToken(payload.session_token);
      setSessionToken(payload.session_token);
      setUser(payload.user);
      setUsage(payload.usage);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Google sign-in failed.");
      throw error;
    } finally {
      setIsAuthenticating(false);
    }
  };

  const logout = async () => {
    const token = sessionToken ?? readStoredToken();
    setAuthError(null);

    try {
      if (token) {
        await fetch(`${API_BASE}/auth/logout`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
      }
    } finally {
      writeStoredToken(null);
      setSessionToken(null);
      setUser(null);
      setUsage(null);
      window.google?.accounts.id.disableAutoSelect?.();
    }
  };

  const startCheckout = async (planSlug: string) => {
    const token = sessionToken ?? readStoredToken();
    if (!token) {
      throw new Error("Sign in before starting checkout.");
    }

    setBillingError(null);
    setIsBillingPending(true);
    try {
      const response = await fetch(`${API_BASE}/billing/checkout`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ plan_slug: planSlug }),
      });

      if (!response.ok) {
        throw new Error(await parseApiError(response));
      }

      const payload = (await response.json()) as BillingRedirectResponse;
      window.location.href = payload.url;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to start checkout.";
      setBillingError(message);
      throw error;
    } finally {
      setIsBillingPending(false);
    }
  };

  const openBillingPortal = async () => {
    const token = sessionToken ?? readStoredToken();
    if (!token) {
      throw new Error("Sign in before opening billing.");
    }

    setBillingError(null);
    setIsBillingPending(true);
    try {
      const response = await fetch(`${API_BASE}/billing/portal`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error(await parseApiError(response));
      }

      const payload = (await response.json()) as BillingRedirectResponse;
      window.location.href = payload.url;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to open billing.";
      setBillingError(message);
      throw error;
    } finally {
      setIsBillingPending(false);
    }
  };

  const value: AuthContextValue = {
    apiBase: API_BASE,
    config,
    billingConfig,
    user,
    usage,
    sessionToken,
    isLoading,
    isAuthenticating,
    isBillingPending,
    authError,
    billingError,
    isAuthenticated: Boolean(sessionToken && user),
    loginWithGoogleCredential,
    logout,
    updateUsage: setUsage,
    refreshSession,
    startCheckout,
    openBillingPortal,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}
