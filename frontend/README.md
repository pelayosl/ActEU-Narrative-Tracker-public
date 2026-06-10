# ActEU Narrative Tracker — Frontend

Next.js 14 (App Router) + Tailwind + shadcn/ui + Zustand + TanStack Query + Recharts.

## Structure

```
src/
├── app/                       Next.js App Router routes
│   ├── layout.tsx             Root layout (providers, fonts)
│   ├── page.tsx               Redirects to /pipeline
│   ├── login/page.tsx         Login page (public)
│   └── (app)/                 Protected routes
│       ├── layout.tsx         Sidebar + header shell
│       ├── pipeline/page.tsx  Pipeline (stepper + 3 steps)
│       ├── projects/page.tsx  Project library
│       └── visualiser/page.tsx
├── components/
│   ├── providers.tsx          React Query provider
│   ├── ui/                    shadcn primitives (Button so far)
│   ├── layout/                Sidebar, Header, ProfileMenu
│   ├── auth/                  LoginForm, RegisterDialog
│   ├── projects/              List, SelectorDialog, ApplyClassifierDialog
│   ├── pipeline/              Stepper + step components + form/cards/dialog
│   └── visualiser/            QueryPanel + 4 panels
├── lib/
│   ├── api-client.ts          Typed FastAPI client
│   └── utils.ts               cn() helper
├── stores/                    Zustand stores (project, pipeline)
└── types/api.ts               Mirror of backend Pydantic schemas
```

## Getting started

```bash
cp .env.local.example .env.local
npm install
npm run dev
```

## Incremental build order

1. Install missing `shadcn/ui` primitives as needed (`dialog`, `select`, `checkbox`, `popover`, `progress`).
2. Auth: login + NextAuth wiring → register dialog.
3. Project selector dialog → project store fully wired.
4. Search form + step 1.
5. Step 2 (sub-states + edit/merge/delete) → wire SSE for generation/reconciliation jobs.
6. Step 3 (train + Phase 1/2 labelling).
7. Project library (list, classifier actions, apply dialog).
8. Visualiser (query panel + 4 panels with Recharts).
9. Validation rules and error banner system.
```
