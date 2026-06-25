import { X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useClickOutside } from '../../../hooks/useClickOutside';

interface RenameConversationModalProps {
  initialTitle: string;
  onClose: () => void;
  onConfirm: (title: string) => void;
}

export function RenameConversationModal({
  initialTitle,
  onClose,
  onConfirm,
}: RenameConversationModalProps) {
  const [nextTitle, setNextTitle] = useState(initialTitle);
  const modalRef = useRef<HTMLDivElement>(null);

  useClickOutside({
    ref: modalRef,
    enabled: true,
    onOutsideClick: onClose,
    onEscape: onClose,
  });

  useEffect(() => {
    setNextTitle(initialTitle);
  }, [initialTitle]);

  const handleConfirm = () => {
    if (!nextTitle.trim()) {
      return;
    }

    onConfirm(nextTitle.trim());
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div
        ref={modalRef}
        className="bg-white rounded-2xl w-[500px] p-6 relative shadow-2xl border border-gray-200"
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute top-6 right-6 p-1 hover:bg-gray-100 rounded-md transition-colors"
        >
          <X className="w-5 h-5 text-gray-600" />
        </button>

        <h2 className="text-2xl font-semibold mb-6">채팅 이름 변경</h2>

        <div className="mb-6">
          <input
            type="text"
            value={nextTitle}
            onChange={(e) => setNextTitle(e.target.value)}
            placeholder="새 이름을 입력하세요"
            className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#e8f4fd] focus:border-transparent"
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleConfirm();
              }
            }}
          />
        </div>

        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors"
          >
            취소
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            className="px-4 py-2 rounded-lg bg-[#e8f4fd] hover:bg-[#d0e8f9] text-gray-800 font-medium transition-colors"
          >
            확인
          </button>
        </div>
      </div>
    </div>
  );
}
