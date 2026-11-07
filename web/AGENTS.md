# web/: front end rules

React 19 + Tailwind v4 on [strata-react](https://github.com/jburnhams/strata-react) (`github:` dependency pinned to a commit in `package.json`; bump the hash to upgrade). Read `DESIGN.md` first, and strata-react's `CLAUDE.md` for its conventions.

- There are no local UI primitives. Button, Status, Metric, PageHeader, DataView, DataTable, LineChart, EmptyState, Skeleton come from `strata-react`; use them (and its other components) before writing markup, and put a gap in a strata-react issue rather than copying a component back in here.
- `className` at call sites is for layout only. Colour, type and radius come from tokens: `app/theme.generated.css` (palette.mjs, never hand-edited) and `app/globals.css` (status roles and the font). `strata-react/strata.css` supplies the namespace reset, type steps, motion and base layer; `@source` in `globals.css` lets Tailwind see the library's classes.
- `main.tsx` wraps the app in `ThemeProvider` (owns `.dark`), `StrataQueryProvider` and a `BrowserRouter` (DataTable keeps its sort in the URL). Remote reads go through TanStack Query (`use-status.ts`) into `DataView`.
- Numbers and times go through `lib/format.ts`. Every status has a word.
- The server owns the data: it samples `/proc`, computes the finding and serves `/_home/api/status`. The UI only draws it and polls every 5 s (paused while the tab is hidden).
- `npm run check` (typecheck + build) and, with `UX_RESEARCH=<checkout of jburnhams/ux-research>`, `npm run lint` (slop-lint, operate mode). **`dist/` is committed**: rebuild it (`npm run build`) in the same commit as any change under `web/`, because the home server runs it without Node.
- Tests: `npm test` (Vitest + Testing Library + jsdom + MSW, `renderWithStrata` from `strata-react/testing`). Put the server into a state with `server.use(...)`, never `vi.mock` or a `fetch` stub. Visual regression with `strata-visual` is not set up yet (homepage issue #3).
