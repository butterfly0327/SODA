import { Code, Database, Star } from "lucide-react";

import type { MyPageReviewCardViewModel } from "@/app/features/mypage/adapters/mypageAdapter";

interface MyReviewCardProps {
  data: MyPageReviewCardViewModel;
  onOpen: () => void;
}

export function MyReviewCard({ data, onOpen }: MyReviewCardProps) {
  const isDataset = data.resourceType === "dataset";
  const displayCreatedAt = data.createdAt.endsWith(".") ? data.createdAt : `${data.createdAt}.`;
  const handleOpen = () => {
    onOpen();
  };

  return (
    <button
      type="button"
      className="w-full cursor-pointer rounded-xl border border-border bg-white p-4 text-left shadow-sm transition-shadow hover:shadow-md"
      onClick={handleOpen}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          handleOpen();
        }
      }}
    >
      <div className="flex items-start gap-3">
        <div
          className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg ${
            isDataset ? "ds-resource-dataset-icon" : "ds-resource-api-icon"
          }`}
        >
          {isDataset ? <Database className="h-5 w-5" /> : <Code className="h-5 w-5" />}
        </div>

        <div className="min-w-0 flex-1">
          <div className="min-w-0">
            <div className="flex min-h-10 items-center">
              <h3 className="text-lg font-semibold text-foreground">{data.resourceTitle}</h3>
            </div>
            <div className="mt-1 space-y-2">
              <p className="text-sm text-muted-foreground">{displayCreatedAt}</p>
              <div className="flex items-center gap-1 text-[#4f76df]">
                {[1, 2, 3, 4, 5].map((starValue) => (
                  <Star
                    key={`${data.id}-star-${starValue}`}
                    className={`h-4 w-4 ${
                      starValue <= data.rating ? "fill-[#4f76df]" : "text-slate-300"
                    }`}
                  />
                ))}
              </div>

              <p className="line-clamp-2 text-sm font-semibold text-foreground">"{data.content}"</p>
            </div>
          </div>
        </div>
      </div>
    </button>
  );
}
