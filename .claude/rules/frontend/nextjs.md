---
paths:
  - "Frontend/**/*.ts"
  - "Frontend/**/*.tsx"
---

# Next.js Frontend Standards

## Tech Stack

- **Next.js** with App Router (not Pages Router)
- **TypeScript** for type safety
- **Tailwind CSS** for styling
- **DaisyUI** for component library
- **Zustand** for state management
- **React 18+**

## App Router Structure

```
Frontend/src/
├── app/
│   ├── layout.tsx      # Root layout (providers, global styles)
│   ├── page.tsx        # Home page
│   ├── loading.tsx     # Loading UI
│   ├── error.tsx       # Error boundary
│   └── [feature]/
│       ├── page.tsx    # Feature page
│       └── layout.tsx  # Feature layout
├── components/         # Reusable components
├── stores/            # Zustand stores
├── lib/               # Utilities, API clients
└── types/             # TypeScript types
```

## Server vs Client Components

- **Default to Server Components** - Better performance
- Use `"use client"` only when needed:
  - Using React hooks (useState, useEffect)
  - Event handlers (onClick, onChange)
  - Browser APIs (localStorage, window)
  - Third-party client libraries

```tsx
// Server Component (default) - no directive needed
async function TodoList() {
  const todos = await fetchTodos(); // Server-side fetch
  return <ul>{todos.map(t => <li key={t.id}>{t.title}</li>)}</ul>;
}

// Client Component - needs directive
"use client";

import { useState } from "react";

function TodoForm() {
  const [title, setTitle] = useState("");
  return <input value={title} onChange={e => setTitle(e.target.value)} />;
}
```

## Data Fetching

- Use `async` Server Components for data fetching
- Use React Query or SWR for client-side fetching
- Keep API calls in `lib/api/` directory

```tsx
// Server Component data fetching
async function Page() {
  const data = await fetch("http://backend:8000/api/todos", {
    next: { revalidate: 60 }, // ISR: revalidate every 60 seconds
  });
  return <TodoList todos={await data.json()} />;
}
```

## TypeScript Standards

- Strict mode enabled
- Explicit return types on functions
- Use `interface` for object shapes, `type` for unions/primitives
- No `any` - use `unknown` if type is truly unknown

```tsx
interface TodoProps {
  id: string;
  title: string;
  completed: boolean;
  onToggle: (id: string) => void;
}

function Todo({ id, title, completed, onToggle }: TodoProps): JSX.Element {
  return (
    <div onClick={() => onToggle(id)}>
      {completed ? "✓" : "○"} {title}
    </div>
  );
}
```

## Styling with Tailwind + DaisyUI

- Use Tailwind utility classes
- Use DaisyUI components for consistency
- Extract repeated patterns to components, not @apply

```tsx
// Use DaisyUI components
<button className="btn btn-primary">Submit</button>
<div className="card bg-base-100 shadow-xl">
  <div className="card-body">
    <h2 className="card-title">Title</h2>
  </div>
</div>

// Tailwind utilities for custom styling
<div className="flex items-center gap-4 p-4 rounded-lg bg-gray-100">
```

## API Communication

- Create typed API client in `lib/api/`
- Handle errors consistently
- Use environment variables for API URLs

```tsx
// lib/api/todos.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL;

export async function createTodo(data: TodoCreate): Promise<Todo> {
  const response = await fetch(`${API_URL}/api/todos`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to create todo: ${response.status}`);
  }

  return response.json();
}
```

## Key Rules

1. **App Router only** - No Pages Router patterns
2. **Server Components first** - Only use client when necessary
3. **TypeScript strict mode** - No `any` types
4. **DaisyUI for components** - Consistent UI library
5. **Zustand for state** - Simple, typed state management

## Anti-Patterns

- **DON'T** use Pages Router patterns (use App Router only)
- **DON'T** add `"use client"` without needing client-side features
- **DON'T** use `any` type (define proper TypeScript interfaces)
- **DON'T** hardcode API URLs (use environment variables)
- **DON'T** use inline styles (use Tailwind utility classes)
- **DON'T** create components without TypeScript interfaces for props
- **DON'T** use `@apply` excessively (extract to components instead)
- **DON'T** mix multiple state management solutions
