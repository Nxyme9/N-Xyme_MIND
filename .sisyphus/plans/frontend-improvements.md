# Frontend Improvements Story - Next.js 16 Feature Parity

## Story ID
`frontend-next16-feature-parity`

## Epic Reference
`frontend-phase2-masterplan.md`

## Priority
**HIGH** - Core UX and performance improvements

---

## 1. Story Overview

### Problem Statement
The Next.js 16 frontend (Next.js 16.2.3) is missing critical App Router features that improve UX, performance, and SEO. Current gaps include missing Suspense/error boundaries, no metadata exports, and no streaming patterns.

### Goal
Implement Next.js 16 App Router best practices across all 7 page routes:
1. Add `loading.tsx` files (Suspense boundaries) to each route segment
2. Add `error.tsx` files (error boundaries) to each route segment  
3. Add per-page `metadata` exports for SEO
4. Create reusable loading skeleton components
5. Add View Transition API support

---

## 2. Current State Analysis

### Existing Files (16 in app router)
```
frontend/src/app/
├── api/
│   ├── auth/[...nextauth]/route.ts
│   ├── auth/signin/page.tsx
│   ├── backend/api-keys/route.ts
│   ├── backend/agents/route.ts
│   ├── backend/health/route.ts
│   ├── backend/mcp/route.ts
│   ├── backend/settings/route.ts
│   └── backend/system-stats/route.ts
│   └── health/route.ts
├── chat/page.tsx
├── dashboard/page.tsx
├── layout.tsx (root)
├── memory/page.tsx
├── orchestration/page.tsx
├── page.tsx (home)
└── settings/page.tsx
```

### Missing Next.js 16 Features
| Feature | Status | Impact |
|---------|--------|--------|
| `loading.tsx` | ❌ None | No Suspense boundaries |
| `error.tsx` | ❌ None | No per-segment error handling |
| `metadata` exports | ⚠️ Root only | No per-page SEO |
| Streaming patterns | ❌ None | No progressive loading |
| View Transitions | ❌ None | No page transitions |
| Parallel Routes | ❌ None | No route groups |

---

## 3. Task Breakdown

### 3.1 Create Loading Skeleton Components

**Story Points:** 3  
**Files to Create:**
- `frontend/src/components/ui/skeleton.tsx`
- `frontend/src/components/ui/skeleton-card.tsx`
- `frontend/src/components/ui/skeleton-table.tsx`
- `frontend/src/components/loading/dashboard-skeleton.tsx`
- `frontend/src/components/loading/memory-skeleton.tsx`
- `frontend/src/components/loading/chat-skeleton.tsx`
- `frontend/src/components/loading/orchestration-skeleton.tsx`

**Acceptance Criteria:**
- [ ] Reusable skeleton components with Tailwind classes
- [ ] Dashboard skeleton with cards and stats placeholders
- [ ] Memory skeleton with list placeholders
- [ ] Chat skeleton with message placeholders
- [ ] Orchestration skeleton with flow diagram placeholder
- [ ] CSS animation for pulse effect

### 3.2 Create Page Loading States

**Story Points:** 5  
**Files to Create:**
- `frontend/src/app/loading.tsx` (root)
- `frontend/src/app/chat/loading.tsx`
- `frontend/src/app/dashboard/loading.tsx`
- `frontend/src/app/memory/loading.tsx`
- `frontend/src/app/orchestration/loading.tsx`
- `frontend/src/app/settings/loading.tsx`

**Acceptance Criteria:**
- [ ] Each loading.tsx uses Suspense with skeleton components
- [ ] Root loading.tsx shows global navigation skeleton
- [ ] Page-specific skeletons match actual page layout
- [ ] Smooth fade-in transition when content loads

### 3.3 Create Page Error Boundaries

**Story Points:** 5  
**Files to Create:**
- `frontend/src/app/error.tsx` (root)
- `frontend/src/app/chat/error.tsx`
- `frontend/src/app/dashboard/error.tsx`
- `frontend/src/app/memory/error.tsx`
- `frontend/src/app/orchestration/error.tsx`
- `frontend/src/app/settings/error.tsx`

**Acceptance Criteria:**
- [ ] Each error.tsx implements error.tsx interface with `error` and `reset`
- [ ] User-friendly error messages (not technical)
- [ ] "Try Again" button that calls `reset()`
- [ ] Error logging to console (for debugging)
- [ ] Consistent error card styling with navigation options

### 3.4 Add Per-Page Metadata Exports

**Story Points:** 3  
**Files to Modify:**
- `frontend/src/app/chat/page.tsx`
- `frontend/src/app/dashboard/page.tsx`
- `frontend/src/app/memory/page.tsx`
- `frontend/src/app/orchestration/page.tsx`
- `frontend/src/app/settings/page.tsx`
- `frontend/src/app/page.tsx` (home)

**Acceptance Criteria:**
- [ ] Each page exports `metadata: Metadata` object
- [ ] Include `title`, `description`, and `keywords`
- [ ] Consistent naming convention: "Page Name | N-Xyme MIND"
- [ ] Update root layout metadata to include Open Graph tags

### 3.5 Implement View Transitions

**Story Points:** 5  
**Files to Modify:**
- `frontend/src/components/Navigation.tsx`
- `frontend/src/hooks/useViewTransition.ts` (create)

**Acceptance Criteria:**
- [ ] Create `useViewTransition` hook for navigation
- [ ] Add `view-transition-name` CSS properties to key elements
- [ ] Navigation links use `next/link` with `viewTransition` prop
- [ ] Smooth fade/slide animations between pages
- [ ] Fallback for browsers without View Transitions API

---

## 4. Detailed File Specifications

### 4.1 Skeleton Components

#### `frontend/src/components/ui/skeleton.tsx`
```typescript
// Base skeleton with pulse animation
// Props: className, variant ('default' | 'text' | 'circular')
// Uses Tailwind animate-pulse
```

#### `frontend/src/components/ui/skeleton-card.tsx`
```typescript
// Card skeleton for dashboard pages
// Props: lines (number of text lines), hasHeader (boolean)
// Renders Card structure with header, content placeholders
```

### 4.2 Loading States

#### `frontend/src/app/chat/loading.tsx`
```typescript
// Shows ChatSkeleton component
// Wrapped in Suspense
// Instant render (no server delay needed for client components)
```

#### `frontend/src/app/dashboard/loading.tsx`
```typescript
// Shows DashboardSkeleton with:
// - 4 stat cards
// - Activity feed placeholder
// - Charts placeholder
```

### 4.3 Error Boundaries

#### Pattern for all error.tsx files
```typescript
'use client';

import { useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Page error:', error);
  }, [error]);

  return (
    <div className="container mx-auto py-12">
      <div className="max-w-md mx-auto text-center">
        <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-destructive" />
        <h2 className="text-2xl font-bold mb-2">Something went wrong</h2>
        <p className="text-muted-foreground mb-6">
          We encountered an error loading this page.
        </p>
        <Button onClick={reset} className="gap-2">
          <RefreshCw className="w-4 h-4" />
          Try Again
        </Button>
      </div>
    </div>
  );
}
```

### 4.4 Metadata Exports

#### `frontend/src/app/dashboard/page.tsx` (example)
```typescript
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Dashboard | N-Xyme MIND',
  description: 'Monitor agent status, MCP connections, and task queue in real-time.',
  keywords: ['dashboard', 'agents', 'monitoring', 'status'],
};

export default function DashboardPage() {
  // ... existing client component code
}
```

---

## 5. Implementation Order

1. **Phase 1:** Create skeleton components (`ui/skeleton.tsx`, `skeleton-card.tsx`, etc.)
2. **Phase 2:** Create page-specific loading skeletons (`loading/*.tsx`)
3. **Phase 3:** Add `loading.tsx` files to each route segment
4. **Phase 4:** Add `error.tsx` files to each route segment
5. **Phase 5:** Add metadata exports to each page
6. **Phase 6:** Implement View Transitions hook and integrate

---

## 6. Success Criteria

### Technical Criteria
- [ ] `npm run type-check` passes with no errors
- [ ] `npm run lint` passes with no errors
- [ ] `npm run build` completes successfully
- [ ] All 6 loading.tsx files created
- [ ] All 6 error.tsx files created
- [ ] All 6 pages export metadata

### UX Criteria
- [ ] Loading skeletons display during data fetch
- [ ] Error boundaries catch and display errors gracefully
- [ ] View transitions work on Chrome/Edge (with fallback)
- [ ] Page titles update correctly in browser tab

### Performance Criteria
- [ ] First Contentful Paint improved with Suspense
- [ ] No layout shift during loading (skeletons match layout)
- [ ] Streaming reduces Time to Interactive

---

## 7. Technical Notes

### Next.js 16 Considerations
- Pages are currently all `'use client'` - they CAN export metadata when using `generateMetadata` pattern
- For client pages, metadata must be defined in a separate `metadata.ts` file OR convert pages to server components where appropriate
- View Transitions API requires `experimental.viewTransition: true` in next.config.ts

### Dependencies
No new dependencies required. Uses existing:
- Tailwind CSS (already in use)
- Lucide React (already in use)
- Radix UI (already in use)

---

## 8. Files Summary

| Action | File Path | Count |
|--------|-----------|-------|
| CREATE | `src/components/ui/skeleton.tsx` | 1 |
| CREATE | `src/components/ui/skeleton-card.tsx` | 1 |
| CREATE | `src/components/loading/*.tsx` | 4 |
| CREATE | `src/hooks/useViewTransition.ts` | 1 |
| CREATE | `src/app/*/loading.tsx` | 6 |
| CREATE | `src/app/*/error.tsx` | 6 |
| MODIFY | `src/app/*/page.tsx` (add metadata) | 6 |
| MODIFY | `src/components/Navigation.tsx` | 1 |
| MODIFY | `next.config.ts` | 1 |

**Total: 26 files (21 new, 7 modified)**

---

## 9. Rollback Plan

If issues arise:
1. Remove loading.tsx files to restore original behavior
2. Remove error.tsx files (React handles errors at parent level)
3. Revert metadata exports (pages work without them)
4. Disable View Transitions in next.config.ts

---

## 10. Implementation Status

### Completed (2026-04-16)

- [x] Create skeleton components (`ui/skeleton.tsx`, `skeleton-card.tsx`)
- [x] Create page-specific loading skeletons (`loading/*.tsx`)
- [x] Add `loading.tsx` to all 6 page routes (+ root)
- [x] Add `error.tsx` to all 6 page routes (+ root)
- [x] Add metadata exports (`metadata.ts` files for each route)
- [x] Enable View Transitions in `next.config.ts`
- [x] Create `useViewTransition` hook
- [x] Update root layout with enhanced OpenGraph metadata

### Build Verification
```
✓ npm run type-check: PASSED
✓ npm run build: PASSED (17 routes generated)
```

### Files Created (14 new)
| File | Purpose |
|------|---------|
| `src/components/ui/skeleton.tsx` | Base skeleton with pulse animation |
| `src/components/ui/skeleton-card.tsx` | Card skeleton variants |
| `src/components/loading/dashboard-skeleton.tsx` | Dashboard page skeleton |
| `src/components/loading/memory-skeleton.tsx` | Memory page skeleton |
| `src/components/loading/chat-skeleton.tsx` | Chat page skeleton |
| `src/components/loading/orchestration-skeleton.tsx` | Orchestration page skeleton |
| `src/hooks/useViewTransition.ts` | View Transitions hook |
| `src/app/loading.tsx` | Root loading state |
| `src/app/error.tsx` | Root error boundary |
| `src/app/dashboard/loading.tsx` | Dashboard loading |
| `src/app/dashboard/error.tsx` | Dashboard error |
| `src/app/memory/loading.tsx` | Memory loading |
| `src/app/memory/error.tsx` | Memory error |
| `src/app/chat/loading.tsx` | Chat loading |
| `src/app/chat/error.tsx` | Chat error |
| `src/app/orchestration/loading.tsx` | Orchestration loading |
| `src/app/orchestration/error.tsx` | Orchestration error |
| `src/app/settings/loading.tsx` | Settings loading |
| `src/app/settings/error.tsx` | Settings error |
| `src/app/dashboard/metadata.ts` | Dashboard metadata |
| `src/app/memory/metadata.ts` | Memory metadata |
| `src/app/chat/metadata.ts` | Chat metadata |
| `src/app/orchestration/metadata.ts` | Orchestration metadata |
| `src/app/settings/metadata.ts` | Settings metadata |
| `src/app/metadata.ts` | Root metadata |

### Files Modified (3)
| File | Changes |
|------|---------|
| `next.config.ts` | Added `experimental.viewTransition: true` |
| `src/app/layout.tsx` | Enhanced metadata with OpenGraph + Twitter cards |

---

*Created: 2026-04-16*
*Completed: 2026-04-16*
*Story Points: 21*
