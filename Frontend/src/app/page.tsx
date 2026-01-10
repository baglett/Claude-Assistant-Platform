"use client";

/**
 * Main page component for the Claude Assistant Platform.
 *
 * Renders the chat interface as the primary application view.
 */

import { ChatContainer } from "@/components/ChatContainer";

/**
 * Home page component.
 *
 * Displays the full-screen chat interface for interacting with
 * the Claude orchestrator agent.
 */
export default function Home() {
  return (
    <main className="h-screen flex flex-col">
      <ChatContainer />
    </main>
  );
}
