---
paths:
  - "Frontend/**/*.tsx"
  - "Frontend/**/*.css"
---

# UI/UX Design Guidelines

This document defines the visual design standards and user experience patterns for the Claude Assistant Platform frontend. Following these guidelines ensures consistency, accessibility, and professional quality.

## Design System Overview

Our design system is built on:
- **DaisyUI** - Component library with semantic theming
- **Tailwind CSS** - Utility-first styling
- **8pt Grid System** - Consistent spacing
- **WCAG 2.1 AA** - Accessibility compliance

---

## Color System

### Semantic Color Usage

Use DaisyUI's semantic color names. Never use raw Tailwind colors (like `blue-500`) directly.

| Color | Usage | Examples |
|-------|-------|----------|
| `primary` | Main actions, active states, key UI elements | Primary buttons, active nav items, links |
| `secondary` | Secondary actions, supporting elements | Secondary buttons, tags, less prominent CTAs |
| `accent` | Highlights, special emphasis | Badges, notifications, highlights |
| `neutral` | Backgrounds, borders, text | Cards, dividers, subtle backgrounds |
| `base-100/200/300` | Background layers | Page bg, card bg, raised surfaces |
| `base-content` | Primary text | Body text, headings |

### State Colors

| Color | Usage | When to Use |
|-------|-------|-------------|
| `success` | Positive outcomes | Task completed, form valid, operation successful |
| `warning` | Caution states | Destructive action pending, approaching limits |
| `error` | Errors & failures | Validation errors, API failures, blocked actions |
| `info` | Informational | Tips, help text, neutral notifications |

### Color Rules

```tsx
// GOOD: Semantic colors
<button className="btn btn-primary">Save</button>
<div className="alert alert-error">Error message</div>
<span className="text-base-content/60">Muted text</span>

// BAD: Raw colors
<button className="bg-blue-500">Save</button>
<div className="bg-red-100 text-red-800">Error</div>
```

### Contrast Requirements

- **Normal text**: Minimum 4.5:1 contrast ratio
- **Large text** (19px+ bold, 24px+ normal): Minimum 3:1 contrast ratio
- **UI components**: Minimum 3:1 against adjacent colors
- Use DaisyUI's `*-content` colors which auto-contrast (e.g., `primary-content` on `primary`)

---

## Typography

### Font Scale (Based on 1.25 ratio)

| Class | Size | Usage |
|-------|------|-------|
| `text-xs` | 12px | Captions, timestamps, helper text |
| `text-sm` | 14px | Secondary text, labels, metadata |
| `text-base` | 16px | Body text (minimum for readability) |
| `text-lg` | 18px | Emphasized body, lead text |
| `text-xl` | 20px | H4, section titles |
| `text-2xl` | 24px | H3, card titles |
| `text-3xl` | 30px | H2, page section headers |
| `text-4xl` | 36px | H1, page titles |

### Typography Rules

1. **Minimum body text**: 16px (`text-base`) - Never smaller for main content
2. **Line height**: 1.5 minimum for body text (`leading-relaxed`)
3. **Max line width**: 65-75 characters for readability (`max-w-prose`)
4. **Heading hierarchy**: One H1 per page, sequential heading levels

```tsx
// GOOD: Proper hierarchy
<h1 className="text-2xl font-bold">Page Title</h1>
<p className="text-base leading-relaxed max-w-prose">Body content...</p>
<span className="text-sm text-base-content/60">Timestamp</span>

// BAD: Skipping hierarchy, tiny text
<h1 className="text-lg">Title</h1>  // Too small for h1
<p className="text-xs">Important content</p>  // Too small to read
```

### Font Weights

| Weight | Class | Usage |
|--------|-------|-------|
| 400 | `font-normal` | Body text |
| 500 | `font-medium` | Labels, buttons, emphasized text |
| 600 | `font-semibold` | Subheadings, card titles |
| 700 | `font-bold` | Page titles, important headings |

---

## Spacing System (8pt Grid)

All spacing values should be multiples of 8px (or 4px for tight spaces).

### Spacing Scale

| Tailwind | Pixels | Usage |
|----------|--------|-------|
| `1` | 4px | Icon gaps, tight inline spacing |
| `2` | 8px | Tight component padding, small gaps |
| `3` | 12px | Form field padding, button padding |
| `4` | 16px | Standard component padding, card padding |
| `6` | 24px | Section spacing, larger gaps |
| `8` | 32px | Major section breaks |
| `12` | 48px | Page section margins |
| `16` | 64px | Large decorative spacing |

### Spacing Rules

1. **Internal ≤ External**: Padding inside elements should be ≤ margin around them
2. **Consistent gaps**: Use `gap-*` instead of individual margins in flex/grid
3. **Breathing room**: Important elements need whitespace to stand out

```tsx
// GOOD: 8pt grid, internal ≤ external
<div className="p-4">  {/* 16px internal padding */}
  <div className="space-y-3">  {/* 12px between children */}
    <button className="px-4 py-2">Button</button>  {/* 16px × 8px */}
  </div>
</div>
<div className="mt-6">  {/* 24px external margin - larger than internal */}

// BAD: Arbitrary spacing
<div className="p-[13px] mt-[7px]">  {/* Not on grid */}
```

### Component Spacing Standards

| Component | Padding | Gap Between |
|-----------|---------|-------------|
| Buttons | `px-4 py-2` (16×8) | `gap-2` (8px) |
| Cards | `p-4` or `p-6` (16 or 24) | `gap-4` (16px) |
| Form fields | `px-3 py-2` (12×8) | `gap-3` (12px) |
| List items | `py-3` (12px vertical) | dividers or `gap-2` |
| Sections | `py-8` or `py-12` | `gap-8` (32px) |

---

## Component Patterns

### Button Hierarchy

Use button variants consistently to indicate importance:

| Variant | Usage | Example |
|---------|-------|---------|
| `btn-primary` | Primary action (1 per section max) | Save, Submit, Send |
| `btn-secondary` | Secondary action | Cancel, Back, View Details |
| `btn-ghost` | Tertiary action, navigation | Close, Menu items |
| `btn-outline` | Alternative secondary | Filter, Toggle |
| `btn-error` | Destructive actions | Delete, Remove |

```tsx
// GOOD: Clear hierarchy
<div className="flex gap-2 justify-end">
  <button className="btn btn-ghost">Cancel</button>
  <button className="btn btn-primary">Save Changes</button>
</div>

// BAD: Multiple primaries, no hierarchy
<div className="flex gap-2">
  <button className="btn btn-primary">Cancel</button>
  <button className="btn btn-primary">Save</button>
  <button className="btn btn-primary">Delete</button>
</div>
```

### Button Sizes

| Size | Class | Touch Target | Usage |
|------|-------|--------------|-------|
| Small | `btn-sm` | 32px | Inline actions, dense UIs |
| Default | `btn` | 40px | Standard buttons |
| Large | `btn-lg` | 48px+ | Primary CTAs, mobile |

**Minimum touch target**: 44×44px for mobile (use `btn` or larger)

### Form Fields

```tsx
// Standard form field pattern
<div className="form-control">
  <label className="label">
    <span className="label-text">Email Address</span>
  </label>
  <input
    type="email"
    className="input input-bordered w-full"
    placeholder="you@example.com"
  />
  <label className="label">
    <span className="label-text-alt text-error">Error message here</span>
  </label>
</div>
```

### Cards

```tsx
// Standard card pattern
<div className="card bg-base-100 shadow-sm">
  <div className="card-body">
    <h3 className="card-title text-lg">Card Title</h3>
    <p className="text-base-content/70">Card description text.</p>
    <div className="card-actions justify-end mt-4">
      <button className="btn btn-ghost btn-sm">Cancel</button>
      <button className="btn btn-primary btn-sm">Action</button>
    </div>
  </div>
</div>
```

---

## State Patterns

### Empty States

Empty states should never leave users confused. Include:
1. **Visual indicator** - Icon or illustration
2. **Headline** - What's empty ("No conversations yet")
3. **Explanation** - Why it's empty or what to do
4. **CTA** - Action to resolve the empty state

```tsx
// GOOD: Complete empty state
<div className="flex flex-col items-center justify-center p-8 text-center">
  <div className="w-16 h-16 rounded-full bg-base-200 flex items-center justify-center mb-4">
    <ChatIcon className="w-8 h-8 text-base-content/40" />
  </div>
  <h3 className="text-lg font-semibold mb-2">No conversations yet</h3>
  <p className="text-base-content/60 mb-4">Start a new chat to begin</p>
  <button className="btn btn-primary">New Chat</button>
</div>

// BAD: Just text
<p>No items</p>
```

### Loading States

- Use skeleton loaders for content areas (maintains layout)
- Use spinners for actions (buttons, small areas)
- Never block the entire screen unless necessary

```tsx
// Skeleton loader for list
<div className="animate-pulse space-y-3">
  {[1, 2, 3].map((i) => (
    <div key={i} className="flex gap-3">
      <div className="w-10 h-10 rounded-full bg-base-300" />
      <div className="flex-1 space-y-2">
        <div className="h-4 bg-base-300 rounded w-3/4" />
        <div className="h-3 bg-base-300 rounded w-1/2" />
      </div>
    </div>
  ))}
</div>

// Button loading
<button className="btn btn-primary" disabled>
  <span className="loading loading-spinner loading-sm" />
  Saving...
</button>
```

### Error States

Errors must explain:
1. **What went wrong** - Clear, non-technical language
2. **Why** (if helpful) - Brief context
3. **How to fix** - Actionable next step

```tsx
// GOOD: Actionable error
<div className="alert alert-error">
  <ErrorIcon className="w-5 h-5" />
  <div>
    <h4 className="font-semibold">Failed to send message</h4>
    <p className="text-sm">Check your connection and try again.</p>
  </div>
  <button className="btn btn-sm btn-ghost">Retry</button>
</div>

// BAD: Vague error
<div className="alert alert-error">Error occurred</div>
```

### Success States

Confirm successful actions briefly, then get out of the way:

```tsx
// Toast notification (auto-dismiss)
<div className="toast toast-end">
  <div className="alert alert-success">
    <span>Message sent successfully</span>
  </div>
</div>
```

---

## Accessibility (WCAG 2.1 AA)

### Keyboard Navigation

- All interactive elements must be keyboard accessible
- Visible focus indicators on all focusable elements
- Logical tab order (follows visual layout)
- No keyboard traps

```tsx
// GOOD: Focusable, visible focus
<button className="btn focus:ring-2 focus:ring-primary focus:ring-offset-2">
  Action
</button>

// For custom interactive elements
<div
  role="button"
  tabIndex={0}
  onKeyDown={(e) => e.key === 'Enter' && handleClick()}
  onClick={handleClick}
>
  Custom clickable
</div>
```

### Screen Readers

- Use semantic HTML (`<button>`, `<nav>`, `<main>`, `<article>`)
- Add `aria-label` for icon-only buttons
- Use `aria-live` for dynamic content updates
- Hide decorative elements with `aria-hidden="true"`

```tsx
// Icon-only button
<button className="btn btn-ghost btn-sm" aria-label="Delete conversation">
  <TrashIcon className="w-4 h-4" />
</button>

// Live region for updates
<div aria-live="polite" className="sr-only">
  {statusMessage}
</div>
```

### Focus Management

- Move focus to new content (modals, drawers)
- Return focus after modal closes
- Skip links for main content

```tsx
// Skip link (first focusable element)
<a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:p-4 focus:bg-primary focus:text-primary-content">
  Skip to main content
</a>
```

### Color & Contrast

- Never convey information by color alone
- Use icons, patterns, or text in addition to color
- Test with color blindness simulators

```tsx
// GOOD: Color + icon
<span className="text-error flex items-center gap-1">
  <ErrorIcon className="w-4 h-4" />
  Required field
</span>

// BAD: Color only
<span className="text-error">*</span>
```

---

## Responsive Design

### Breakpoints (Tailwind defaults)

| Breakpoint | Width | Target |
|------------|-------|--------|
| Default | 0px+ | Mobile first |
| `sm` | 640px+ | Large phones |
| `md` | 768px+ | Tablets |
| `lg` | 1024px+ | Laptops/Desktops |
| `xl` | 1280px+ | Large screens |

### Mobile-First Rules

1. Design for mobile first, enhance for larger screens
2. Touch targets: minimum 44×44px
3. Thumb-friendly: important actions in easy reach zones
4. Collapsible navigation on mobile

```tsx
// Mobile-first responsive pattern
<div className="
  p-4              // Base: mobile
  md:p-6           // Tablet+: more padding
  lg:p-8           // Desktop+: even more
">
  <div className="
    flex flex-col    // Mobile: stack
    lg:flex-row      // Desktop: side by side
    gap-4
  ">
```

---

## Animation & Motion

### Principles

1. **Purposeful**: Animation should provide feedback or guide attention
2. **Fast**: 150-300ms for most transitions
3. **Subtle**: Don't distract from content
4. **Respect preferences**: Honor `prefers-reduced-motion`

### Timing

| Duration | Usage |
|----------|-------|
| 150ms | Micro-interactions (hover, focus) |
| 200ms | Standard transitions (fade, slide) |
| 300ms | Complex animations (modals, drawers) |

```tsx
// Respect reduced motion
<div className="
  transition-opacity duration-200
  motion-reduce:transition-none
">

// Standard hover transition
<button className="
  btn
  transition-colors duration-150
  hover:bg-primary-focus
">
```

---

## Iconography

### Standards

- **Library**: Use Heroicons (included via copy-paste SVGs)
- **Size**: Match to text or use standard sizes (16, 20, 24px)
- **Style**: Use `solid` for filled, `outline` for line icons
- **Consistency**: Don't mix icon libraries

### Sizing

| Size | Class | Usage |
|------|-------|-------|
| 16px | `w-4 h-4` | Inline with small text |
| 20px | `w-5 h-5` | Inline with body text, buttons |
| 24px | `w-6 h-6` | Standalone, navigation |
| 32px+ | `w-8 h-8` | Empty states, features |

```tsx
// Icon in button
<button className="btn btn-primary gap-2">
  <PlusIcon className="w-5 h-5" />
  New Chat
</button>

// Icon button (needs aria-label)
<button className="btn btn-ghost btn-sm" aria-label="Settings">
  <CogIcon className="w-5 h-5" />
</button>
```

---

## Copy & Content Guidelines

### Tone

- **Clear**: Plain language, no jargon
- **Concise**: Say more with less
- **Helpful**: Guide users to success
- **Friendly**: Warm but professional

### Button Labels

| Do | Don't |
|----|-------|
| Save | Submit |
| Send Message | OK |
| Delete Conversation | Yes |
| Cancel | No |
| Try Again | Retry |

### Error Messages

| Do | Don't |
|----|-------|
| "Couldn't send message. Check your connection." | "Error 500" |
| "Enter a valid email address" | "Invalid input" |
| "Session expired. Please sign in again." | "Unauthorized" |

### Empty States

| Context | Headline | Description |
|---------|----------|-------------|
| No conversations | "No conversations yet" | "Start a new chat to begin" |
| No search results | "No results found" | "Try different keywords" |
| No todos | "All caught up!" | "Create a new task to get started" |

---

## Checklist

Before shipping any UI:

- [ ] Colors use semantic names (primary, error, etc.)
- [ ] Text is minimum 16px for body content
- [ ] Spacing follows 8pt grid
- [ ] One primary button per section
- [ ] Empty, loading, and error states designed
- [ ] Keyboard navigable
- [ ] Color contrast meets 4.5:1 minimum
- [ ] Touch targets are 44px+ on mobile
- [ ] Animations respect reduced-motion preference
- [ ] Icon buttons have aria-labels

---

## References

- [DaisyUI Themes](https://daisyui.com/docs/themes/)
- [DaisyUI Colors](https://daisyui.com/docs/colors/)
- [8pt Grid System](https://spec.fm/specifics/8-pt-grid)
- [WCAG 2.1 Guidelines](https://www.w3.org/TR/WCAG21/)
- [WebAIM Checklist](https://webaim.org/standards/wcag/checklist)
- [Nielsen Norman Group - Empty States](https://www.nngroup.com/articles/empty-state-interface-design/)
- [Material Design Spacing](https://m3.material.io/foundations/layout/understanding-layout)
