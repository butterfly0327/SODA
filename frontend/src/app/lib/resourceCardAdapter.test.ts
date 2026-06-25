import test from "node:test";
import assert from "node:assert/strict";

import type { ResultCard } from "../../types/recommendation.ts";
import { mapBookmarkItemToResultCard } from "./bookmarkPageAdapter.ts";
import { buildSearchResourceCardModel } from "./resourceCardAdapter.ts";

test("buildSearchResourceCardModel maps dataset result into the shared card shape", () => {
  const resource: ResultCard = {
    id: 12,
    type: "dataset",
    name: "서울시 공공데이터",
    source: "서울특별시",
    lastUpdate: "2026-03-26",
    domains: ["교통", "행정"],
    reliability: "High",
    commercialUseAllowed: true,
    isFree: true,
    tags: ["서울", "공공"],
  };

  const card = buildSearchResourceCardModel(resource, {
    isBookmarked: true,
    isBookmarkPending: false,
  });
  const expectedDate = new Date("2026-03-26").toLocaleDateString("ko-KR");

  assert.equal(card.type, "dataset");
  assert.equal(card.title, "서울시 공공데이터");
  assert.deepEqual(card.topMeta, ["출처: 서울특별시", `업데이트: ${expectedDate}`]);
  assert.equal(card.detailItems[0]?.label, "도메인");
  assert.equal(card.detailItems[0]?.value, "교통, 행정");
  assert.equal(card.isBookmarked, true);
  assert.deepEqual(card.tags, ["서울", "공공"]);
});

test("buildSearchResourceCardModel renders bookmark-backed result with the same card layout", () => {
  const bookmarkResource = mapBookmarkItemToResultCard({
    bookmarkId: 7,
    id: 101,
    type: "OPEN_API",
    title: "Weather Forecast API",
    score: 4.5,
    isFree: true,
    isBookmarked: true,
    createdAt: "2026-03-20T10:00:00+09:00",
    bookmarkedAt: "2026-03-26T10:00:00+09:00",
    datasetMeta: null,
    openApiMeta: {
      provider: "기상청",
      category: "Weather",
      avgResponseTime: 0.1,
      authType: "API_KEY",
      dailyLimit: 500,
      responseFormat: "JSON",
      commercialUse: true,
      tags: ["날씨", "예보"],
    },
  });

  const card = buildSearchResourceCardModel(bookmarkResource, {
    isBookmarked: true,
    isBookmarkPending: true,
  });

  assert.equal(card.type, "api");
  assert.equal(card.title, "Weather Forecast API");
  assert.deepEqual(card.topMeta, ["카테고리: Weather", "제공: 기상청"]);
  assert.equal(card.detailItems[0]?.label, "인증 방식");
  assert.equal(card.detailItems[0]?.value, "API_KEY");
  assert.equal(card.detailItems[1]?.value, "JSON");
  assert.equal(card.detailItems[3]?.label, "비용");
  assert.equal(card.isBookmarked, true);
  assert.equal(card.isBookmarkPending, true);
});
