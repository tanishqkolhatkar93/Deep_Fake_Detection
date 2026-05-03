# VeriLens Web

This is the production-facing frontend for the VeriLens public website.

## Stack

- Next.js App Router
- TypeScript
- Tailwind CSS v4
- shadcn-compatible structure
- Framer Motion

## Important paths

- Global styles: `src/app/globals.css`
- UI components: `src/components/ui`
- Utilities: `src/lib/utils.ts`

The component path lives under `src/components/ui` instead of a root-level `/components/ui`
because this app uses Next's `src` layout. It is still the correct shadcn-style location. Keeping
shared primitives in that folder matters because it prevents reusable UI from getting scattered
across feature folders and makes the design system maintainable.

## 21st-style component integration

The imported command-surface component now lives here:

- `src/components/ui/animated-ai-chat.tsx`

It was adapted to the VeriLens workflow so the commands route users to the scanner, API docs, and
architecture sections rather than behaving like a generic chat toy.

## Local development

```bash
npm ci
npm run dev
```

## Validation

```bash
npm run lint
npm run build
```
