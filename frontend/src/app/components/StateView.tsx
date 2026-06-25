import type { ReactNode } from 'react';
import { AlertTriangle, Inbox, Loader2 } from 'lucide-react';

interface BaseStateViewProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  actions?: ReactNode;
  className?: string;
}

function StateContainer({ title, description, icon, actions, className }: BaseStateViewProps) {
  return (
    <div className={`rounded-lg border border-border bg-white p-8 text-center ${className ?? ''}`.trim()}>
      <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
        {icon}
      </div>
      <p className="text-foreground font-medium mb-1">{title}</p>
      {description ? <p className="text-sm text-muted-foreground">{description}</p> : null}
      {actions ? <div className="mt-5 flex items-center justify-center gap-2">{actions}</div> : null}
    </div>
  );
}

interface EmptyStateProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  className?: string;
}

export function EmptyState({ title, description, actions, className }: EmptyStateProps) {
  return (
    <StateContainer
      title={title}
      description={description}
      icon={<Inbox className="h-5 w-5" />}
      actions={actions}
      className={className}
    />
  );
}

interface LoadingStateProps {
  title?: string;
  description?: string;
  className?: string;
}

export function LoadingState({
  title = '불러오는 중입니다',
  description,
  className,
}: LoadingStateProps) {
  return (
    <StateContainer
      title={title}
      description={description}
      icon={<Loader2 className="h-5 w-5 animate-spin" />}
      className={className}
    />
  );
}

interface ErrorStateProps {
  title?: string;
  description: string;
  actions?: ReactNode;
  className?: string;
}

export function ErrorState({
  title = '문제가 발생했습니다',
  description,
  actions,
  className,
}: ErrorStateProps) {
  return (
    <StateContainer
      title={title}
      description={description}
      icon={<AlertTriangle className="h-5 w-5 text-red-600" />}
      actions={actions}
      className={className}
    />
  );
}
