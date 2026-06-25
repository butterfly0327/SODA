import { Link } from 'react-router';

export function NotFoundPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-background px-6">
      <section className="max-w-md w-full rounded-xl border border-border bg-card p-8 text-center shadow-sm">
        <p className="text-sm text-muted-foreground">404</p>
        <h1 className="mt-2 text-2xl font-semibold text-foreground">페이지를 찾을 수 없습니다</h1>
        <p className="mt-3 text-sm text-muted-foreground">
          주소가 변경되었거나 삭제된 페이지입니다. 홈으로 돌아가 다시 탐색해 주세요.
        </p>
        <Link
          to="/"
          className="mt-6 inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90"
        >
          홈으로 이동
        </Link>
      </section>
    </main>
  );
}
