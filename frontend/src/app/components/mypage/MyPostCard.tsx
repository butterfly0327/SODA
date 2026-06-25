import { MessageSquare } from "lucide-react";

import type { MyPagePostCardViewModel } from "@/app/features/mypage/adapters/mypageAdapter";

interface MyPostCardProps {
  data: MyPagePostCardViewModel;
  onOpen: () => void;
}

export function MyPostCard({ data, onOpen }: MyPostCardProps) {
  const displayCreatedAt = data.createdAt.endsWith(".") ? data.createdAt : `${data.createdAt}.`;

  return (
    <button
      type="button"
      onClick={onOpen}
      className="w-full cursor-pointer rounded-xl border border-border bg-white p-4 text-left shadow-sm transition-shadow hover:shadow-md"
    >
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-[#e8f4fd] text-foreground">
          <MessageSquare className="h-5 w-5" />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex min-h-[4.5rem] flex-col justify-between py-1">
            <div className="min-w-0">
              <h3 className="text-lg font-semibold text-foreground">{data.title}</h3>
            </div>

            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <span>{displayCreatedAt}</span>
            </div>
          </div>
        </div>
      </div>
    </button>
  );
}
