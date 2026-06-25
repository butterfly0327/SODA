import type { CreateBookmarkResponse, MyBookmarksPage } from "../../api/types.ts";

export type BookmarkResourceType = "DATASET" | "OPEN_API";

export type ResourceBookmarkTarget = {
  resourceId: number;
  resourceType: BookmarkResourceType;
  isBookmarked: boolean;
  bookmarkId?: number | null;
  title?: string;
};

type BookmarkApiDeps = {
  createBookmark: (payload: {
    resourceType: BookmarkResourceType;
    resourceId: number;
  }) => Promise<CreateBookmarkResponse>;
  deleteBookmark: (bookmarkId: number) => Promise<void>;
  getMyBookmarks: (
    page?: number,
    size?: number,
    filters?: {
      keyword?: string;
      type?: BookmarkResourceType;
      freeOnly?: boolean;
    },
  ) => Promise<MyBookmarksPage>;
};

const defaultDeps: BookmarkApiDeps = {
  createBookmark: async (payload) => {
    const { bookmarkApi } = await import("../../api/bookmarkApi.ts");
    return bookmarkApi.createBookmark(payload);
  },
  deleteBookmark: async (bookmarkId) => {
    const { bookmarkApi } = await import("../../api/bookmarkApi.ts");
    return bookmarkApi.deleteBookmark(bookmarkId);
  },
  getMyBookmarks: async (page, size, filters) => {
    const { userApi } = await import("../../api/userApi.ts");
    return userApi.getMyBookmarks(page, size, filters);
  },
};

export function normalizeBookmarkResourceType(
  value: "dataset" | "api" | BookmarkResourceType,
): BookmarkResourceType {
  if (value === "dataset" || value === "DATASET") {
    return "DATASET";
  }

  return "OPEN_API";
}

function normalizeKeyword(title?: string) {
  const trimmed = title?.trim();
  return trimmed ? trimmed : undefined;
}

async function findBookmarkIdInPagedResults(
  target: Pick<ResourceBookmarkTarget, "resourceId" | "resourceType"> & { title?: string },
  deps: BookmarkApiDeps,
  keyword?: string,
) {
  let page = 0;

  while (true) {
    const response = await deps.getMyBookmarks(page, 100, {
      type: target.resourceType,
      keyword,
    });

    const matched = response.content.find(
      (item) =>
        item.id === target.resourceId && item.type === target.resourceType,
    );

    if (matched) {
      return matched.bookmarkId;
    }

    if (page >= response.totalPages - 1) {
      return null;
    }

    page += 1;
  }
}

export async function resolveBookmarkIdForResource(
  target: Pick<ResourceBookmarkTarget, "resourceId" | "resourceType" | "bookmarkId"> & {
    title?: string;
  },
  deps: BookmarkApiDeps = defaultDeps,
) {
  if (typeof target.bookmarkId === "number" && Number.isFinite(target.bookmarkId)) {
    return target.bookmarkId;
  }

  const keyword = normalizeKeyword(target.title);
  const resolvedFromKeyword = await findBookmarkIdInPagedResults(target, deps, keyword);
  if (resolvedFromKeyword !== null || !keyword) {
    return resolvedFromKeyword;
  }

  return findBookmarkIdInPagedResults(target, deps, undefined);
}

export async function toggleResourceBookmark(
  target: ResourceBookmarkTarget,
  deps: BookmarkApiDeps = defaultDeps,
) {
  if (!target.isBookmarked) {
    const created = await deps.createBookmark({
      resourceType: target.resourceType,
      resourceId: target.resourceId,
    });

    return {
      isBookmarked: true,
      bookmarkId: created.bookmarkId,
    };
  }

  const bookmarkId = await resolveBookmarkIdForResource(target, deps);
  if (bookmarkId === null) {
    return {
      isBookmarked: false,
      bookmarkId: null,
    };
  }

  await deps.deleteBookmark(bookmarkId);

  return {
    isBookmarked: false,
    bookmarkId: null,
  };
}
