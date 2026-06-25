import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { Layout } from '../components/Layout';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/api/client';
import { userApi } from '@/api/userApi';
import { useAuthStore } from '@/stores/authStore';
import { consumeLoginRedirectTarget } from '../lib/authNavigation';
import {
  beginSsafyLoginFlow,
  clearSsafyLoginInFlight,
  hasSsafyConsentGranted,
  markSsafyConsentGranted,
} from '../lib/ssafyLoginFlow';
import { resolveSsafyOAuthConfig } from '../lib/ssafyOAuthConfig';
import { ErrorState } from '../components/StateView';

interface CallbackPayload {
  accessToken: string;
  refreshToken?: string;
  isNewUser: boolean;
}

interface ApiResponse<T> {
  status: number;
  message: string;
  data: T;
}

export function AuthCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const oauthLoginSuccess = useAuthStore((state) => state.oauthLoginSuccess);
  const oauthLoginFail = useAuthStore((state) => state.oauthLoginFail);

  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    const run = async () => {
      clearSsafyLoginInFlight();

      const oauthError = searchParams.get('error');
      if (oauthError) {
        const message = 'SSAFY OAuth 인증에 실패했습니다. 다시 시도해주세요.';
        oauthLoginFail(message);
        setErrorMessage(message);
        setIsLoading(false);
        return;
      }

      const code = searchParams.get('code');
      if (!code) {
        const message = '인가 코드가 없습니다. 로그인 절차를 다시 진행해주세요.';
        oauthLoginFail(message);
        setErrorMessage(message);
        setIsLoading(false);
        return;
      }

      try {
        const { redirectUri: redirectUrl } = resolveSsafyOAuthConfig(
          import.meta.env,
          {
            basePath: import.meta.env.BASE_URL || '/',
            origin: window.location.origin,
          },
        );

        const response = await apiClient.post<ApiResponse<CallbackPayload>>('/auth/callback', {
          code,
          redirectUrl,
        }, {
          skipAuth: true,
        });

        const callbackResult = response.data.data;
        oauthLoginSuccess({
          accessToken: callbackResult.accessToken,
          refreshToken: callbackResult.refreshToken,
        });

        try {
          const profile = await userApi.getMyProfile();
          oauthLoginSuccess({
            accessToken: callbackResult.accessToken,
            refreshToken: callbackResult.refreshToken,
            user: {
              id: String(profile.id),
              email: profile.email ?? '',
              name: profile.name ?? '',
            },
          });
        } catch {
          // Keep authenticated session even when profile hydration fails.
        }

        if (callbackResult.isNewUser && !hasSsafyConsentGranted()) {
          navigate('/signup?consent=required', { replace: true });
          return;
        }

        markSsafyConsentGranted();

        navigate(consumeLoginRedirectTarget() || '/', { replace: true });
      } catch {
        const message = '인가 코드 처리에 실패했습니다. 잠시 후 다시 시도해주세요.';
        oauthLoginFail(message);
        setErrorMessage(message);
      } finally {
        setIsLoading(false);
      }
    };

    run();
  }, [navigate, oauthLoginFail, oauthLoginSuccess, searchParams]);

  return (
    <Layout>
      <main className="flex-1 overflow-y-auto">
        {!isLoading && errorMessage ? (
          <div className="max-w-xl mx-auto px-6 py-12">
            <div className="bg-white border border-border rounded-xl p-8 shadow-sm">
              <ErrorState
                title="인증 처리 실패"
                description={errorMessage}
                className="border-0 bg-transparent p-0"
                actions={
                  <>
                    <Button onClick={() => beginSsafyLoginFlow()}>
                      SSAFY 로그인 다시 시도
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => navigate('/', { replace: true })}
                    >
                      홈으로 이동
                    </Button>
                  </>
                }
              />
            </div>
          </div>
        ) : null}
      </main>
    </Layout>
  );
}
