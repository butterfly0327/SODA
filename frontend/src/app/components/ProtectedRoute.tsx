import { useEffect } from 'react';
import { useLocation } from 'react-router';
import { useAuthStore } from '../../stores/authStore';
import { beginSsafyLoginFlow } from '../lib/ssafyLoginFlow';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const justWithdrew = useAuthStore((state) => state.justWithdrew);
  const location = useLocation();

  useEffect(() => {
    if (!isAuthenticated) {
      // 탈퇴 직후에는 자동 로그인 금지, 그냥 홈에 머무르기
      if (justWithdrew) {
        return;
      }
      beginSsafyLoginFlow(
        `${location.pathname}${location.search}${location.hash}`,
      );
    }
  }, [isAuthenticated, justWithdrew, location.hash, location.pathname, location.search]);

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
