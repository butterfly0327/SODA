import { useEffect } from 'react';
import type { RefObject } from 'react';

interface UseClickOutsideOptions<T extends HTMLElement> {
  ref: RefObject<T | null>;
  enabled?: boolean;
  onOutsideClick: () => void;
  onEscape?: () => void;
}

export function useClickOutside<T extends HTMLElement>({
  ref,
  enabled = true,
  onOutsideClick,
  onEscape,
}: UseClickOutsideOptions<T>) {
  useEffect(() => {
    if (!enabled) {
      return;
    }

    const handleMouseDown = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        onOutsideClick();
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onEscape?.();
      }
    };

    document.addEventListener('mousedown', handleMouseDown);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('mousedown', handleMouseDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [enabled, onEscape, onOutsideClick, ref]);
}
