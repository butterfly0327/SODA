import type { MyBookmarksPage } from "@/api/types";
import type { SearchResourceCard } from "@/app/lib/resourceSearchApi";
import { mapResourceItem } from "@/app/lib/resourceSearchApi";

type BookmarkItem = MyBookmarksPage["content"][number];

export function mapBookmarkItemToResultCard(item: BookmarkItem): SearchResourceCard {
  return mapResourceItem({
    bookmarkId: item.bookmarkId,
    id: item.id,
    type: item.type,
    title: item.title,
    score: item.score,
    isFree: item.isFree,
    isBookmarked: item.isBookmarked,
    createdAt: item.createdAt,
    datasetMeta: item.datasetMeta,
    openApiMeta: item.openApiMeta,
  });
}
