import test from "node:test";
import assert from "node:assert/strict";

import { formatMyPageDate, mapMyPostItemToCard, mapMyReviewItemToCard } from "./mypageAdapter.ts";

test("formatMyPageDate formats ISO string as yyyy.mm.dd", () => {
  assert.equal(formatMyPageDate("2026-03-26T18:20:00+09:00"), "2026.03.26");
});

test("mapMyPostItemToCard keeps card metrics", () => {
  const result = mapMyPostItemToCard({
    id: 7,
    title: "게시글 제목",
    createdAt: "2026-03-26T18:20:00+09:00",
    likeCount: 5,
    referenceCount: 2,
  });

  assert.deepEqual(result, {
    id: "7",
    title: "게시글 제목",
    createdAt: "2026.03.26",
    likeCount: 5,
    referenceCount: 2,
  });
});

test("mapMyPostItemToCard preserves zero like counts", () => {
  const result = mapMyPostItemToCard({
    id: 9,
    title: "좋아요 0 게시글",
    createdAt: "2026-03-26T18:20:00+09:00",
    likeCount: 0,
    referenceCount: 0,
  });

  assert.equal(result.likeCount, 0);
});

test("mapMyReviewItemToCard maps resource type labels", () => {
  const result = mapMyReviewItemToCard({
    id: 11,
    resourceType: "OPEN_API",
    resourceId: 99,
    resourceTitle: "리소스 제목",
    rating: 4,
    content: "리뷰 내용",
    createdAt: "2026-03-26T18:20:00+09:00",
  });

  assert.deepEqual(result, {
    id: "11",
    resourceId: 99,
    resourceType: "api",
    resourceTypeLabel: "Open API",
    resourceTitle: "리소스 제목",
    isTitleFallback: false,
    rating: 4,
    content: "리뷰 내용",
    createdAt: "2026.03.26",
  });
});
