"use client";

import { Check, CreditCard, Sparkles } from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function PricingGrid() {
  const {
    billingConfig,
    billingError,
    config,
    isAuthenticated,
    isBillingPending,
    startCheckout,
    openBillingPortal,
    user,
  } = useAuth();

  const plans = billingConfig?.plans ?? [];

  return (
    <section id="pricing" className="mt-20 space-y-6">
      <div className="max-w-3xl space-y-3">
        <p className="text-sm uppercase tracking-[0.28em] text-orange-200/65">Pricing</p>
        <h2 className="font-[family:var(--font-instrument-serif)] text-4xl text-white">
          Free entry, clear paid upgrade path.
        </h2>
        <p className="text-white/65">
          Start with {config?.free_image_limit ?? 10} image scans and{" "}
          {config?.free_video_limit ?? 3} short video scans each month. Upgrade only when usage
          grows.
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-4">
        <article className="rounded-[1.8rem] border border-white/10 bg-white/6 p-5 backdrop-blur-xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-lg font-semibold text-white">Free</p>
              <p className="mt-2 text-3xl font-semibold text-white">$0</p>
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/10 text-white">
              <Sparkles className="size-5" />
            </div>
          </div>
          <p className="mt-4 text-sm leading-6 text-white/65">
            Evaluate the detector before spending on higher scan volume.
          </p>
          <ul className="mt-5 space-y-3 text-sm text-white/70">
            <li className="flex items-center gap-2">
              <Check className="size-4 text-emerald-300" />
              {config?.free_image_limit ?? 10} images per month
            </li>
            <li className="flex items-center gap-2">
              <Check className="size-4 text-emerald-300" />
              {config?.free_video_limit ?? 3} videos per month
            </li>
            <li className="flex items-center gap-2">
              <Check className="size-4 text-emerald-300" />
              Google sign-in and tracked usage
            </li>
          </ul>
          <div className="mt-6 rounded-2xl border border-white/10 bg-[#091224] px-4 py-3 text-sm text-white/68">
            {isAuthenticated ? "Your current starting tier." : "Sign in to start on free."}
          </div>
        </article>

        {plans.map((plan) => {
          const isCurrentPlan = user?.plan_name === plan.slug;
          const actionLabel = !billingConfig?.enabled
            ? "Billing setup required"
            : isCurrentPlan
              ? "Current plan"
              : user && user.plan_name !== "free"
                ? "Change plan"
                : "Upgrade";

          return (
            <article
              key={plan.slug}
              className={cn(
                "rounded-[1.8rem] border bg-white/6 p-5 backdrop-blur-xl",
                plan.featured
                  ? "border-orange-300/35 shadow-[0_24px_60px_rgba(251,146,60,0.14)]"
                  : "border-white/10",
              )}
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-lg font-semibold text-white">{plan.name}</p>
                  <p className="mt-2 text-3xl font-semibold text-white">{plan.price_label}</p>
                </div>
                {plan.featured ? (
                  <div className="rounded-full border border-orange-300/25 bg-orange-300/10 px-3 py-1 text-xs uppercase tracking-[0.2em] text-orange-100">
                    Popular
                  </div>
                ) : null}
              </div>

              <p className="mt-4 text-sm leading-6 text-white/65">{plan.description}</p>

              <ul className="mt-5 space-y-3 text-sm text-white/70">
                <li className="flex items-center gap-2">
                  <Check className="size-4 text-emerald-300" />
                  {plan.image_limit} images per month
                </li>
                <li className="flex items-center gap-2">
                  <Check className="size-4 text-emerald-300" />
                  {plan.video_limit} videos per month
                </li>
                <li className="flex items-center gap-2">
                  <Check className="size-4 text-emerald-300" />
                  Hosted checkout and subscription billing
                </li>
              </ul>

              <Button
                type="button"
                disabled={
                  !isAuthenticated ||
                  !billingConfig?.enabled ||
                  isBillingPending ||
                  isCurrentPlan ||
                  !plan.checkout_available
                }
                onClick={() => {
                  if (!isAuthenticated) {
                    return;
                  }
                  if (user && user.plan_name !== "free") {
                    void openBillingPortal();
                    return;
                  }
                  void startCheckout(plan.slug);
                }}
                className={cn(
                  "mt-6 w-full rounded-2xl",
                  plan.featured
                    ? "bg-white text-[#07101f] hover:bg-white/90"
                    : "bg-white/10 text-white hover:bg-white/15",
                )}
              >
                <CreditCard className="size-4" />
                {actionLabel}
              </Button>
            </article>
          );
        })}
      </div>

      {billingError ? <p className="text-sm text-red-200">{billingError}</p> : null}
      {!billingConfig?.enabled ? (
        <p className="text-sm text-white/55">
          Billing UI is ready, but Lemon Squeezy is not configured on this deployment yet.
        </p>
      ) : null}
    </section>
  );
}
