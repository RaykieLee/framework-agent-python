---
description: Frontend conventions for Next.js
globs: ["frontend/**/*.ts", "frontend/**/*.tsx", "frontend/**/*.css"]
---

# 前端约定

## 技术栈

- Next.js 15 with App Router
- TypeScript strict mode
- Tailwind CSS for styling
- i18n support built-in

## 结构

- Pages in `frontend/src/app/` following Next.js App Router conventions
- Reusable components in `frontend/src/components/`
- API client functions in `frontend/src/lib/`
- Types in `frontend/src/types/`

## 约定

- Use `"use client"` directive only when component needs client-side interactivity
- Prefer Server Components by default
- Use `fetch` with proper error handling for API calls
- Keep components small and focused — extract when a component exceeds ~100 lines
