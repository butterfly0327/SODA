# Frontend Feature Modules (Phase 1 Scaffold)

This directory is an additive scaffold for incremental frontend refactoring.

## Goal

- Keep route/page UX unchanged.
- Move domain logic from page files into feature modules gradually.
- Preserve backend API contracts while refactoring structure.

## Dependency Rules

- `app/pages` can import from `app/features` and `app/shared`.
- `app/features` can import from `app/shared` and `src/api`.
- `app/shared` must not import from `app/pages` or `app/features`.
- Adapter files should stay pure (no React hooks, no store mutation).

## Migration Order

1. Search
2. Bookmark
3. MyPage
4. Community

Each step should keep behavior identical and pass diagnostics/build.
