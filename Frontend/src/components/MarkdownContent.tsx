"use client";

/**
 * MarkdownContent component for rendering markdown with syntax highlighting.
 *
 * Renders markdown content with support for:
 * - GitHub Flavored Markdown (tables, task lists, strikethrough)
 * - Syntax highlighting for code blocks
 * - Proper styling for all markdown elements
 */

import dynamic from "next/dynamic";
import { useCallback, useState, Suspense } from "react";

/**
 * Props for the MarkdownContent component.
 */
interface MarkdownContentProps {
  /** The markdown content to render */
  content: string;
  /** Additional CSS classes to apply */
  className?: string;
}

/**
 * Dynamically import ReactMarkdown to handle ESM compatibility.
 */
const ReactMarkdown = dynamic(
  () => import("react-markdown").then((mod) => mod.default),
  { ssr: false }
);

/**
 * Copy button component for code blocks.
 */
function CopyButton({ text }: { text: string }): JSX.Element {
  const [copied, setCopied] = useState(false);

  /**
   * Handle copy to clipboard.
   */
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  }, [text]);

  return (
    <button
      onClick={handleCopy}
      className="btn btn-ghost btn-xs opacity-70 hover:opacity-100"
      title={copied ? "Copied!" : "Copy code"}
      aria-label={copied ? "Copied!" : "Copy code"}
    >
      {copied ? (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="w-4 h-4 text-success"
        >
          <path
            fillRule="evenodd"
            d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
            clipRule="evenodd"
          />
        </svg>
      ) : (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="w-4 h-4"
        >
          <path d="M7 3.5A1.5 1.5 0 018.5 2h3.879a1.5 1.5 0 011.06.44l3.122 3.12A1.5 1.5 0 0117 6.622V12.5a1.5 1.5 0 01-1.5 1.5h-1v-3.379a3 3 0 00-.879-2.121L10.5 5.379A3 3 0 008.379 4.5H7v-1z" />
          <path d="M4.5 6A1.5 1.5 0 003 7.5v9A1.5 1.5 0 004.5 18h7a1.5 1.5 0 001.5-1.5v-5.879a1.5 1.5 0 00-.44-1.06L9.44 6.439A1.5 1.5 0 008.378 6H4.5z" />
        </svg>
      )}
    </button>
  );
}

/**
 * Loading placeholder for markdown content.
 */
function MarkdownLoading(): JSX.Element {
  return (
    <div className="animate-pulse">
      <div className="h-4 bg-base-300 rounded w-3/4 mb-2" />
      <div className="h-4 bg-base-300 rounded w-1/2" />
    </div>
  );
}

/**
 * Component props type for markdown elements.
 *
 * These props are passed by ReactMarkdown to custom component renderers.
 */
interface MarkdownComponentProps {
  /** CSS class name (e.g., "language-typescript" for code blocks) */
  className?: string;
  /** Child elements to render */
  children?: React.ReactNode;
  /** Link href for anchor elements */
  href?: string;
}

/**
 * Custom components for ReactMarkdown rendering.
 *
 * Provides styled renderers for code blocks, links, headings, lists,
 * blockquotes, tables, and other markdown elements.
 */
const markdownComponents: Record<string, React.ComponentType<MarkdownComponentProps>> = {
  // Custom code block rendering with copy button
  code: ({ className, children, ...props }: MarkdownComponentProps) => {
    const match = /language-(\w+)/.exec(className || "");
    const language = match ? match[1] : "";
    const codeString = String(children).replace(/\n$/, "");
    const isInline = !className;

    // Inline code
    if (isInline) {
      return (
        <code
          className="bg-base-300 px-1.5 py-0.5 rounded text-sm font-mono"
          {...props}
        >
          {children}
        </code>
      );
    }

    // Code block
    return (
      <div className="relative group my-3">
        <div className="flex items-center justify-between bg-base-300 px-3 py-1.5 rounded-t-lg border-b border-base-content/10">
          <span className="text-xs text-base-content/60 font-mono">
            {language || "plaintext"}
          </span>
          <CopyButton text={codeString} />
        </div>
        <pre className="bg-base-300 p-4 rounded-b-lg overflow-x-auto text-sm !mt-0">
          <code className={className} {...props}>
            {children}
          </code>
        </pre>
      </div>
    );
  },
  // Links open in new tab
  a: ({ href, children }: MarkdownComponentProps) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="link link-primary"
    >
      {children}
    </a>
  ),
  // Styled headings
  h1: ({ children }: MarkdownComponentProps) => (
    <h1 className="text-2xl font-bold mt-4 mb-2">{children}</h1>
  ),
  h2: ({ children }: MarkdownComponentProps) => (
    <h2 className="text-xl font-bold mt-3 mb-2">{children}</h2>
  ),
  h3: ({ children }: MarkdownComponentProps) => (
    <h3 className="text-lg font-semibold mt-2 mb-1">{children}</h3>
  ),
  // Lists
  ul: ({ children }: MarkdownComponentProps) => (
    <ul className="list-disc list-inside my-2 space-y-1">{children}</ul>
  ),
  ol: ({ children }: MarkdownComponentProps) => (
    <ol className="list-decimal list-inside my-2 space-y-1">{children}</ol>
  ),
  // Blockquotes
  blockquote: ({ children }: MarkdownComponentProps) => (
    <blockquote className="border-l-4 border-primary pl-4 my-2 italic text-base-content/80">
      {children}
    </blockquote>
  ),
  // Tables
  table: ({ children }: MarkdownComponentProps) => (
    <div className="overflow-x-auto my-3">
      <table className="table table-sm">{children}</table>
    </div>
  ),
  th: ({ children }: MarkdownComponentProps) => (
    <th className="bg-base-200 font-semibold">{children}</th>
  ),
  // Paragraphs
  p: ({ children }: MarkdownComponentProps) => <p className="my-2">{children}</p>,
  // Horizontal rule
  hr: () => <hr className="my-4 border-base-300" />,
  // Strong/bold
  strong: ({ children }: MarkdownComponentProps) => (
    <strong className="font-semibold">{children}</strong>
  ),
};

/**
 * Renders markdown content with syntax highlighting and GFM support.
 *
 * @example
 * <MarkdownContent content="# Hello\n\nThis is **bold** text." />
 */
export function MarkdownContent({
  content,
  className = "",
}: MarkdownContentProps): JSX.Element {
  return (
    <div className={`markdown-content ${className}`}>
      <Suspense fallback={<MarkdownLoading />}>
        <ReactMarkdown components={markdownComponents}>
          {content}
        </ReactMarkdown>
      </Suspense>
    </div>
  );
}
