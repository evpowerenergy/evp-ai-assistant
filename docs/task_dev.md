# Task Dev: Whole-System Dark Mode + UI Rework

Date: 2026-03-20
Project: `evp-ai-assistant` (Next.js 14 + Tailwind)

## 1) Goal
Rework UI to support Dark Mode across the entire frontend (chat, admin console, auth pages, shared UI components) with consistent contrast and readable layout.

## 2) Current State (Observed)
1. `frontend/src/app/globals.css` defines `--background` and `--foreground` using `@media (prefers-color-scheme: dark)`.
2. Many components/pages use hardcoded light-only Tailwind classes (e.g. `bg-white`, `bg-gray-50`, `text-gray-*`, `border-gray-*`), so even if background variables change, large parts still look wrong in dark.
3. Tailwind config currently does not explicitly set `darkMode`, so dark styling may rely only on `media` and not support user toggle.

## 3) Target UX / Acceptance Criteria
1. Dark Mode looks intentional (not “inverted” or washed out).
2. User can toggle theme (at least `light` and `dark`); `system` optional.
3. Theme choice persists across refresh (via `localStorage`).
4. No hydration mismatch / flicker on initial load.
5. All major pages remain usable and readable:
   - `/chat`
   - Admin pages under `/admin/*`
   - `/login`
   - Loading / error boundaries / auth callback

## 4) Design Approach (Recommended)
Phase-based to reduce risk:
1. Infrastructure first (theme toggling + class-based dark mode + CSS variables).
2. Apply dark styling to shared layout tokens (background, borders, text).
3. Convert hardcoded UI components page-by-page (start with shared, then chat, then admin).

## 5) Implementation Plan (Detailed Tasks)

### Task A: Dark mode infrastructure (foundation)
Files likely involved:
- `frontend/tailwind.config.ts`
- `frontend/src/app/globals.css`
- `frontend/src/app/layout.tsx`
- New: `frontend/src/contexts/ThemeContext.tsx`
- New: `frontend/src/components/ui/ThemeToggle.tsx` (or similar)

Tasks:
1. Update Tailwind to use class-based dark mode:
   - Set `darkMode: 'class'` in `tailwind.config.ts`.
2. Update CSS variables to be driven by `.dark` class (not only media query):
   - In `globals.css`, define light values in `:root`.
   - Add `.dark { ... }` overrides for dark values.
3. Create ThemeContext:
   - Theme state: `light | dark | system` (system optional).
   - Read initial theme from `localStorage`.
   - If `system`, set based on `matchMedia('(prefers-color-scheme: dark)')`.
4. Apply theme at runtime:
   - `document.documentElement.classList.toggle('dark', theme === 'dark')`
   - Avoid flicker by setting the class as early as possible (via inline script or early client boot).
5. Add a toggle UI:
   - Place theme toggle where it’s accessible (suggest: top-right in main header, and login page).
6. Wrap the app with ThemeProvider:
   - Add ThemeProvider around existing providers (currently `AuthProvider`) in `src/app/layout.tsx`.

Task A checklist (status):
- [x] Set `darkMode: 'class'` in `frontend/tailwind.config.ts`.
- [x] Replace media-only dark setup with `.dark`-driven CSS variables in `frontend/src/app/globals.css`.
- [x] Add semantic color tokens in Tailwind config (`card`, `border`, `muted`, `input`, `ring`).
- [x] Create `frontend/src/contexts/ThemeContext.tsx` with:
  - [x] `light | dark | system` state
  - [x] localStorage persistence (`evp-ai-assistant-theme`)
  - [x] system theme detection via `matchMedia`
  - [x] runtime class toggle on `document.documentElement`
- [x] Add anti-flicker init script in `frontend/src/app/layout.tsx` and set `suppressHydrationWarning` on `<html>`.
- [x] Wrap app with `ThemeProvider` in `frontend/src/app/layout.tsx`.
- [x] Create `frontend/src/components/ui/ThemeToggle.tsx`.
- [x] Add Theme toggle in:
  - [x] `frontend/src/app/(dashboard)/chat/page.tsx`
  - [x] `frontend/src/app/(auth)/login/page.tsx`
- [x] Smoke test route status: `/chat` = 200, `/login` = 200.
- [!] Lint command status: `npm run lint` prompted interactive Next.js ESLint setup and was stopped (no auto lint result yet).

Definition of done:
- Toggle changes theme immediately.
- Refresh preserves the selection.
- No visible layout flicker on first paint.

### Task B: Replace hardcoded light-only tokens (shared baseline)
Goal:
1. Ensure background/text/borders follow the chosen theme.
2. Reduce the number of future fixes by establishing semantic tokens.

Tasks:
1. Extend CSS variables beyond `--background` / `--foreground`:
   - Examples to add: `--card`, `--card-foreground`, `--border`, `--muted`, `--muted-foreground`, `--input`, `--ring`, `--accent`.
2. Update Tailwind theme extension:
   - Map `bg-background`, `text-foreground`, `border-border`, etc.
3. Update `body` and top-level containers:
   - Replace `bg-gray-50` / `bg-white` where possible with `bg-background` / `text-foreground`.

Task B checklist (status):
- [x] Extend CSS variables beyond `--background` / `--foreground` in `frontend/src/app/globals.css`.
- [x] Map semantic colors in Tailwind (`card`, `border`, `muted`, `input`, `ring`).
- [x] Apply shared baseline tokens to top-level pages:
  - [x] `frontend/src/app/(dashboard)/chat/page.tsx`
  - [x] `frontend/src/app/(auth)/login/page.tsx`
  - [x] `frontend/src/app/page.tsx`
  - [x] `frontend/src/app/(auth)/callback/page.tsx`
- [x] Apply shared baseline tokens to auth/shared UI:
  - [x] `frontend/src/components/auth/ProtectedRoute.tsx`
  - [x] `frontend/src/components/auth/UserProfile.tsx`
  - [x] `frontend/src/components/ui/ErrorBoundary.tsx`
  - [x] `frontend/src/components/ui/Notification.tsx`
  - [x] `frontend/src/components/ui/LoadingSkeleton.tsx`
  - [x] `frontend/src/components/ui/ThemeToggle.tsx`
- [x] Smoke test route status after refactor: `/chat` = 200, `/login` = 200.
- [!] Note: Deep component-level conversion for chat/admin internals is intentionally deferred to Task C and Task E.

Definition of done:
- Overall page background and default text colors look correct in both modes.

### Task C: Chat UI dark conversion (most visible)
Files:
- `frontend/src/components/chat/*` including:
  - `ChatInterface.tsx`
  - `SessionSidebar.tsx`
  - `MessageInput.tsx`
  - `MessageBubble.tsx`
  - `MessageList.tsx`
  - `ProcessStatusPanel.tsx`
  - `FeedbackButtons.tsx`
  - `CitationBadge.tsx`

Tasks:
1. Convert container backgrounds:
   - `bg-gray-50` -> `bg-background`
   - `bg-white` sections -> `bg-card` (or `bg-background` with borders)
2. Convert text + borders:
   - `text-gray-900/600/500` -> `text-foreground` / `text-muted-foreground` (or `dark:` variants)
   - `border-gray-*` -> `border-border`
3. Convert chat bubbles:
   - Assistant bubble should become a dark “card” with proper border and readable text.
   - User bubble (indigo) should keep good contrast in dark.
4. Inputs:
   - Update textarea/background/border for dark and focused states.
5. Process panel:
   - Replace `bg-gray-50/white` sections with themed card backgrounds.
   - Ensure `pre` and debug JSON backgrounds are readable (dark code block).
6. Feedback buttons:
   - Adjust base/hover colors for dark so they remain meaningful and accessible.

Task C checklist (status):
- [x] Convert chat container backgrounds to semantic tokens:
  - [x] `frontend/src/components/chat/ChatInterface.tsx`
  - [x] `frontend/src/components/chat/SessionSidebar.tsx`
  - [x] `frontend/src/components/chat/MessageInput.tsx`
  - [x] `frontend/src/components/chat/ProcessStatusPanel.tsx`
- [x] Convert text and borders to theme-aware tokens in chat components.
- [x] Convert assistant/user message bubble styling for dark readability:
  - [x] `frontend/src/components/chat/MessageBubble.tsx`
  - [x] `frontend/src/components/chat/MessageList.tsx`
- [x] Update input area focus/background/placeholder for dark:
  - [x] `frontend/src/components/chat/MessageInput.tsx`
- [x] Update process panel cards/debug/pre blocks for dark:
  - [x] `frontend/src/components/chat/ProcessStatusPanel.tsx`
- [x] Update feedback and citation visual states:
  - [x] `frontend/src/components/chat/FeedbackButtons.tsx`
  - [x] `frontend/src/components/chat/CitationBadge.tsx`
- [x] Smoke test route status after conversion: `/chat` = 200, `/login` = 200.
- [x] IDE lint check on modified chat files: no issues found.

Definition of done:
- Chat page looks cohesive and readable end-to-end in dark mode.

### Task D: Auth + Error/Loading components dark conversion
Files:
- `frontend/src/app/(auth)/login/page.tsx`
- `frontend/src/app/(auth)/callback/page.tsx`
- `frontend/src/components/auth/ProtectedRoute.tsx`
- `frontend/src/components/auth/UserProfile.tsx`
- `frontend/src/components/ui/ErrorBoundary.tsx`
- `frontend/src/components/ui/Notification.tsx`
- `frontend/src/components/ui/LoadingSkeleton.tsx`

Tasks:
1. Login page:
   - Replace `bg-gray-50` containers and `text-gray-*` input styles with dark equivalents.
2. Loading states:
   - Update spinner container backgrounds/text colors.
3. ProtectedRoute access denied panel:
   - Ensure background/text uses dark-friendly palette.
4. ErrorBoundary:
   - Replace `bg-gray-50` + `text-gray-600` with themed tokens or `dark:` variants.
5. Notification:
   - `bg-green-50/red-50/blue-50` should get dark versions (or semantic tokens).
6. LoadingSkeleton:
   - `bg-gray-200` needs dark counterpart (e.g. `dark:bg-gray-700`).

Task D checklist (status):
- [x] Login page dark conversion:
  - [x] Base container and typography moved to semantic theme tokens.
  - [x] Input fields updated to `bg-input` / `ring-border` / `text-foreground`.
  - [x] Error alert dark style completed (`dark:bg-red-950/50`, `dark:text-red-300`).
- [x] Callback/loading page dark conversion:
  - [x] `frontend/src/app/(auth)/callback/page.tsx`
- [x] ProtectedRoute loading + access-denied states dark conversion:
  - [x] `frontend/src/components/auth/ProtectedRoute.tsx`
- [x] User profile panel conversion:
  - [x] `frontend/src/components/auth/UserProfile.tsx`
- [x] Error boundary conversion:
  - [x] `frontend/src/components/ui/ErrorBoundary.tsx`
- [x] Notification dark variants added:
  - [x] `frontend/src/components/ui/Notification.tsx`
- [x] Loading skeleton dark variant added:
  - [x] `frontend/src/components/ui/LoadingSkeleton.tsx`
- [x] Verification:
  - [x] IDE lint check on changed files: no issues found.
  - [x] Route smoke test: `/login` = 200, `/chat` = 200.

Definition of done:
- Login page and all fallback UIs do not look “white on black” or low contrast.

### Task E: Admin console dark conversion (pages + components)
Files:
- `frontend/src/app/(dashboard)/admin/page.tsx`
- `frontend/src/app/(dashboard)/admin/chat/page.tsx` (if uses light tokens)
- `frontend/src/app/(dashboard)/admin/documents/page.tsx`
- `frontend/src/app/(dashboard)/admin/line/page.tsx`
- `frontend/src/app/(dashboard)/admin/prompt-tests/page.tsx`
- Components:
  - `frontend/src/components/admin/DocumentUpload.tsx`
  - `frontend/src/components/admin/DocumentList.tsx`
  - `frontend/src/components/admin/LineLinking.tsx`
  - `frontend/src/components/admin/LogViewer.tsx`

Tasks:
1. Check each admin page for hardcoded `bg-white` / `text-gray-*` blocks:
   - Convert to `bg-card` and themed text/border tokens.
2. Update admin cards/buttons:
   - Tables and form controls must have dark-friendly borders and row hover states.
3. Ensure any existing dark-looking sections are consistent:
   - Some admin pages already use `bg-gray-800` and `text-gray-100` (keep consistent and avoid mixed styles).

Task E checklist (status):
- [x] Convert admin pages to theme-aware tokens:
  - [x] `frontend/src/app/(dashboard)/admin/page.tsx`
  - [x] `frontend/src/app/(dashboard)/admin/documents/page.tsx`
  - [x] `frontend/src/app/(dashboard)/admin/line/page.tsx`
  - [x] `frontend/src/app/(dashboard)/admin/prompt-tests/page.tsx`
- [x] Convert admin components:
  - [x] `frontend/src/components/admin/DocumentUpload.tsx`
  - [x] `frontend/src/components/admin/DocumentList.tsx`
  - [x] `frontend/src/components/admin/LineLinking.tsx`
  - [x] `frontend/src/components/admin/LogViewer.tsx`
- [x] Update tables/forms/cards in admin to dark-friendly borders, backgrounds, and text.
- [x] Keep existing dark header sections consistent while unifying internal card/table styles.
- [x] Verification:
  - [x] `rg` scan on admin app/components confirms no remaining core light-only tokens (`bg-white`, `bg-gray-50`, `text-gray-*`, `border-gray-*`) in those scopes.
  - [x] IDE lint check on changed admin files: no issues found.
  - [x] Route smoke tests: `/admin` = 200, `/admin/documents` = 200, `/admin/line` = 200, `/admin/prompt-tests` = 200.

Definition of done:
- Admin pages look consistent and usable in dark mode.

### Task F: Final cleanup + consistency pass
Tasks:
1. Global search for hardcoded light-only classes:
   - Targets: `bg-white`, `bg-gray-50`, `bg-gray-100`, `text-gray-600/500/700/900`, `border-gray-*`, `bg-indigo-50`.
2. For each occurrence:
   - Either replace with semantic tokens, or add `dark:` variants.
3. Ensure focus rings remain visible in dark.
4. Run lint:
   - `cd frontend && npm run lint`

Task F checklist (status):
- [x] Global `rg` scan completed for light-only tokens in `frontend/src`.
- [x] Remaining non-intentional token found and fixed:
  - [x] `frontend/src/components/chat/ProcessStatusPanel.tsx` (`bg-gray-100` -> `bg-muted`, indicator -> `bg-muted-foreground`)
- [x] Final `rg` scan now shows only intentional admin dark-header styles:
  - [x] `frontend/src/app/(dashboard)/admin/page.tsx`
  - [x] `frontend/src/app/(dashboard)/admin/prompt-tests/page.tsx`
- [x] Focus ring baseline remains visible in dark (preserved across updated inputs/selects/buttons).
- [!] `npm run lint` remains interactive in this repo (Next.js ESLint setup prompt), so non-interactive full lint run could not be completed in this session.
- [x] Verification smoke tests:
  - [x] `/chat` = 200
  - [x] `/login` = 200
  - [x] `/admin` = 200
- [x] IDE lint diagnostics on changed files: no issues found.

Definition of done:
- `rg` scan shows minimal remaining unhandled light-only classes.

## 6) Development Commands
1. Run dev:
   - `cd frontend && npm run dev`
2. Lint:
   - `cd frontend && npm run lint`
3. Build (optional before release):
   - `cd frontend && npm run build`

## 7) Manual Test Matrix
1. Theme = Light:
   - `/login`
   - `/chat`
   - `/admin`
   - `/admin/documents`
   - `/admin/line`
   - `/admin/prompt-tests`
2. Theme = Dark:
   - same pages as above
3. Theme persistence:
   - change theme -> refresh browser -> verify still selected
4. Responsiveness:
   - mobile sidebar open/close in chat
5. Error states:
   - Trigger access denied and ErrorBoundary (if possible)

## 8) Risks / Notes
1. If class-based dark mode is not implemented (`darkMode: 'class'`), toggling will not work.
2. Hardcoded colors are scattered; a partial approach may create mixed themes. That’s why this plan starts with infrastructure + tokens.
3. Tailwind `dark:` requires class-based configuration and consistent class application.

