import test from "node:test";
import assert from "node:assert/strict";

import {
  resolveBookmarkIdForResource,
  toggleResourceBookmark,
} from "./resourceBookmarkApi.ts";

test("resolveBookmarkIdForResource finds bookmark id from paged bookmark responses", async () => {
  const bookmarkId = await resolveBookmarkIdForResource(
    {
      resourceId: 22,
      resourceType: "OPEN_API",
      title: "교통 Open API",
    },
    {
      createBookmark: async () => {
        throw new Error("should not create");
      },
      deleteBookmark: async () => {
        throw new Error("should not delete");
      },
      getMyBookmarks: async (page) => {
        if (page === 0) {
          return {
            content: [],
            totalElements: 2,
            totalPages: 2,
            page: 0,
            size: 100,
          };
        }

        return {
          content: [
            {
              bookmarkId: 202,
              id: 22,
              type: "OPEN_API",
              title: "교통 Open API",
              score: 4.2,
              isFree: true,
              isBookmarked: true,
              createdAt: "2026-03-20T10:00:00+09:00",
              bookmarkedAt: "2026-03-26T10:00:00+09:00",
              datasetMeta: null,
              openApiMeta: null,
            },
          ],
          totalElements: 2,
          totalPages: 2,
          page: 1,
          size: 100,
        };
      },
    },
  );

  assert.equal(bookmarkId, 202);
});

test("toggleResourceBookmark creates bookmark for an unbookmarked resource", async () => {
  let createdPayload:
    | {
        resourceType: "DATASET" | "OPEN_API";
        resourceId: number;
      }
    | undefined;

  const result = await toggleResourceBookmark(
    {
      resourceId: 11,
      resourceType: "DATASET",
      isBookmarked: false,
    },
    {
      createBookmark: async (payload) => {
        createdPayload = payload;
        return {
          bookmarkId: 55,
          resourceType: "DATASET",
          resourceId: 11,
          bookmarkedAt: "2026-03-26T10:00:00+09:00",
        };
      },
      deleteBookmark: async () => {
        throw new Error("should not delete");
      },
      getMyBookmarks: async () => {
        throw new Error("should not load bookmarks");
      },
    },
  );

  assert.deepEqual(createdPayload, {
    resourceType: "DATASET",
    resourceId: 11,
  });
  assert.deepEqual(result, {
    isBookmarked: true,
    bookmarkId: 55,
  });
});

test("toggleResourceBookmark deletes bookmark after resolving bookmark id", async () => {
  let deletedBookmarkId: number | null = null;

  const result = await toggleResourceBookmark(
    {
      resourceId: 22,
      resourceType: "OPEN_API",
      title: "교통 Open API",
      isBookmarked: true,
    },
    {
      createBookmark: async () => {
        throw new Error("should not create");
      },
      deleteBookmark: async (bookmarkId) => {
        deletedBookmarkId = bookmarkId;
      },
      getMyBookmarks: async () => ({
        content: [
          {
            bookmarkId: 202,
            id: 22,
            type: "OPEN_API",
            title: "교통 Open API",
            score: 4.2,
            isFree: true,
            isBookmarked: true,
            createdAt: "2026-03-20T10:00:00+09:00",
            bookmarkedAt: "2026-03-26T10:00:00+09:00",
            datasetMeta: null,
            openApiMeta: null,
          },
        ],
        totalElements: 1,
        totalPages: 1,
        page: 0,
        size: 100,
      }),
    },
  );

  assert.equal(deletedBookmarkId, 202);
  assert.deepEqual(result, {
    isBookmarked: false,
    bookmarkId: null,
  });
});
