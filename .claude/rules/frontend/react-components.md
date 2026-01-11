---
paths:
  - "Frontend/src/components/**/*.tsx"
---

# React Component Patterns

## Component Structure

```tsx
"use client"; // Only if needed

import { useState, useCallback } from "react";
import { useChatStore } from "@/stores/chatStore";
import type { Message } from "@/types/chat";

/**
 * Props for the ChatMessage component.
 */
interface ChatMessageProps {
  /** The message to display */
  message: Message;
  /** Whether this is the last message in the list */
  isLast?: boolean;
  /** Callback when user clicks retry */
  onRetry?: (messageId: string) => void;
}

/**
 * Displays a single chat message with sender info and content.
 *
 * @example
 * <ChatMessage message={msg} isLast={idx === messages.length - 1} />
 */
export function ChatMessage({
  message,
  isLast = false,
  onRetry,
}: ChatMessageProps): JSX.Element {
  const isUser = message.role === "user";

  return (
    <div className={`chat ${isUser ? "chat-end" : "chat-start"}`}>
      <div className="chat-bubble">
        {message.content}
      </div>
    </div>
  );
}
```

## Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Component files | PascalCase | `ChatMessage.tsx` |
| Component functions | PascalCase | `function ChatMessage()` |
| Props interfaces | `ComponentNameProps` | `ChatMessageProps` |
| Event handlers | `onEventName` | `onSubmit`, `onClick` |
| Handler functions | `handleEventName` | `handleSubmit` |

## Props Typing

Always use explicit interfaces for props:

```tsx
// Good: Explicit interface with documentation
interface ButtonProps {
  /** Button text content */
  children: React.ReactNode;
  /** Visual style variant */
  variant?: "primary" | "secondary" | "ghost";
  /** Button size */
  size?: "sm" | "md" | "lg";
  /** Disabled state */
  disabled?: boolean;
  /** Click handler */
  onClick?: () => void;
}

// Bad: Inline types
function Button(props: { children: React.ReactNode; onClick?: () => void }) {}
```

## Event Handlers

Use `useCallback` for handlers passed to children:

```tsx
function ChatInput({ onSend }: ChatInputProps): JSX.Element {
  const [value, setValue] = useState("");

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (value.trim()) {
        onSend(value);
        setValue("");
      }
    },
    [value, onSend]
  );

  return (
    <form onSubmit={handleSubmit}>
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Type a message..."
      />
      <button type="submit">Send</button>
    </form>
  );
}
```

## State Management with Zustand

Access store state with selectors:

```tsx
import { useChatStore } from "@/stores/chatStore";

function MessageList(): JSX.Element {
  // Select only what you need
  const messages = useChatStore((state) => state.messages);
  const isLoading = useChatStore((state) => state.isLoading);

  // Or combine with shallow compare for objects
  const { messages, isLoading } = useChatStore(
    (state) => ({ messages: state.messages, isLoading: state.isLoading }),
    shallow
  );

  return (
    <div>
      {messages.map((msg) => (
        <ChatMessage key={msg.id} message={msg} />
      ))}
      {isLoading && <LoadingIndicator />}
    </div>
  );
}
```

## DaisyUI Component Usage

Use DaisyUI classes for consistent styling:

```tsx
// Buttons
<button className="btn btn-primary">Primary</button>
<button className="btn btn-secondary btn-sm">Small Secondary</button>
<button className="btn btn-ghost">Ghost</button>

// Cards
<div className="card bg-base-100 shadow-xl">
  <div className="card-body">
    <h2 className="card-title">Card Title</h2>
    <p>Card content here</p>
    <div className="card-actions justify-end">
      <button className="btn btn-primary">Action</button>
    </div>
  </div>
</div>

// Inputs
<input type="text" className="input input-bordered w-full" />
<textarea className="textarea textarea-bordered" />

// Loading
<span className="loading loading-spinner loading-md" />
```

## Component Organization

Export components from index file:

```tsx
// components/index.ts
export { ChatContainer } from "./ChatContainer";
export { ChatInput } from "./ChatInput";
export { ChatMessage } from "./ChatMessage";

// Usage in pages
import { ChatContainer, ChatInput } from "@/components";
```

## Key Rules

1. **One component per file** - Named after the component
2. **Props interface required** - With JSDoc documentation
3. **"use client" only when needed** - Check if hooks are used
4. **Zustand selectors** - Don't subscribe to entire store
5. **DaisyUI classes** - For consistent UI patterns
