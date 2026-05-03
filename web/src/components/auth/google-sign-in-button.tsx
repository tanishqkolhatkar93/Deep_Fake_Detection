"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";

export function GoogleSignInButton() {
  const { config, loginWithGoogleCredential, isAuthenticating, authError } = useAuth();
  const buttonRef = useRef<HTMLDivElement>(null);
  const [isGoogleReady, setIsGoogleReady] = useState(false);

  useEffect(() => {
    if (!config?.enabled || !config.google_client_id || !buttonRef.current) {
      return;
    }

    const clientId = config.google_client_id;
    let intervalId: number | undefined;

    const mountButton = () => {
      if (!window.google?.accounts?.id || !buttonRef.current) {
        return false;
      }

      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: async (response) => {
          if (!response.credential) {
            return;
          }
          await loginWithGoogleCredential(response.credential);
        },
        auto_select: false,
        cancel_on_tap_outside: true,
        ux_mode: "popup",
      });

      buttonRef.current.innerHTML = "";
      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: "filled_black",
        size: "large",
        text: "continue_with",
        shape: "pill",
        logo_alignment: "left",
        width: Math.min(buttonRef.current.offsetWidth || 320, 360),
      });
      setIsGoogleReady(true);
      return true;
    };

    if (!mountButton()) {
      intervalId = window.setInterval(() => {
        if (mountButton() && intervalId) {
          window.clearInterval(intervalId);
        }
      }, 250);
    }

    return () => {
      if (intervalId) {
        window.clearInterval(intervalId);
      }
    };
  }, [config, loginWithGoogleCredential]);

  if (!config) {
    return (
      <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-3 text-sm text-white/60">
        <Loader2 className="size-4 animate-spin" />
        Checking login configuration
      </div>
    );
  }

  if (!config.enabled || !config.google_client_id) {
    return (
      <div className="rounded-2xl border border-amber-300/20 bg-amber-300/10 px-4 py-3 text-sm text-amber-50">
        Google login is not configured on the API yet.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div
        ref={buttonRef}
        className="min-h-11 min-w-[220px]"
        aria-busy={isAuthenticating || !isGoogleReady}
      />
      {isAuthenticating ? (
        <div className="inline-flex items-center gap-2 text-sm text-white/60">
          <Loader2 className="size-4 animate-spin" />
          Completing Google sign-in
        </div>
      ) : null}
      {authError ? <p className="text-sm text-red-200">{authError}</p> : null}
    </div>
  );
}
