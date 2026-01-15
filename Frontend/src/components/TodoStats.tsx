"use client";

/**
 * TodoStats component for displaying todo statistics.
 *
 * Shows counts by status in a compact card grid format.
 */

import { useTodoStore } from "@/stores/todoStore";

/**
 * Single stat card component.
 */
interface StatCardProps {
  /** Stat label */
  label: string;
  /** Stat value */
  value: number;
  /** Optional color class */
  colorClass?: string;
}

/**
 * Individual stat display card.
 */
function StatCard({
  label,
  value,
  colorClass = "text-base-content",
}: StatCardProps): JSX.Element {
  return (
    <div className="stat p-3">
      <div className="stat-title text-xs">{label}</div>
      <div className={`stat-value text-2xl ${colorClass}`}>{value}</div>
    </div>
  );
}

/**
 * TodoStats component displaying aggregated todo counts.
 *
 * @example
 * <TodoStats />
 */
export function TodoStats(): JSX.Element {
  const stats = useTodoStore((state) => state.stats);
  const isLoading = useTodoStore((state) => state.isLoading);

  if (isLoading && !stats) {
    return (
      <div className="stats shadow bg-base-100 w-full">
        <div className="stat animate-pulse">
          <div className="h-4 bg-base-300 rounded w-16 mb-2" />
          <div className="h-8 bg-base-300 rounded w-12" />
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="stats shadow bg-base-100 w-full opacity-50">
        <StatCard label="Total" value={0} />
      </div>
    );
  }

  return (
    <div className="stats shadow bg-base-100 w-full stats-horizontal overflow-x-auto">
      <StatCard label="Total" value={stats.total} colorClass="text-primary" />
      <StatCard
        label="Pending"
        value={stats.pending}
        colorClass="text-warning"
      />
      <StatCard
        label="In Progress"
        value={stats.in_progress}
        colorClass="text-info"
      />
      <StatCard
        label="Completed"
        value={stats.completed}
        colorClass="text-success"
      />
      <StatCard label="Failed" value={stats.failed} colorClass="text-error" />
    </div>
  );
}
