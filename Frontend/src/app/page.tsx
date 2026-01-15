"use client";

/**
 * Main page component for the Claude Assistant Platform.
 *
 * Renders the chat interface with session sidebar as the primary application view.
 */

import { ChatLayout } from "@/components/ChatLayout";

/**
 * Home page component.
 *
 * Displays the full-screen chat interface with session history sidebar
 * for interacting with the Claude orchestrator agent.
 */
export default function Home() {
  return (
    <main className="h-screen">
      <ChatLayout />
    </main>
  );
}
