"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  Film,
  ImageUp,
  Loader2,
  Sparkles,
} from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import { GoogleSignInButton } from "@/components/auth/google-sign-in-button";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Mode = "image" | "video";

interface MetadataResponse {
  limits: {
    max_image_bytes: number;
    max_video_bytes: number;
    max_video_duration_seconds: number;
  };
  model: {
    name: string;
    threshold: number;
  };
}

interface DetectionUsage {
  period: string;
  images_used: number;
  videos_used: number;
  image_limit: number;
  video_limit: number;
  image_remaining: number;
  video_remaining: number;
}

interface DetectionResponse {
  request_id: string;
  processing_ms: number;
  model: string;
  media_type: string;
  report: {
    verdict: string;
    fake_probability: number;
    summary: string;
    evidence: Record<string, number>;
    frames_sampled?: number;
  };
  usage?: DetectionUsage;
}

export function MediaScanner() {
  const {
    apiBase,
    authError,
    config,
    isAuthenticated,
    sessionToken,
    updateUsage,
    usage,
    user,
  } = useAuth();
  const [mode, setMode] = useState<Mode>("image");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<MetadataResponse | null>(null);
  const [result, setResult] = useState<DetectionResponse | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    let cancelled = false;

    fetch(`${apiBase}/metadata`)
      .then((response) => response.json())
      .then((payload: MetadataResponse) => {
        if (!cancelled) {
          setMetadata(payload);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setMetadata(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [apiBase]);

  const limitText = useMemo(() => {
    if (!metadata) {
      return "Loading live limits...";
    }

    return mode === "image"
      ? `Images up to ${Math.round(metadata.limits.max_image_bytes / (1024 * 1024))} MB`
      : `Videos up to ${Math.round(metadata.limits.max_video_bytes / (1024 * 1024))} MB and ${Math.round(metadata.limits.max_video_duration_seconds)} seconds`;
  }, [metadata, mode]);

  const evidenceEntries = result
    ? Object.entries(result.report.evidence).sort((left, right) => right[1] - left[1])
    : [];

  const handleSubmit = async () => {
    if (!isAuthenticated || !sessionToken) {
      setError("Sign in with Google to start scanning and track your free-tier usage.");
      return;
    }

    if (!file) {
      setError("Choose a file before starting the scan.");
      return;
    }

    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    startTransition(async () => {
      try {
        const endpoint = mode === "image" ? "detect/image" : "detect/video";
        const response = await fetch(`${apiBase}/${endpoint}`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${sessionToken}`,
          },
          body: formData,
        });
        const payload = (await response.json()) as DetectionResponse | { detail?: string };

        if (!response.ok) {
          throw new Error(
            "detail" in payload && payload.detail
              ? payload.detail
              : "The detector could not process that upload.",
          );
        }

        const detectionPayload = payload as DetectionResponse;
        setResult(detectionPayload);
        if (detectionPayload.usage) {
          updateUsage(detectionPayload.usage);
        }
      } catch (submissionError) {
        setError(
          submissionError instanceof Error
            ? submissionError.message
            : "Unexpected scanner failure.",
        );
      }
    });
  };

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => {
            setMode("image");
            setFile(null);
            setResult(null);
            setError(null);
          }}
          className={cn(
            "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm transition",
            mode === "image"
              ? "border-white/20 bg-white text-[#07101f]"
              : "border-white/10 bg-white/5 text-white/70 hover:bg-white/10",
          )}
        >
          <ImageUp className="size-4" />
          Image scan
        </button>
        <button
          type="button"
          onClick={() => {
            setMode("video");
            setFile(null);
            setResult(null);
            setError(null);
          }}
          className={cn(
            "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm transition",
            mode === "video"
              ? "border-white/20 bg-white text-[#07101f]"
              : "border-white/10 bg-white/5 text-white/70 hover:bg-white/10",
          )}
        >
          <Film className="size-4" />
          Video scan
        </button>
      </div>

      <div className="rounded-[1.7rem] border border-white/10 bg-[#07101f]/78 p-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div className="space-y-2">
            <p className="text-sm uppercase tracking-[0.22em] text-white/45">Live upload</p>
            <h3 className="text-2xl font-semibold text-white">
              {mode === "image"
                ? "Check an image for synthetic artifacts"
                : "Check a short clip for manipulation risk"}
            </h3>
            <p className="max-w-2xl text-sm leading-6 text-white/62">{limitText}</p>
            {usage ? (
              <div className="flex flex-wrap items-center gap-3 pt-2 text-sm text-white/70">
                <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5">
                  Images left:{" "}
                  <span className="font-medium text-white">{usage.image_remaining}</span>
                </span>
                <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5">
                  Videos left:{" "}
                  <span className="font-medium text-white">{usage.video_remaining}</span>
                </span>
              </div>
            ) : (
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-white/60">
                Free tier starts at {config?.free_image_limit ?? 10} image scans and{" "}
                {config?.free_video_limit ?? 3} short video scans each month.
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white/60">
            Model: <span className="font-medium text-white">{metadata?.model.name ?? "Loading..."}</span>
          </div>
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_auto]">
          <label className="flex min-h-40 cursor-pointer flex-col justify-between rounded-[1.5rem] border border-dashed border-white/15 bg-white/[0.03] p-5 transition hover:bg-white/[0.05]">
            <div className="space-y-2">
              <p className="text-lg font-semibold text-white">
                {file ? file.name : `Choose a ${mode} file`}
              </p>
              <p className="text-sm leading-6 text-white/58">
                {mode === "image"
                  ? "PNG, JPG, and WEBP are supported."
                  : "MP4, MOV, AVI, MKV, and WEBM are supported."}
              </p>
            </div>
            <input
              className="hidden"
              type="file"
              accept={
                mode === "image"
                  ? "image/png,image/jpeg,image/webp"
                  : "video/mp4,video/quicktime,video/x-msvideo,video/x-matroska,video/webm"
              }
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
            <div className="inline-flex items-center gap-2 text-sm text-white/78">
              <Sparkles className="size-4" />
              {file ? "Ready to analyze" : "Drop here or browse from device"}
            </div>
          </label>

          <div className="flex flex-col gap-3">
            {!isAuthenticated ? (
              <div className="rounded-[1.4rem] border border-white/10 bg-white/[0.04] p-4 text-sm text-white/68">
                <p className="font-medium text-white">Sign in before you run your first scan.</p>
                <p className="mt-2 leading-6">
                  Usage is tracked per account so the monthly free tier stays fair for every
                  client.
                </p>
                <div className="mt-4">
                  <GoogleSignInButton />
                </div>
              </div>
            ) : (
              <div className="rounded-[1.4rem] border border-white/10 bg-white/[0.04] p-4 text-sm text-white/68">
                <p className="font-medium text-white">
                  Signed in as {user?.name || user?.email}
                </p>
                <p className="mt-2 leading-6">
                  Each successful scan updates your monthly quota immediately.
                </p>
              </div>
            )}

            <Button
              type="button"
              size="lg"
              onClick={handleSubmit}
              disabled={!file || isPending || !isAuthenticated}
              className="rounded-2xl bg-white px-5 text-[#07101f] hover:bg-white/90"
            >
              {isPending ? <Loader2 className="size-4 animate-spin" /> : null}
              {isPending ? "Analyzing..." : "Run detector"}
            </Button>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 text-sm leading-6 text-white/60">
              The browser submits directly to the public API with your session token. Quotas,
              timings, and model details stay visible in the UI.
            </div>
          </div>
        </div>

        {error ? (
          <div className="mt-5 flex items-start gap-3 rounded-2xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-100">
            <AlertCircle className="mt-0.5 size-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : null}
        {!error && authError ? (
          <div className="mt-5 flex items-start gap-3 rounded-2xl border border-amber-300/20 bg-amber-300/10 px-4 py-3 text-sm text-amber-50">
            <AlertCircle className="mt-0.5 size-4 shrink-0" />
            <span>{authError}</span>
          </div>
        ) : null}

        {result ? (
          <div className="mt-6 grid gap-4 lg:grid-cols-[0.52fr_0.48fr]">
            <div className="rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm uppercase tracking-[0.22em] text-white/42">Verdict</p>
                  <div className="mt-2 flex items-center gap-3">
                    {result.report.verdict === "Yes" ? (
                      <AlertCircle className="size-5 text-orange-300" />
                    ) : (
                      <CheckCircle2 className="size-5 text-emerald-300" />
                    )}
                    <span className="text-3xl font-semibold text-white">
                      {result.report.verdict}
                    </span>
                  </div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-[#0a1020] px-4 py-3 text-right">
                  <p className="text-xs uppercase tracking-[0.22em] text-white/38">
                    Fake probability
                  </p>
                  <p className="mt-2 text-2xl font-semibold text-white">
                    {(result.report.fake_probability * 100).toFixed(1)}%
                  </p>
                </div>
              </div>

              <p className="mt-5 text-sm leading-6 text-white/68">{result.report.summary}</p>

              <div className="mt-5 grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-white/38">Request ID</p>
                  <p className="mt-2 text-sm text-white">{result.request_id.slice(0, 12)}</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-white/38">Processing</p>
                  <p className="mt-2 inline-flex items-center gap-2 text-sm text-white">
                    <Clock3 className="size-4 text-cyan-200" />
                    {result.processing_ms.toFixed(0)} ms
                  </p>
                </div>
                {usage ? (
                  <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 sm:col-span-2">
                    <p className="text-xs uppercase tracking-[0.22em] text-white/38">
                      Quota tracking
                    </p>
                    <p className="mt-2 text-sm text-white/78">
                      {usage.images_used}/{usage.image_limit} image scans used,{" "}
                      {usage.videos_used}/{usage.video_limit} video scans used in {usage.period}.
                    </p>
                  </div>
                ) : null}
              </div>
            </div>

            <div className="rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-5">
              <p className="text-sm uppercase tracking-[0.22em] text-white/42">Evidence</p>
              <div className="mt-4 space-y-3">
                {evidenceEntries.map(([key, value]) => (
                  <div
                    key={key}
                    className="flex items-center justify-between gap-4 rounded-2xl border border-white/8 bg-[#0a1020] px-4 py-3"
                  >
                    <span className="text-sm text-white/68">{key.replaceAll("_", " ")}</span>
                    <span className="text-sm font-semibold text-white">{value.toFixed(3)}</span>
                  </div>
                ))}
              </div>

              {result.report.frames_sampled ? (
                <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-sm text-white/68">
                  Frames sampled:{" "}
                  <span className="font-semibold text-white">
                    {result.report.frames_sampled}
                  </span>
                </div>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
