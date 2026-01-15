/**
 * Chat state management using Zustand.
 *
 * Manages conversation state, message history, session management,
 * and API interactions for the chat interface.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

import {
  ConversationSummary,
  deleteConversation,
  getConversationHistory,
  getConversations,
} from "@/lib/api/chat";

/**
 * Represents a single chat message.
 */
export interface ChatMessage {
  /** Unique message identifier */
  id: string;
  /** Message sender role */
  role: "user" | "assistant";
  /** Message content text */
  content: string;
  /** Message creation timestamp */
  timestamp: Date;
  /** Whether the message is still being generated */
  isStreaming?: boolean;
}

/**
 * Chat store state interface.
 */
interface ChatState {
  /** Array of messages in the current conversation */
  messages: ChatMessage[];
  /** Current conversation ID */
  conversationId: string | null;
  /** Whether a message is currently being processed */
  isLoading: boolean;
  /** Current error message, if any */
  error: string | null;

  /** List of conversation sessions */
  sessions: ConversationSummary[];
  /** Whether sessions are being loaded */
  sessionsLoading: boolean;
  /** Total number of sessions */
  sessionsTotal: number;
  /** Whether more sessions are available */
  sessionsHasMore: boolean;

  /** Add a new message to the conversation */
  addMessage: (message: Omit<ChatMessage, "id" | "timestamp">) => void;
  /** Update an existing message by ID */
  updateMessage: (id: string, content: string) => void;
  /** Set the loading state */
  setLoading: (loading: boolean) => void;
  /** Set an error message */
  setError: (error: string | null) => void;
  /** Set the conversation ID */
  setConversationId: (id: string) => void;
  /** Clear all messages and start a new conversation */
  clearMessages: () => void;
  /** Send a message to the backend API */
  sendMessage: (content: string) => Promise<void>;

  /** Fetch the list of sessions */
  fetchSessions: (page?: number) => Promise<void>;
  /** Load a specific session's messages */
  loadSession: (sessionId: string) => Promise<void>;
  /** Delete a session */
  deleteSession: (sessionId: string) => Promise<boolean>;
  /** Start a new chat (clear current and reset) */
  startNewChat: () => void;
}

/**
 * Generate a unique message ID.
 */
const generateId = (): string => {
  return `msg_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
};

/**
 * API base URL from environment or default to localhost.
 */
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Zustand store for chat state management.
 *
 * Persists conversation history to localStorage for session continuity.
 */
export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      messages: [],
      conversationId: null,
      isLoading: false,
      error: null,
      sessions: [],
      sessionsLoading: false,
      sessionsTotal: 0,
      sessionsHasMore: false,

      addMessage: (message) => {
        const newMessage: ChatMessage = {
          ...message,
          id: generateId(),
          timestamp: new Date(),
        };
        set((state) => ({
          messages: [...state.messages, newMessage],
        }));
      },

      updateMessage: (id, content) => {
        set((state) => ({
          messages: state.messages.map((msg) =>
            msg.id === id ? { ...msg, content, isStreaming: false } : msg
          ),
        }));
      },

      setLoading: (loading) => set({ isLoading: loading }),

      setError: (error) => set({ error }),

      setConversationId: (id) => set({ conversationId: id }),

      clearMessages: () =>
        set({
          messages: [],
          conversationId: null,
          error: null,
        }),

      sendMessage: async (content: string) => {
        const { addMessage, setLoading, setError, setConversationId, conversationId, fetchSessions } = get();

        // Don't send empty messages
        if (!content.trim()) return;

        // Add user message to the conversation
        addMessage({ role: "user", content: content.trim() });

        // Set loading state
        setLoading(true);
        setError(null);

        // Add placeholder for assistant response
        const assistantMessageId = generateId();
        set((state) => ({
          messages: [
            ...state.messages,
            {
              id: assistantMessageId,
              role: "assistant" as const,
              content: "",
              timestamp: new Date(),
              isStreaming: true,
            },
          ],
        }));

        try {
          // Send request to backend
          const response = await fetch(`${API_URL}/api/chat`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              message: content.trim(),
              conversation_id: conversationId,
            }),
          });

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(
              errorData.detail || `Request failed with status ${response.status}`
            );
          }

          const data = await response.json();

          // Update conversation ID if we got one
          if (data.conversation_id) {
            setConversationId(data.conversation_id);
          }

          // Update assistant message with response
          set((state) => ({
            messages: state.messages.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: data.response, isStreaming: false }
                : msg
            ),
          }));

          // Refresh sessions list to include the new/updated conversation
          fetchSessions();
        } catch (error) {
          // Remove the streaming placeholder on error
          set((state) => ({
            messages: state.messages.filter((msg) => msg.id !== assistantMessageId),
          }));

          const errorMessage =
            error instanceof Error ? error.message : "An unexpected error occurred";
          setError(errorMessage);
          console.error("Chat error:", error);
        } finally {
          setLoading(false);
        }
      },

      fetchSessions: async (page = 1) => {
        set({ sessionsLoading: true });

        try {
          const response = await getConversations(page, 20);
          set({
            sessions: response.items,
            sessionsTotal: response.total,
            sessionsHasMore: response.has_next,
          });
        } catch (error) {
          console.error("Failed to fetch sessions:", error);
        } finally {
          set({ sessionsLoading: false });
        }
      },

      loadSession: async (sessionId: string) => {
        const { setLoading, setError, setConversationId, fetchSessions } = get();

        setLoading(true);
        setError(null);

        try {
          const history = await getConversationHistory(sessionId);

          // Convert API messages to ChatMessage format
          const messages: ChatMessage[] = history.messages.map((msg, index) => ({
            id: `loaded_${sessionId}_${index}`,
            role: msg.role,
            content: msg.content,
            timestamp: new Date(),
          }));

          set({
            messages,
            conversationId: sessionId,
          });

          // Refresh sessions to update the active state
          fetchSessions();
        } catch (error) {
          const errorMessage =
            error instanceof Error ? error.message : "Failed to load session";
          setError(errorMessage);
          console.error("Load session error:", error);
        } finally {
          setLoading(false);
        }
      },

      deleteSession: async (sessionId: string) => {
        const { conversationId, fetchSessions, startNewChat } = get();

        try {
          await deleteConversation(sessionId);

          // If we deleted the active session, start a new chat
          if (conversationId === sessionId) {
            startNewChat();
          }

          // Refresh the sessions list
          await fetchSessions();
          return true;
        } catch (error) {
          console.error("Delete session error:", error);
          return false;
        }
      },

      startNewChat: () => {
        set({
          messages: [],
          conversationId: null,
          error: null,
        });
      },
    }),
    {
      name: "claude-assistant-chat",
      partialize: (state) => ({
        messages: state.messages,
        conversationId: state.conversationId,
      }),
    }
  )
);
