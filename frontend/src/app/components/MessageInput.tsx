import { useState, useRef } from 'react';
import { ArrowUp } from 'lucide-react';
import { useChat } from '../../hooks/useChat';

interface MessageInputProps {
  inline?: boolean;
  onSubmitMessage?: (text: string) => void;
  isLoading?: boolean;
}

export function MessageInput({ inline = false, onSubmitMessage, isLoading: controlledLoading }: MessageInputProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { sendMessage, isLoading: localLoading } = useChat();
  const isLoading = onSubmitMessage ? Boolean(controlledLoading) : localLoading;

  const submitMessage = () => {
    if (!input.trim() || isLoading) return;

    const message = input.trim();

    if (onSubmitMessage) {
      onSubmitMessage(message);
    } else {
      sendMessage(message);
    }

    setInput('');

    // textarea 높이 초기화
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submitMessage();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submitMessage();
    }
  };

  const inputRow = (
    <div className="relative flex items-center gap-3 px-4 py-2 rounded-3xl bg-background border border-border shadow-lg">
      <textarea
        id={inline ? 'inline-message-input' : 'chat-message-input'}
        ref={textareaRef}
        value={input}
        onChange={(e) => {
          setInput(e.target.value);
          e.currentTarget.style.height = 'auto';
          e.currentTarget.style.height = `${Math.min(e.currentTarget.scrollHeight, 200)}px`;
        }}
        onKeyDown={handleKeyDown}
        placeholder="무엇이든 물어보세요"
        rows={1}
        disabled={isLoading}
        className="flex-1 bg-transparent resize-none border-none text-foreground placeholder:text-muted-foreground max-h-[200px] overflow-y-auto focus-visible:outline-none focus-visible:ring-0 rounded"
        style={{ minHeight: '24px' }}
        aria-label="메시지 입력"
      />

      <button
        type="submit"
        disabled={!input.trim() || isLoading}
        className="flex-shrink-0 w-9 h-9 rounded-full bg-black text-white flex items-center justify-center cursor-pointer hover:bg-black/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        aria-label="메시지 전송"
      >
        <ArrowUp className="w-4 h-4" />
      </button>
    </div>
  );

  if (inline) {
    return (
      <form onSubmit={handleSubmit} className="mb-8">
        <label htmlFor="inline-message-input" className="sr-only">
          메시지 입력
        </label>
        {inputRow}
      </form>
    );
  }

  return (
    <div className="sticky bottom-0 w-full bg-background border-t border-border/50 py-4">
      <div className="w-full px-4 sm:px-12">
        <div className="max-w-2xl mx-auto">
          <form onSubmit={handleSubmit} className="relative">
            <label htmlFor="chat-message-input" className="sr-only">
              메시지 입력
            </label>
            {inputRow}
          </form>
        </div>
      </div>
    </div>
  );
}
