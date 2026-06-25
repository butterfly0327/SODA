import { AlertTriangle, CheckCircle2, ShieldCheck, X } from "lucide-react";
import { useRef } from "react";
import { useClickOutside } from "../../../hooks/useClickOutside";

interface SsafyPermissionModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isLoading?: boolean;
}

export function SsafyPermissionModal({
  open,
  onClose,
  onConfirm,
  isLoading = false,
}: SsafyPermissionModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  const handleClose = () => {
    if (isLoading) {
      return;
    }
    onClose();
  };

  useClickOutside({
    ref: modalRef,
    enabled: open && !isLoading,
    onOutsideClick: handleClose,
    onEscape: handleClose,
  });

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[70] bg-black/50 flex items-center justify-center p-4">
      <div
        ref={modalRef}
        className="relative w-full max-w-xl rounded-2xl border border-border bg-white p-6 shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-label="SSAFY 권한 확인"
      >
        <button
          type="button"
          onClick={handleClose}
          className="absolute right-4 top-4 rounded-md p-1 text-muted-foreground hover:bg-muted"
          aria-label="모달 닫기"
          disabled={isLoading}
        >
          <X className="h-5 w-5" />
        </button>

        <div className="mb-4 flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-[#3e7fb4]" />
          <h2 className="text-lg font-semibold text-foreground">SSAFY 로그인 권한 확인</h2>
        </div>

        <p className="text-sm text-muted-foreground leading-6">
          SSAFY 로그인 진행 시 서비스는 로그인 처리를 위해 기본 사용자 정보를 요청합니다.
          아래 항목 확인 후 계속 진행해 주세요.
        </p>

        <div className="mt-5 rounded-lg border border-border bg-muted/30 p-4">
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-foreground">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            요청 권한
          </div>
          <ul className="space-y-1 text-sm text-muted-foreground">
            <li>- 사용자 식별자(userId)</li>
            <li>- 이메일(email)</li>
            <li>- 이름(name)</li>
          </ul>
        </div>

        <div className="mt-4 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <p>
            동의 후 SSAFY 인증 페이지로 이동합니다. 인증 취소 시 로그인 페이지로 돌아옵니다.
          </p>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={handleClose}
            className="h-10 rounded-md border border-border px-4 text-sm font-medium text-foreground hover:bg-muted"
            disabled={isLoading}
          >
            취소
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="h-10 rounded-md bg-[#dce9f5] px-4 text-sm font-medium text-foreground hover:bg-[#d5e5f2]"
            disabled={isLoading}
          >
            동의하고 계속
          </button>
        </div>
      </div>
    </div>
  );
}
