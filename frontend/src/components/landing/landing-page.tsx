import Link from "next/link";
import {
  Search,
  Boxes,
  GitMerge,
  LineChart,
  ArrowRight,
  ExternalLink,
  Globe2,
} from "lucide-react";
import { EuropeMotif } from "@/components/landing/europe-motif";

const COUNTRIES = [
  "Spain",
  "France",
  "Germany",
  "Italy",
  "Poland",
  "Netherlands",
  "Sweden",
  "Hungary",
  "Portugal",
  "Greece",
];

const CORE_TOPICS = ["Immigration", "Climate Change", "Gender Issues"];
const PLATFORMS = ["Twitter / X", "Telegram", "Online Media"];

const FEATURES = [
  {
    icon: Search,
    title: "Faceted search",
    body: "Carve out collections from a multilingual corpus by date, country, platform, topic and subtopic — a Media Cloud-style entry point into the data.",
  },
  {
    icon: Boxes,
    title: "Topic modelling",
    body: "Run BERTopic over a collection to surface latent narratives, with multilingual embeddings and topic labels drafted by a language model.",
  },
  {
    icon: GitMerge,
    title: "Expert-in-the-loop",
    body: "Reconcile topics across countries and platforms, then edit, merge and validate them by hand before annotating documents and training a classifier.",
  },
  {
    icon: LineChart,
    title: "Narrative visualisation",
    body: "Track how topics evolve over time, compare languages and platforms, and surface the most central entities and the most relevant documents.",
  },
];

const PIPELINE_STEPS = [
  { n: "1", label: "Search" },
  { n: "2", label: "Topic Modelling" },
  { n: "3", label: "Label Dataset" },
  { n: "4", label: "Visualise" },
];

export function LandingPage() {
  return (
    <div className="min-h-screen bg-white text-ink">
      {/* Top navigation */}
      <header className="sticky top-0 z-20 border-b border-border bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <div className="flex items-baseline gap-2">
            <span className="text-lg font-semibold tracking-tight text-acteu-red">
              ActEU
            </span>
            <span className="text-sm text-muted-foreground">Narrative Tracker</span>
          </div>
          <nav className="flex items-center gap-5 text-sm">
            <a
              href="https://acteu.org/"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden items-center gap-1 text-muted-foreground transition-colors hover:text-ink sm:inline-flex"
            >
              ActEU project
              <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
            </a>
            <Link
              href="/login"
              className="inline-flex h-9 items-center rounded-md bg-acteu-red px-4 font-medium text-white transition-colors hover:bg-acteu-red-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-acteu-red"
            >
              Log in
            </Link>
          </nav>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="relative overflow-hidden border-b border-border">
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.07]"
            aria-hidden="true"
          >
            <EuropeMotif className="absolute right-[-6rem] top-1/2 h-[42rem] w-[42rem] -translate-y-1/2 text-acteu-red" />
          </div>
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-acteu-red to-transparent" />

          <div className="relative mx-auto grid max-w-6xl gap-12 px-6 py-20 md:grid-cols-[1.15fr_1fr] md:items-center md:py-28">
            <div>
              <span className="inline-flex items-center gap-2 rounded-full border border-acteu-red/30 bg-acteu-red/5 px-3 py-1 text-xs font-medium text-acteu-red">
                <Globe2 className="h-3.5 w-3.5" aria-hidden="true" />
                Trust, legitimacy &amp; polarisation in European democracies
              </span>

              <h1 className="mt-6 text-4xl font-semibold leading-[1.1] tracking-tight md:text-5xl">
                Discover and track{" "}
                <span className="text-acteu-red">emerging narratives</span> across
                European media.
              </h1>

              <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted-foreground">
                A research tool for the European{" "}
                <span className="font-medium text-ink">ActEU</span> project that turns a
                multilingual, multi-platform corpus of political discourse into an
                explorable map of narratives — combining clustering, topic modelling and
                language models with expert validation.
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-4">
                <Link
                  href="/login"
                  className="inline-flex h-12 items-center gap-2 rounded-md bg-acteu-red px-6 text-base font-medium text-white transition-colors hover:bg-acteu-red-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-acteu-red"
                >
                  Log in to the tool
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
                <a
                  href="#how-it-works"
                  className="inline-flex h-12 items-center rounded-md border border-border px-6 text-base font-medium text-ink transition-colors hover:bg-bg"
                >
                  See how it works
                </a>
              </div>
            </div>

            {/* Stat panel */}
            <div className="relative">
              <div className="rounded-xl border border-border bg-white p-6 shadow-sm">
                <p className="text-sm font-medium text-muted-foreground">
                  At a glance
                </p>
                <dl className="mt-4 grid grid-cols-3 gap-4 text-center">
                  {[
                    { v: "10", l: "Countries" },
                    { v: "3", l: "Platforms" },
                    { v: "3", l: "Core topics" },
                  ].map((s) => (
                    <div key={s.l} className="rounded-lg bg-bg py-4">
                      <dt className="text-3xl font-semibold text-acteu-red">{s.v}</dt>
                      <dd className="mt-1 text-xs text-muted-foreground">{s.l}</dd>
                    </div>
                  ))}
                </dl>
                <div className="mt-5 space-y-3 text-sm">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Platforms
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {PLATFORMS.map((p) => (
                        <span
                          key={p}
                          className="rounded-full bg-ink/5 px-3 py-1 text-xs font-medium text-ink"
                        >
                          {p}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Core topics
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {CORE_TOPICS.map((t) => (
                        <span
                          key={t}
                          className="rounded-full bg-acteu-red/10 px-3 py-1 text-xs font-medium text-acteu-red"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* About ActEU */}
        <section className="border-b border-border bg-bg">
          <div className="mx-auto max-w-6xl px-6 py-16 md:py-20">
            <div className="grid gap-10 md:grid-cols-[1fr_1.4fr] md:items-start">
              <h2 className="text-2xl font-semibold tracking-tight md:text-3xl">
                Part of the ActEU research project
              </h2>
              <div className="space-y-4 text-base leading-relaxed text-muted-foreground">
                <p>
                  <span className="font-medium text-ink">ActEU</span> is a European
                  research initiative studying trust, legitimacy and polarisation in
                  contemporary European democracies. It works with discourse drawn from
                  social media, digital press and institutional sites across ten European
                  countries.
                </p>
                <p>
                  The Narrative Tracker is the analytical instrument built on top of that
                  data: it lets researchers and communication professionals move from a
                  raw, multilingual corpus to validated, human-refined narratives that can
                  be explored dynamically — in both academic and professional settings.
                </p>
                <a
                  href="https://acteu.org/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 font-medium text-acteu-red hover:underline"
                >
                  Visit acteu.org
                  <ExternalLink className="h-4 w-4" aria-hidden="true" />
                </a>
              </div>
            </div>
          </div>
        </section>

        {/* Features */}
        <section id="how-it-works" className="border-b border-border">
          <div className="mx-auto max-w-6xl px-6 py-16 md:py-24">
            <div className="max-w-2xl">
              <h2 className="text-2xl font-semibold tracking-tight md:text-3xl">
                From raw discourse to refined narratives
              </h2>
              <p className="mt-4 text-base leading-relaxed text-muted-foreground">
                Every step keeps a human expert in control. Automated techniques propose;
                researchers refine, label and validate.
              </p>
            </div>

            <div className="mt-12 grid gap-6 sm:grid-cols-2">
              {FEATURES.map(({ icon: Icon, title, body }) => (
                <article
                  key={title}
                  className="group rounded-xl border border-border bg-white p-6 transition-shadow hover:shadow-sm"
                >
                  <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-acteu-red/10 text-acteu-red">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <h3 className="mt-4 text-lg font-semibold">{title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                    {body}
                  </p>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* Pipeline */}
        <section className="border-b border-border bg-bg">
          <div className="mx-auto max-w-6xl px-6 py-16 md:py-20">
            <h2 className="text-2xl font-semibold tracking-tight md:text-3xl">
              A guided, four-stage pipeline
            </h2>
            <p className="mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground">
              Work happens inside a project, so the original corpus is never altered.
              Labels and classifiers live with the project.
            </p>

            <ol className="mt-12 grid gap-4 md:grid-cols-7 md:items-center">
              {PIPELINE_STEPS.map((step, i) => (
                <li
                  key={step.label}
                  className="contents"
                >
                  <div className="flex items-center gap-4 rounded-xl border border-border bg-white p-5 md:col-span-1 md:flex-col md:gap-3 md:text-center">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-acteu-red text-sm font-semibold text-white">
                      {step.n}
                    </span>
                    <span className="text-sm font-medium leading-tight">
                      {step.label}
                    </span>
                  </div>
                  {i < PIPELINE_STEPS.length - 1 && (
                    <div
                      className="mx-auto hidden h-px w-full bg-gradient-to-r from-acteu-red/60 to-acteu-red/20 md:block"
                      aria-hidden="true"
                    />
                  )}
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* Coverage */}
        <section className="border-b border-border">
          <div className="mx-auto max-w-6xl px-6 py-16 md:py-20">
            <div className="flex items-center gap-3">
              <Globe2 className="h-6 w-6 text-acteu-red" aria-hidden="true" />
              <h2 className="text-2xl font-semibold tracking-tight md:text-3xl">
                Ten countries, one corpus
              </h2>
            </div>
            <p className="mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground">
              Political discourse spanning ten European democracies and multiple
              languages, analysed side by side.
            </p>
            <ul className="mt-10 flex flex-wrap gap-3">
              {COUNTRIES.map((c) => (
                <li
                  key={c}
                  className="rounded-full border border-border bg-white px-4 py-2 text-sm font-medium text-ink"
                >
                  {c}
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* Final CTA */}
        <section className="bg-acteu-red">
          <div className="mx-auto flex max-w-6xl flex-col items-center gap-6 px-6 py-16 text-center text-white md:py-20">
            <h2 className="max-w-2xl text-2xl font-semibold tracking-tight md:text-3xl">
              Ready to explore the narratives shaping European debate?
            </h2>
            <p className="max-w-xl text-white/85">
              Sign in with your researcher credentials to start building collections and
              tracking topics.
            </p>
            <Link
              href="/login"
              className="inline-flex h-12 items-center gap-2 rounded-md bg-white px-6 text-base font-medium text-acteu-red transition-colors hover:bg-white/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
            >
              Log in to the tool
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-10 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-semibold text-acteu-red">ActEU Narrative Tracker</p>
            <p className="mt-1">
              Bachelor&apos;s Thesis (TFG) developed within the European ActEU project.
            </p>
          </div>
          <a
            href="https://acteu.org/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 transition-colors hover:text-ink"
          >
            acteu.org
            <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
          </a>
        </div>
      </footer>
    </div>
  );
}
