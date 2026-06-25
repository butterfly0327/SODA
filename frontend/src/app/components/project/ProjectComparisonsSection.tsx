import { GitCompare, MoreHorizontal, Trash2 } from 'lucide-react';
import { useRef, useState } from 'react';
import type { ComparisonItem } from '../../../stores/chatStore';
import { useClickOutside } from '../../../hooks/useClickOutside';

interface ProjectComparisonsSectionProps {
  comparisons: ComparisonItem[];
  onDeleteComparison: (comparisonId: string) => void;
}

export function ProjectComparisonsSection({
  comparisons,
  onDeleteComparison,
}: ProjectComparisonsSectionProps) {
  const sectionRef = useRef<HTMLDivElement>(null);
  const [comparisonMenuOpen, setComparisonMenuOpen] = useState<string | null>(null);

  useClickOutside({
    ref: sectionRef,
    enabled: comparisonMenuOpen !== null,
    onOutsideClick: () => setComparisonMenuOpen(null),
    onEscape: () => setComparisonMenuOpen(null),
  });

  return (
    <div ref={sectionRef} className="mb-4">
      <div className="px-3 py-2 text-xs text-muted-foreground font-medium">비교 목록</div>
      {comparisons.length > 0 ? (
        <div className="space-y-1">
          {comparisons.map((comparison) => (
            <div key={comparison.id} className="relative">
              <div className="w-full flex items-center gap-2 px-3 py-2 pr-10 rounded-lg hover:bg-sidebar-accent/50 transition-colors text-left group">
                <GitCompare className="w-3.5 h-3.5 text-purple-600 flex-shrink-0" />
                <span className="text-sm text-sidebar-foreground truncate">- {comparison.name}</span>

                <div className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 flex items-center gap-1">
                  <div className="relative">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setComparisonMenuOpen(
                          comparisonMenuOpen === comparison.id ? null : comparison.id
                        );
                      }}
                      className="p-1 hover:bg-sidebar-accent rounded transition-colors"
                      aria-label="비교 항목 더보기"
                    >
                      <MoreHorizontal className="w-4 h-4" />
                    </button>

                    {comparisonMenuOpen === comparison.id && (
                      <div className="absolute right-0 top-full mt-1 w-32 bg-white border border-border shadow-lg rounded-lg overflow-hidden z-50">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteComparison(comparison.id);
                            setComparisonMenuOpen(null);
                          }}
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted transition-colors text-left text-destructive"
                        >
                          <Trash2 className="w-3 h-3" />
                          <span>삭제</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="px-3 py-2 text-xs text-muted-foreground italic">비교 목록이 비어 있습니다</div>
      )}
    </div>
  );
}
