/**
 * Centralized component exports for the Claude Assistant Platform.
 *
 * This index file provides a single import point for all components,
 * enabling cleaner imports throughout the application.
 *
 * @example
 * // Instead of multiple imports:
 * import { ChatContainer } from "@/components/ChatContainer";
 * import { ChatInput } from "@/components/ChatInput";
 *
 * // Use a single import:
 * import { ChatContainer, ChatInput } from "@/components";
 */

// Chat components
export { ChatContainer } from "./ChatContainer";
export { ChatMessage } from "./ChatMessage";
export { ChatInput } from "./ChatInput";
export { ChatLayout } from "./ChatLayout";
export { MarkdownContent } from "./MarkdownContent";

// Session components
export { SessionItem } from "./SessionItem";
export { SessionSidebar } from "./SessionSidebar";

// Todo components
export { TodoItem } from "./TodoItem";
export { TodoList } from "./TodoList";
export { TodoForm } from "./TodoForm";
export { TodoFilters } from "./TodoFilters";
export { TodoStats } from "./TodoStats";

// Shared/utility components
export { ConfirmModal } from "./ConfirmModal";
