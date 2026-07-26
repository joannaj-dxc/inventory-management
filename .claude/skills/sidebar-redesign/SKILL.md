---
name: sidebar-redesign
description: Redesign this app's UI shell into a modern SaaS-style layout with a vertical left sidebar nav, a consistent spacing scale, and polished visual details across every view. Use when asked to modernize the UI, replace the top nav with a sidebar, or do a visual/design overhaul of the app.
---

# Sidebar Redesign

Turn the current top-nav layout into a modern SaaS shell: fixed vertical sidebar on the left, slim utility bar on the right, one consistent spacing/type scale applied everywhere. This is a layout and polish pass, not a rewrite — the data-loading patterns, API calls, and business logic in every view stay untouched.

## Non-negotiables

- **Every `.vue` file create/edit MUST be delegated to the `vue-expert` subagent** — this is a mandatory project rule (root `CLAUDE.md`), not optional here.
- **No new npm dependencies without asking first.** `client/package.json` currently has only `vue`, `vue-router`, `axios` — no icon library, no `@vueuse/core`, no CSS framework. Build icons as inline SVG (stroke icons, `currentColor`, ~20px) rather than pulling in a package. If a dependency genuinely seems worth it, stop and ask — don't add it silently (root `CLAUDE.md` also flags this repo as public, so any new dependency is a real, visible decision).
- **Keep the i18n contract intact.** Every nav label and any new UI copy goes through `t()` from `useI18n()` (see `client/src/composables/useI18n.js`) with matching keys added to **both** `client/src/locales/en.js` and `ja.js`. A redesign that leaves Japanese mode showing raw keys or English text is incomplete.
- **Preserve existing conventions** from `client/CLAUDE.md`: Composition API only (no `<script setup>`, no Options API), loading/error/data ref pattern, unique `:key` in `v-for`, computed for derived data. Note: that file's debounce example (`watchDebounced` from `@vueuse/core`) does not apply — that package isn't installed; use manual `setTimeout`/`clearTimeout` if a redesign step needs debouncing.
- **Comment non-obvious logic** — standing project rule. Layout/z-index tricks, sidebar active-state logic, or anything not self-evident from the code gets a short WHY comment.

## Current state (re-verify with `ls`/`Read` before relying on this — it drifts)

- Shell lives in `client/src/App.vue`: a sticky `.top-nav` header with logo, a horizontal `.nav-tabs` (router-links), `<LanguageSwitcher />`, `<ProfileMenu />`, then `<FilterBar />` below the header, then `<router-view>` inside `.main-content`.
- Routes (`client/src/main.js`): `/` (Dashboard), `/inventory`, `/orders`, `/demand`, `/spending`, `/reports`, `/restocking`. `Backlog.vue` exists in `views/` but is currently unrouted — leave that as-is unless asked.
- Global design tokens already established in `App.vue`'s `<style>` block (not yet CSS custom properties — just repeated literals): text `#0f172a`, secondary text `#64748b`, borders `#e2e8f0`, page background `#f8fafc`, accent/active `#2563eb`, plus status colors on `.badge`/`.stat-card` (`success` #059669/#d1fae5, `warning` #ea580c/#fed7aa, `danger` #dc2626/#fecaca, `info` #2563eb/#dbeafe). Shared structural classes used by every view: `.page-header`, `.stats-grid` + `.stat-card`, `.card` + `.card-header` + `.card-title`, `.table-container` + table/`th`/`td`, `.badge`.
- No spacing scale exists — paddings/margins are hand-picked rem values repeated per-component (`1.25rem`, `0.875rem`, `1.5rem`, etc.), which is exactly what "consistent spacing" in this task needs to fix.
- Views today: `Dashboard.vue`, `Inventory.vue`, `Orders.vue`, `Demand.vue`, `Spending.vue`, `Reports.vue`, `Restocking.vue` (Backlog.vue, unrouted). Sizes range from ~150 to ~1270 lines — re-`ls`/`wc -l` before planning agent work so effort is sized correctly.

## Design plan to lock in before touching code

Don't skip straight to editing files — first decide and write down (in your response to the user, not a new file, unless they ask for one):

1. **Color tokens as CSS custom properties.** Promote the existing slate/blue palette above to `:root` variables (e.g. `--color-text`, `--color-text-secondary`, `--color-border`, `--color-bg`, `--color-accent`, plus the four status colors) instead of repeated literals. Reuse the existing hex values — this task is about structure and consistency, not a new brand.
2. **Spacing scale.** Define a small numeric scale as custom properties, e.g. `--space-1: 0.25rem` through `--space-8: 3rem` (4px base grid), and go through every view replacing ad hoc padding/margin/gap values with the nearest scale step. Flag any place where the existing value doesn't cleanly map (don't force it — pick the closest reasonable step).
3. **Sidebar shape.** Fixed width (~240–260px), full viewport height, `position: sticky` or `fixed`. Contents top-to-bottom: logo/brand (reuse `nav.companyName`/`nav.subtitle` copy), nav items (icon + label, one per route, translated), nothing else load-bearing — utility controls (filters, language, profile) move to a slim top bar in the remaining column, not into the sidebar.
4. **Icons.** One small inline-SVG icon per nav item (outline/stroke style, 20×20, `stroke="currentColor"`, `stroke-width="1.5"`–`2`) — simple enough to hand-author (grid/dashboard icon, box/inventory, cart/orders, chart/demand, wallet/spending, document/reports, refresh/restocking). Keep them as tiny inline `<svg>` in the sidebar component, not a new icon library.
5. **Active/hover state.** Replace the current underline-on-active pattern (`.nav-tabs a.active::after`) with something suited to a vertical rail — a left accent bar, filled pill background, or both — using the accent token.
6. **Top bar.** What's left of `.top-nav` after the nav-tabs move out: keep `<FilterBar />`, `<LanguageSwitcher />`, `<ProfileMenu />` together in one slim horizontal bar at the top of the content column, not full-width across the sidebar.

If any of these choices are genuinely ambiguous for the specific ask (e.g. collapsible sidebar vs. fixed, icon set style), ask the user once via a short question rather than guessing — but don't ask about things this file already answers.

## Execution order

Stage the work so `vue-expert` isn't handed the whole app at once:

1. **Shell first.** New `client/src/components/Sidebar.vue` + restructured `client/src/App.vue` (flex row: sidebar + content column with top bar and `<router-view>`). Get this rendering correctly with the existing views unchanged before touching per-view spacing — this is the highest-risk step (layout regressions affect every page).
2. **Design tokens.** Move the color palette (and introduce the spacing scale) into `:root` custom properties in `App.vue`'s global `<style>` block; update the shell and shared classes (`.page-header`, `.stats-grid`, `.card`, `.badge`, table styles) to consume the new spacing variables.
3. **Per-view spacing pass.** One `vue-expert` call per view (or small batches for the smaller ones — `Backlog.vue`, `Restocking.vue`, `Demand.vue`, `Inventory.vue` are similar sizes and could be grouped) auditing scoped `<style>` blocks for one-off spacing values and swapping in scale tokens. Don't touch script logic or template structure beyond what layout/spacing requires.
4. **i18n.** Add/adjust any new `nav.*` copy needs in both `en.js` and `ja.js` — likely none beyond what already exists, since nav labels aren't changing, just their container.

## Verification

Use Playwright MCP tools (`http://localhost:3000`) after the shell lands and again after the full pass:
- Every route renders inside the new shell with no layout breakage (check the largest view, `Dashboard.vue`, and the smallest, `Backlog.vue`, as bookends).
- Active nav item highlights correctly per route; hover states work.
- Toggle to Japanese via `LanguageSwitcher` and revisit a few pages — no raw i18n keys, sidebar labels translate.
- Resize the viewport down (e.g. 1280px, 1024px) — sidebar + content shouldn't break; this app has no existing mobile breakpoint handling, so match whatever level of responsiveness the rest of the app already has rather than inventing a new standard.
- Check the browser console for new errors introduced by the restructure.
- Confirm `FilterBar` filters still apply to page data (the shell move shouldn't change how `useFilters()` wires into views).
