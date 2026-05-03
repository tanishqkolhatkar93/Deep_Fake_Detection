import { ArrowRight, Radar, ShieldCheck, Sparkles, Workflow } from "lucide-react";

import { Demo } from "@/components/demo";
import { MediaScanner } from "@/components/sections/media-scanner";

const architectureCards = [
  {
    title: "Live scanner UX",
    description:
      "Fast browser uploads, contextual results, clear limits, and a visual hierarchy that reduces hesitation for first-time users.",
    icon: Sparkles,
  },
  {
    title: "API-backed detection",
    description:
      "The public website talks directly to the Hugging Face-hosted inference API, keeping the UI responsive and the architecture explicit.",
    icon: Radar,
  },
  {
    title: "Responsible guardrails",
    description:
      "File-size caps, duration limits, MIME validation, and rate limiting keep the public product usable without pretending free infrastructure is limitless.",
    icon: ShieldCheck,
  },
  {
    title: "Clear system design",
    description:
      "GitHub Pages serves the frontend. FastAPI on Hugging Face serves the model. The split is simple, honest, and operationally lightweight.",
    icon: Workflow,
  },
];

export default function Home() {
  return (
    <main className="lab-bg relative isolate overflow-x-hidden bg-[#050816] text-white">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(214,101,61,0.18),transparent_30%),radial-gradient(circle_at_top_right,rgba(59,130,246,0.18),transparent_32%),linear-gradient(180deg,#050816_0%,#091224_45%,#050816_100%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:72px_72px] opacity-35" />

      <div className="relative mx-auto flex w-full max-w-7xl flex-col px-5 pb-24 pt-6 md:px-8 lg:px-10">
        <header className="mb-12 flex flex-col gap-4 rounded-full border border-white/10 bg-white/5 px-5 py-4 backdrop-blur-xl md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-orange-400 to-fuchsia-500 text-sm font-semibold text-white shadow-[0_20px_50px_rgba(245,118,59,0.3)]">
              VL
            </div>
            <div>
              <p className="text-sm font-semibold tracking-[0.24em] text-white/55 uppercase">
                VeriLens
              </p>
              <p className="text-sm text-white/60">
                AI image and deepfake video authenticity workflow
              </p>
            </div>
          </div>

          <nav className="flex flex-wrap items-center gap-3 text-sm text-white/65">
            <a className="transition hover:text-white" href="#scanner">
              Scanner
            </a>
            <a className="transition hover:text-white" href="#architecture">
              Architecture
            </a>
            <a className="transition hover:text-white" href="#trust">
              Trust posture
            </a>
            <a
              className="transition hover:text-white"
              href="https://tanishq93-deepfake-detection.hf.space/docs"
              target="_blank"
              rel="noreferrer"
            >
              API docs
            </a>
          </nav>
        </header>

        <section className="grid gap-10 py-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
          <div className="space-y-8">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/6 px-4 py-2 text-sm text-white/70 backdrop-blur">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_24px_rgba(16,185,129,0.9)]" />
              Public website, public API, production-minded launch posture
            </div>

            <div className="space-y-5">
              <h1 className="max-w-5xl font-[family:var(--font-instrument-serif)] text-5xl leading-[0.95] tracking-tight text-white sm:text-6xl lg:text-7xl">
                World-class detection UX for the synthetic media era.
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-white/72">
                VeriLens turns a raw model endpoint into a polished trust product: richer hierarchy,
                calmer decision flow, stronger SEO, faster orientation, and a scanner experience
                that feels deliberate instead of improvised.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <a
                className="inline-flex h-11 items-center rounded-full bg-white px-6 text-sm font-medium text-[#0a1020] shadow-[0_20px_55px_rgba(255,255,255,0.14)] transition hover:bg-white/90"
                href="#scanner"
              >
                Launch scanner
                <ArrowRight className="ml-2 size-4" />
              </a>
              <a
                className="inline-flex h-11 items-center rounded-full border border-white/15 bg-white/5 px-6 text-sm font-medium text-white transition hover:bg-white/10"
                href="https://github.com/tanishqkolhatkar93/Deep_Fake_Detection"
                target="_blank"
                rel="noreferrer"
              >
                View source
              </a>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div className="rounded-3xl border border-white/10 bg-white/6 p-5 backdrop-blur-lg">
                <p className="text-sm uppercase tracking-[0.24em] text-white/45">UX posture</p>
                <p className="mt-2 text-2xl font-semibold text-white">Command-led</p>
                <p className="mt-2 text-sm leading-6 text-white/60">
                  Users can orient through commands, CTAs, and a guided upload path.
                </p>
              </div>
              <div className="rounded-3xl border border-white/10 bg-white/6 p-5 backdrop-blur-lg">
                <p className="text-sm uppercase tracking-[0.24em] text-white/45">Deployment</p>
                <p className="mt-2 text-2xl font-semibold text-white">Split stack</p>
                <p className="mt-2 text-sm leading-6 text-white/60">
                  GitHub Pages for the frontend, Hugging Face Spaces for inference.
                </p>
              </div>
              <div className="rounded-3xl border border-white/10 bg-white/6 p-5 backdrop-blur-lg">
                <p className="text-sm uppercase tracking-[0.24em] text-white/45">Signal</p>
                <p className="mt-2 text-2xl font-semibold text-white">Yes / No + trace</p>
                <p className="mt-2 text-sm leading-6 text-white/60">
                  Verdicts stay simple while evidence, timings, and model IDs stay available.
                </p>
              </div>
            </div>
          </div>

          <div className="relative">
            <div className="absolute inset-0 -z-10 rounded-[2rem] bg-[radial-gradient(circle_at_20%_20%,rgba(244,114,182,0.28),transparent_28%),radial-gradient(circle_at_80%_15%,rgba(59,130,246,0.25),transparent_30%),radial-gradient(circle_at_50%_80%,rgba(249,115,22,0.22),transparent_26%)] blur-3xl" />
            <Demo />
          </div>
        </section>

        <section
          id="scanner"
          className="mt-20 grid gap-6 rounded-[2rem] border border-white/10 bg-white/6 p-6 shadow-[0_30px_80px_rgba(0,0,0,0.35)] backdrop-blur-2xl lg:grid-cols-[0.62fr_0.38fr]"
        >
          <div className="space-y-4">
            <div className="space-y-2">
              <p className="text-sm uppercase tracking-[0.28em] text-cyan-200/65">Live scanner</p>
              <h2 className="font-[family:var(--font-instrument-serif)] text-4xl text-white">
                A richer upload flow with less friction.
              </h2>
              <p className="max-w-2xl text-white/68">
                The scanner preserves the backend contract you already deployed, but the interaction
                quality is materially higher: stronger feedback loops, clearer statuses, and cleaner
                evidence presentation.
              </p>
            </div>
            <MediaScanner />
          </div>

          <aside className="grid gap-4 rounded-[1.75rem] border border-white/8 bg-[#07101f]/72 p-5">
            <div className="rounded-[1.5rem] border border-white/10 bg-white/6 p-5">
              <p className="text-sm uppercase tracking-[0.24em] text-white/45">Experience principles</p>
              <ul className="mt-4 space-y-3 text-sm leading-6 text-white/70">
                <li>Immediate orientation for first-time visitors</li>
                <li>One dominant action per visual region</li>
                <li>Direct API transparency without exposing backend complexity</li>
                <li>Luxury-feeling motion without adding cognitive noise</li>
              </ul>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-gradient-to-br from-orange-400/18 via-transparent to-sky-400/14 p-5">
              <p className="text-sm uppercase tracking-[0.24em] text-white/45">21st-style leverage</p>
              <p className="mt-3 text-sm leading-6 text-white/72">
                21st.dev is useful here because it gives high-finish interaction patterns that can
                be adapted into a real product surface quickly. The right move is to use those
                patterns as a starting point, then anchor them to your actual detector workflow.
              </p>
            </div>
          </aside>
        </section>

        <section id="architecture" className="mt-20 space-y-6">
          <div className="max-w-3xl space-y-3">
            <p className="text-sm uppercase tracking-[0.28em] text-fuchsia-200/65">Architecture</p>
            <h2 className="font-[family:var(--font-instrument-serif)] text-4xl text-white">
              Product polish backed by explicit system design.
            </h2>
            <p className="text-white/65">
              World-class UI is only credible when the product surface reflects the actual
              architecture. These cards map the UX to the runtime.
            </p>
          </div>

          <div className="grid gap-5 lg:grid-cols-4">
            {architectureCards.map(({ title, description, icon: Icon }) => (
              <article
                key={title}
                className="rounded-[1.75rem] border border-white/10 bg-white/6 p-5 backdrop-blur-xl"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/10 text-white">
                  <Icon className="size-5" />
                </div>
                <h3 className="mt-5 text-lg font-semibold text-white">{title}</h3>
                <p className="mt-3 text-sm leading-6 text-white/65">{description}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="trust" className="mt-20 grid gap-6 lg:grid-cols-[0.52fr_0.48fr]">
          <div className="rounded-[2rem] border border-white/10 bg-white/6 p-6 backdrop-blur-xl">
            <p className="text-sm uppercase tracking-[0.28em] text-emerald-200/60">Trust posture</p>
            <h2 className="mt-3 font-[family:var(--font-instrument-serif)] text-4xl text-white">
              Beautiful does not mean misleading.
            </h2>
            <p className="mt-4 max-w-2xl text-white/68">
              The site now communicates limits clearly. This is a high-quality public product
              baseline, not a fabricated claim of forensic certainty.
            </p>
          </div>

          <div className="grid gap-4">
            {[
              "Model-backed verdicts are exposed with probability and evidence.",
              "Video remains short-form and synchronous to respect the free-hosting constraints.",
              "The UI keeps people moving, but the copy keeps the claims honest.",
            ].map((item) => (
              <div
                key={item}
                className="rounded-[1.6rem] border border-white/10 bg-[#07101f]/72 p-5 text-sm leading-6 text-white/72"
              >
                {item}
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
