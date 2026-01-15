/**
 * Global loading component for the application.
 *
 * Displayed automatically by Next.js during route transitions
 * and while page content is being loaded.
 */

/**
 * Full-page loading skeleton with centered spinner.
 *
 * This component is automatically rendered by Next.js App Router
 * when navigating between routes or during initial page load.
 */
export default function Loading(): JSX.Element {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-base-100">
      {/* Loading spinner */}
      <span className="loading loading-spinner loading-lg text-primary" />

      {/* Loading text */}
      <p className="mt-4 text-base-content/60 text-sm">Loading...</p>

      {/* Skeleton preview for chat layout */}
      <div className="mt-8 w-full max-w-4xl px-4">
        <div className="animate-pulse space-y-4">
          {/* Header skeleton */}
          <div className="h-12 bg-base-200 rounded-lg" />

          {/* Message skeletons */}
          <div className="space-y-3">
            <div className="flex gap-3">
              <div className="w-10 h-10 rounded-full bg-base-300" />
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-base-300 rounded w-3/4" />
                <div className="h-4 bg-base-300 rounded w-1/2" />
              </div>
            </div>
            <div className="flex gap-3 justify-end">
              <div className="flex-1 space-y-2 max-w-[60%]">
                <div className="h-4 bg-base-300 rounded w-full" />
                <div className="h-4 bg-base-300 rounded w-2/3 ml-auto" />
              </div>
              <div className="w-10 h-10 rounded-full bg-base-300" />
            </div>
            <div className="flex gap-3">
              <div className="w-10 h-10 rounded-full bg-base-300" />
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-base-300 rounded w-5/6" />
                <div className="h-4 bg-base-300 rounded w-1/3" />
              </div>
            </div>
          </div>

          {/* Input skeleton */}
          <div className="h-14 bg-base-200 rounded-lg mt-4" />
        </div>
      </div>
    </div>
  );
}
