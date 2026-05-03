"use client";

import { LogOut, ShieldCheck, Sparkles } from "lucide-react";

import { GoogleSignInButton } from "@/components/auth/google-sign-in-button";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth/auth-provider";

export function AccountPanel() {
  const {
    billingConfig,
    billingError,
    config,
    user,
    usage,
    isAuthenticated,
    isBillingPending,
    isLoading,
    logout,
    openBillingPortal,
  } = useAuth();

  if (isLoading) {
    return (
      <div className="rounded-[1.4rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white/60">
        Checking session
      </div>
    );
  }

  if (!isAuthenticated || !user || !usage) {
    return (
      <div className="flex flex-col gap-3 rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-4 text-white">
        <div className="space-y-1">
          <p className="text-sm font-medium text-white">Sign in to unlock your quota</p>
          <p className="text-sm leading-6 text-white/60">
            Free tier includes {config?.free_image_limit ?? 10} image scans and{" "}
            {config?.free_video_limit ?? 3} short video scans each month.
          </p>
        </div>
        <GoogleSignInButton />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 rounded-[1.6rem] border border-white/10 bg-white/[0.05] p-4 text-white shadow-[0_20px_45px_rgba(0,0,0,0.18)]">
      <div className="flex items-center gap-3">
        {user.picture_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={user.picture_url}
            alt={user.name}
            className="h-11 w-11 rounded-2xl border border-white/10 object-cover"
          />
        ) : (
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10 text-sm font-semibold">
            {user.name.slice(0, 1).toUpperCase()}
          </div>
        )}

        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-white">{user.name}</p>
          <p className="truncate text-sm text-white/58">{user.email}</p>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-[#091224] px-4 py-3">
          <p className="text-xs uppercase tracking-[0.22em] text-white/40">Images left</p>
          <p className="mt-2 flex items-center gap-2 text-2xl font-semibold text-white">
            <Sparkles className="size-4 text-orange-300" />
            {usage.image_remaining}
          </p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-[#091224] px-4 py-3">
          <p className="text-xs uppercase tracking-[0.22em] text-white/40">Videos left</p>
          <p className="mt-2 flex items-center gap-2 text-2xl font-semibold text-white">
            <ShieldCheck className="size-4 text-cyan-300" />
            {usage.video_remaining}
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between gap-4">
        <div className="text-sm text-white/58">
          Plan: <span className="font-medium text-white capitalize">{user.plan_name}</span>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          {billingConfig?.enabled && user.plan_name !== "free" ? (
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                void openBillingPortal();
              }}
              disabled={isBillingPending}
              className="rounded-full border-white/15 bg-transparent text-white hover:bg-white/10"
            >
              Manage billing
            </Button>
          ) : null}
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              void logout();
            }}
            className="rounded-full border-white/15 bg-transparent text-white hover:bg-white/10"
          >
            <LogOut className="size-4" />
            Log out
          </Button>
        </div>
      </div>
      {billingError ? <p className="text-sm text-red-200">{billingError}</p> : null}
    </div>
  );
}
