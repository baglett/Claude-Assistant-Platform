"use client";

/**
 * ChatLayout component that combines the session sidebar with the chat container.
 *
 * Provides a ChatGPT-style layout with sidebar for session history on desktop
 * and a collapsible sidebar on mobile.
 */

import { useState, useCallback } from "react";

import { SessionSidebar } from "./SessionSidebar";
import { ChatContainer } from "./ChatContainer";

/**
 * Props for the ChatLayout component.
 */
interface ChatLayoutProps {
  /** Whether to show the sidebar by default on mobile */
  defaultSidebarOpen?: boolean;
}

/**
 * Main chat layout with session sidebar.
 *
 * Features:
 * - Desktop: Always visible sidebar on the left
 * - Mobile: Collapsible sidebar with toggle button
 * - Responsive flex layout
 *
 * @example
 * <ChatLayout />
 */
export function ChatLayout({
  defaultSidebarOpen = false,
}: ChatLayoutProps): JSX.Element {
  // Mobile sidebar state
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(defaultSidebarOpen);

  /**
   * Toggle the mobile sidebar visibility.
   */
  const handleToggleSidebar = useCallback(() => {
    setIsMobileSidebarOpen((prev) => !prev);
  }, []);

  /**
   * Close the mobile sidebar.
   */
  const handleCloseSidebar = useCallback(() => {
    setIsMobileSidebarOpen(false);
  }, []);

  return (
    <div className="flex h-full">
      {/* Desktop sidebar - always visible on lg screens */}
      <div className="hidden lg:block">
        <SessionSidebar />
      </div>

      {/* Mobile sidebar overlay */}
      {isMobileSidebarOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/50 z-40 lg:hidden"
            onClick={handleCloseSidebar}
          />
          {/* Sidebar */}
          <div className="fixed inset-y-0 left-0 z-50 lg:hidden">
            <SessionSidebar onClose={handleCloseSidebar} />
          </div>
        </>
      )}

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        <ChatContainer onToggleSidebar={handleToggleSidebar} />
      </div>
    </div>
  );
}
