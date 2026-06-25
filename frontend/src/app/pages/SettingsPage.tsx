import { Layout } from '../components/Layout';
import { useNavigate } from 'react-router';
import { useAuthStore } from '../../stores/authStore';
import { AlertTriangle, UserX, Check } from 'lucide-react';
import { useState } from 'react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { userApi } from '@/api/userApi';

export function SettingsPage() {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [isConfirmed, setIsConfirmed] = useState(false);
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);
  const [deleteAccountError, setDeleteAccountError] = useState<string | null>(null);

  const handleDeleteClick = () => {
    if (!isConfirmed) return;
    setDeleteAccountError(null);
    setShowConfirmModal(true);
  };

  const confirmDeleteAccount = async () => {
    if (isDeletingAccount) return;

    setDeleteAccountError(null);
    setIsDeletingAccount(true);

    try {
      await userApi.deleteMyAccount();
      setShowConfirmModal(false);
      setIsConfirmed(false);
      
      // 탈퇴 완료: 플래그 설정 후 홈으로 이동
      const setJustWithdrew = useAuthStore.getState().setJustWithdrew;
      setJustWithdrew(true);
      
      await logout();
      navigate('/', { replace: true });
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const status = error.response?.status;
        
        setDeleteAccountError(
          error.response?.data?.message ??
            '회원 탈퇴 처리에 실패했습니다. 잠시 후 다시 시도해주세요.'
        );
        return;
      }

      setDeleteAccountError('회원 탈퇴 처리에 실패했습니다. 잠시 후 다시 시도해주세요.');
    } finally {
      setIsDeletingAccount(false);
    }
  };

  const cancelDelete = () => {
    setShowConfirmModal(false);
    setIsConfirmed(false);
  };

  return (
    <Layout>
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-[480px] mx-auto px-6 py-12">
          {deleteAccountError && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {deleteAccountError}
            </div>
          )}

          {/* 회원탈퇴 카드 */}
          <div className="bg-white border border-red-200 rounded-xl p-6 shadow-sm">
            {/* 상단 경고 영역 */}
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-5 h-5 text-red-600" />
              </div>
              <h1 className="text-xl font-semibold text-foreground">회원 탈퇴</h1>
            </div>

            {/* 안내 문구 */}
            <p className="text-sm text-muted-foreground mb-4">
              계정을 삭제하면 다음 정보가 영구적으로 삭제됩니다.
            </p>

            {/* 목록 */}
            <ul className="text-sm text-muted-foreground mb-4 space-y-1.5">
              <li className="flex items-start gap-2">
                <span className="text-red-500 mt-0.5">•</span>
                작성한 게시글
              </li>
              <li className="flex items-start gap-2">
                <span className="text-red-500 mt-0.5">•</span>
                작성한 리뷰
              </li>
              <li className="flex items-start gap-2">
                <span className="text-red-500 mt-0.5">•</span>
                북마크
              </li>
            </ul>

            {/* 경고 문구 */}
            <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg p-3 mb-6">
              <AlertTriangle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-red-700">
                이 작업은 되돌릴 수 없습니다.
              </p>
            </div>

            {/* 확인 체크박스 */}
            <label className="flex items-center gap-2.5 mb-4 cursor-pointer">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={isConfirmed}
                  onChange={(e) => setIsConfirmed(e.target.checked)}
                  className="sr-only"
                />
                <div
                  className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                    isConfirmed
                      ? 'bg-red-500 border-red-500'
                      : 'border-gray-300 bg-white'
                  }`}
                >
                  {isConfirmed && <Check className="w-3 h-3 text-white" />}
                </div>
              </div>
              <span className="text-sm text-muted-foreground">위 내용을 확인했습니다</span>
            </label>

            {/* 회원탈퇴 버튼 */}
            <Button
              onClick={handleDeleteClick}
              disabled={!isConfirmed}
              className={`w-full py-2.5 rounded-lg font-medium text-sm transition-colors ${
                isConfirmed
                  ? 'bg-red-500 text-white hover:bg-red-600'
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed'
              }`}
            >
              회원 탈퇴
            </Button>
          </div>
        </div>
      </div>

      {/* 탈퇴 확인 모달 */}
      {showConfirmModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-sm w-full mx-4 shadow-xl">
            {/* 모달 헤더 */}
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
                <UserX className="w-5 h-5 text-red-600" />
              </div>
              <h3 className="text-lg font-semibold text-foreground">
                정말로 회원 탈퇴하시겠습니까?
              </h3>
            </div>

            {/* 모달 내용 */}
            <p className="text-sm text-muted-foreground mb-4">
              작성한 게시글과 리뷰가 삭제됩니다.
            </p>

            <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg p-3 mb-6">
              <AlertTriangle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-red-700">
                이 작업은 되돌릴 수 없습니다.
              </p>
            </div>

            {/* 모달 버튼 */}
            <div className="flex gap-3">
              <Button
                onClick={cancelDelete}
                variant="outline"
                className="flex-1 px-4 py-2.5 rounded-lg"
              >
                취소
              </Button>
              <Button
                onClick={confirmDeleteAccount}
                disabled={isDeletingAccount}
                className={`flex-1 px-4 py-2.5 rounded-lg transition-colors ${
                  isDeletingAccount
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-red-500 text-white hover:bg-red-600'
                }`}
              >
                탈퇴하기
              </Button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
