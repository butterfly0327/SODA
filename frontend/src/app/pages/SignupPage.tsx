import { useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { ArrowRight, ShieldCheck } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router';
import { Layout } from '../components/Layout';
import { Button } from '@/components/ui/button';
import { buildSsafyAuthorizeUrl } from '../lib/ssafyOAuth';
import { markSsafyConsentGranted } from '../lib/ssafyLoginFlow';
import { consumeLoginRedirectTarget } from '../lib/authNavigation';
import { useAuthStore } from '../../stores/authStore';

interface SignupFormValues {
  agreePolicy: boolean;
}

export function SignupPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const authorizeUrl = useMemo(() => buildSsafyAuthorizeUrl(), []);
  const isPostAuthConsentMode = searchParams.get('consent') === 'required' && isAuthenticated;

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignupFormValues>({
    defaultValues: {
      agreePolicy: false,
    },
    mode: 'onSubmit',
  });

  const onSubmit = async () => {
    markSsafyConsentGranted();

    if (isPostAuthConsentMode) {
      navigate(consumeLoginRedirectTarget() || '/', { replace: true });
      return;
    }

    window.location.href = authorizeUrl;
  };

  return (
    <Layout>
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-xl mx-auto px-6 py-12">
          <div className="bg-white border border-border rounded-xl p-8 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <ShieldCheck className="w-6 h-6 text-foreground" />
              <h1 className="text-2xl font-semibold text-foreground">권한 동의</h1>
            </div>

              <p className="text-sm text-muted-foreground mb-6">
                {isPostAuthConsentMode
                  ? '최초 로그인 사용자 확인을 위해 권한 동의를 완료해주세요.'
                  : '최초 1회 권한 동의 후 SSAFY 로그인으로 이동합니다.'}
              </p>

            <form noValidate onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <label className="flex items-start gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="mt-0.5 h-4 w-4 rounded border-gray-300"
                  aria-invalid={Boolean(errors.agreePolicy)}
                  aria-describedby={errors.agreePolicy ? 'signup-agree-error' : undefined}
                  {...register('agreePolicy', {
                    validate: (value) => value || '회원가입을 위해 안내사항 동의가 필요합니다.',
                  })}
                />
                <span className="text-sm text-muted-foreground">
                  개인정보 수집 및 OAuth 인증 진행 안내에 동의합니다.
                </span>
              </label>
              {errors.agreePolicy && (
                <p id="signup-agree-error" className="text-sm text-red-600" role="alert" aria-live="assertive">
                  {errors.agreePolicy.message}
                </p>
              )}

              <Button type="submit" className="w-full h-11 text-base" disabled={isSubmitting}>
                {isPostAuthConsentMode ? '동의하고 계속' : '동의하고 SSAFY 로그인'}
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </form>
          </div>
        </div>
      </main>
    </Layout>
  );
}
