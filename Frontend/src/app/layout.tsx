import type { Metadata } from "next";
import "./globals.css";

/**
 * Application metadata for SEO and browser display.
 */
export const metadata: Metadata = {
  title: "Claude Assistant Platform",
  description:
    "A self-hosted AI assistant platform powered by Claude for intelligent task management.",
  icons: {
    icon: "/favicon.ico",
  },
};

/**
 * Root layout component for the application.
 *
 * Provides the base HTML structure and theme configuration.
 *
 * @param children - Child components to render
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-theme="claude">
      <body className="min-h-screen bg-base-100 antialiased">{children}</body>
    </html>
  );
}
