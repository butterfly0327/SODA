import { Bookmark, Code, Database } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { ResourceCardViewModel } from "@/app/lib/resourceCardAdapter";

interface ResourceCardProps {
  data: ResourceCardViewModel;
  onOpenDetail?: () => void;
  onToggleBookmark?: () => void;
  variant?: "default" | "mypage" | "bookmark" | "search";
}

export function ResourceCard({
  data,
  onOpenDetail,
  onToggleBookmark,
  variant = "default",
}: ResourceCardProps) {
  const isDataset = data.type === "dataset";
  const handleOpenDetail = () => {
    if (onOpenDetail) {
      onOpenDetail();
    }
  };

  if (variant === "mypage") {
    return (
      <article
        className={`rounded-xl border border-border bg-white p-4 shadow-sm transition-shadow hover:shadow-md ${
          onOpenDetail ? "cursor-pointer" : ""
        }`}
        role={onOpenDetail ? "button" : undefined}
        tabIndex={onOpenDetail ? 0 : undefined}
        onClick={onOpenDetail ? handleOpenDetail : undefined}
        onKeyDown={
          onOpenDetail
            ? (event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  handleOpenDetail();
                }
              }
            : undefined
        }
      >
        <div className="flex items-center gap-3">
          <div
            className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg ${
              isDataset ? "ds-resource-dataset-icon" : "ds-resource-api-icon"
            }`}
          >
            {isDataset ? <Database className="h-5 w-5" /> : <Code className="h-5 w-5 text-black" />}
          </div>

          <div className="min-w-0 flex flex-1 items-center">
            <div className="flex h-10 w-full items-center justify-between gap-3">
              <h3 className="truncate text-lg font-semibold text-foreground">{data.title}</h3>

              {onToggleBookmark ? (
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    onToggleBookmark();
                  }}
                  onKeyDown={(event) => {
                    event.stopPropagation();
                  }}
                  disabled={data.isBookmarkPending}
                  title={data.isBookmarked ? "북마크 해제" : "북마크 추가"}
                  aria-label={data.isBookmarked ? "북마크 해제" : "북마크 추가"}
                  className="rounded-md p-2.5 transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <Bookmark
                    className={`h-5 w-5 ${
                      data.isBookmarked ? "fill-[#4f76df] text-[#4f76df]" : "text-muted-foreground"
                    }`}
                  />
                </button>
              ) : null}
            </div>
          </div>
        </div>
      </article>
    );
  }

  const defaultSurfaceClass =
    variant === "bookmark" || variant === "search"
      ? "rounded-xl border border-border bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
      : "ds-card-surface p-6 transition-shadow hover:shadow-md";
  const isCardClickableVariant = variant === "bookmark" || variant === "search";

  return (
    <article
      className={`${defaultSurfaceClass} ${isCardClickableVariant && onOpenDetail ? "cursor-pointer" : ""}`}
      role={isCardClickableVariant && onOpenDetail ? "button" : undefined}
      tabIndex={isCardClickableVariant && onOpenDetail ? 0 : undefined}
      onClick={isCardClickableVariant && onOpenDetail ? handleOpenDetail : undefined}
      onKeyDown={
        isCardClickableVariant && onOpenDetail
          ? (event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                handleOpenDetail();
              }
            }
          : undefined
      }
    >
      <div className="flex items-start gap-4">
        <div
          className={`flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg ${
            isDataset ? "ds-resource-dataset-icon" : "ds-resource-api-icon"
          }`}
        >
          {isDataset ? (
            <Database className="h-6 w-6" />
          ) : (
            <Code className={variant === "bookmark" ? "h-6 w-6 text-black" : "h-6 w-6"} />
          )}
        </div>

        <div className="flex-1">
          <div className="mb-2 flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="mb-1 text-lg font-semibold text-foreground">{data.title}</h3>
              <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                {data.topMeta.map((item, index) => (
                  <span key={`${data.id}-${item}`} className="inline-flex items-center gap-3">
                    {index > 0 ? <span aria-hidden="true">•</span> : null}
                    <span>{item}</span>
                  </span>
                ))}
              </div>
            </div>

            {onToggleBookmark ? (
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onToggleBookmark();
                }}
                onKeyDown={(event) => {
                  event.stopPropagation();
                }}
                disabled={data.isBookmarkPending}
                title={data.isBookmarked ? "북마크 해제" : "북마크 추가"}
                aria-label={data.isBookmarked ? "북마크 해제" : "북마크 추가"}
                className={`rounded-md p-2.5 ${
                  variant === "search" || variant === "bookmark"
                    ? "cursor-pointer disabled:cursor-pointer disabled:opacity-40"
                    : "transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-40"
                }`}
              >
                <Bookmark
                  className={`h-5 w-5 ${
                    data.isBookmarked ? "fill-[#4f76df] text-[#4f76df]" : "text-muted-foreground"
                  }`}
                />
              </button>
            ) : null}
          </div>

          <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
            {data.detailItems.map((item) => (
              <div key={`${item.label}-${item.value}`}>
                <p className="mb-1 text-xs text-muted-foreground">{item.label}</p>
                <p className="truncate text-sm font-semibold text-foreground" title={item.value}>
                  {item.value}
                </p>
              </div>
            ))}
          </div>

          {data.tags && data.tags.length > 0 ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {data.tags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center rounded-md border border-border bg-muted px-2 py-1 text-xs font-medium text-muted-foreground"
                >
                  #{tag}
                </span>
              ))}
            </div>
          ) : null}

          {onOpenDetail && !isCardClickableVariant ? (
            <div className="mt-4 flex items-center gap-2">
              <Button
                className="cursor-pointer border border-border bg-white px-4 py-2 text-sm font-medium text-foreground shadow-sm transition-all hover:border-[#e8f4fd] hover:bg-[#e8f4fd] hover:text-[#2b6ea6]"
                onClick={onOpenDetail}
              >
                상세보기
              </Button>
            </div>
          ) : null}
        </div>
      </div>
    </article>
  );
}
