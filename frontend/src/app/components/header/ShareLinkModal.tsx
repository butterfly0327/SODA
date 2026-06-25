import { Copy, X } from 'lucide-react';
import { useRef, useState } from 'react';
import { useClickOutside } from '../../../hooks/useClickOutside';

interface ShareLinkModalProps {
  shareLink: string;
  onClose: () => void;
}

export function ShareLinkModal({ shareLink, onClose }: ShareLinkModalProps) {
  const [copied, setCopied] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);

  useClickOutside({
    ref: modalRef,
    enabled: true,
    onOutsideClick: onClose,
    onEscape: onClose,
  });

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div
        ref={modalRef}
        className="bg-white rounded-2xl w-[600px] p-6 relative shadow-2xl border border-gray-200"
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute top-6 right-6 p-1 hover:bg-gray-100 rounded-md transition-colors"
        >
          <X className="w-5 h-5 text-gray-600" />
        </button>

        <h2 className="text-2xl font-semibold mb-6">공유 가능한 공개 링크</h2>

        <div className="flex items-center gap-3 mb-4">
          <div className="flex-1 bg-gray-100 rounded-lg px-4 py-3">
            <input
              type="text"
              value={shareLink}
              readOnly
              className="w-full bg-transparent outline-none text-gray-700"
            />
          </div>
          <button
            type="button"
            onClick={handleCopyLink}
            className="bg-[#e8f4fd] hover:bg-[#d0e8f9] text-gray-800 px-6 py-3 rounded-lg font-medium flex items-center gap-2 transition-colors"
          >
            <Copy className="w-4 h-4" />
            {copied ? '복사됨!' : '링크 복사'}
          </button>
        </div>

        <div className="flex gap-2 mb-8 text-sm text-gray-600">
          <span className="text-gray-400">ⓘ</span>
          <p>
            공개 링크는 다시 공유할 수 있습니다.{' '}
            <span className="text-blue-600">신중하게</span> 공유하고 언제든지{' '}
            <span className="text-blue-600">삭제하세요</span>. 서드 파티와 공유하는 경우, 서드 파티의 정책이 적용됩니다.
          </p>
        </div>

        <div className="flex justify-center gap-8">
          <button type="button" className="flex flex-col items-center gap-2 hover:opacity-80 transition-opacity">
            <div className="w-14 h-14 bg-blue-700 rounded-full flex items-center justify-center">
              <span className="text-white text-xl font-bold">in</span>
            </div>
            <span className="text-sm text-gray-700">LinkedIn</span>
          </button>
          <button type="button" className="flex flex-col items-center gap-2 hover:opacity-80 transition-opacity">
            <div className="w-14 h-14 bg-blue-600 rounded-full flex items-center justify-center">
              <span className="text-white text-3xl font-bold">f</span>
            </div>
            <span className="text-sm text-gray-700">Facebook</span>
          </button>
          <button type="button" className="flex flex-col items-center gap-2 hover:opacity-80 transition-opacity">
            <div className="w-14 h-14 bg-black rounded-full flex items-center justify-center">
              <span className="text-white text-xl font-bold">𝕏</span>
            </div>
            <span className="text-sm text-gray-700">X</span>
          </button>
          <button type="button" className="flex flex-col items-center gap-2 hover:opacity-80 transition-opacity">
            <div className="w-14 h-14 bg-orange-600 rounded-full flex items-center justify-center">
              <span className="text-white text-2xl">☺</span>
            </div>
            <span className="text-sm text-gray-700">Reddit</span>
          </button>
        </div>
      </div>
    </div>
  );
}
