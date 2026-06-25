import type { ReactNode } from "react";

interface MyPageSectionProps {
  itemsCount: number;
  emptyMessage: string;
  children: ReactNode;
  pagination?: ReactNode;
}

export function MyPageSection({
  itemsCount,
  emptyMessage,
  children,
  pagination,
}: MyPageSectionProps) {
  if (itemsCount === 0) {
    return (
      <div className="space-y-4">
        <div className="ds-card-surface p-6 text-center text-muted-foreground">
          {emptyMessage}
        </div>
        {pagination}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="space-y-3">{children}</div>
      {pagination}
    </div>
  );
}
