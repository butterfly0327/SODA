import test from "node:test";
import assert from "node:assert/strict";

import {
  mapBookmarkItemToResultCard,
} from "./bookmarkPageAdapter.ts";

test("mapBookmarkItemToResultCard maps dataset bookmark into search-card compatible model", () => {
  const card = mapBookmarkItemToResultCard({
    bookmarkId: 101,
    id: 11,
    type: "DATASET",
    title: "서울시 인구 데이터",
    score: 4.5,
    isFree: true,
    isBookmarked: true,
    createdAt: "2026-03-20T10:00:00+09:00",
    bookmarkedAt: "2026-03-26T14:20:00+09:00",
    datasetMeta: {
      publisherName: "서울특별시",
      sourceUpdatedAt: "2026-03-25",
      sampleCount: 1200,
      domains: ["행정", "인구"],
      accessType: "OPEN",
      commercialUseAllowed: true,
      tags: ["서울", "인구"],
    },
    openApiMeta: null,
  });

  assert.equal(card.type, "dataset");
  assert.equal(card.id, 11);
  assert.equal(card.bookmarkId, 101);
  assert.equal(card.name, "서울시 인구 데이터");
  assert.equal(card.source, "서울특별시");
  assert.equal(card.lastUpdate, "2026-03-25");
  assert.deepEqual(card.domains, ["행정", "인구"]);
  assert.equal(card.reliability, "OPEN");
  assert.equal(card.commercialUseAllowed, true);
  assert.deepEqual(card.tags, ["서울", "인구"]);
  assert.equal(card.sampleCount, "1.2K");
  assert.equal(card.isBookmarked, true);
});

test("mapBookmarkItemToResultCard maps open api bookmark into search-card compatible model", () => {
  const card = mapBookmarkItemToResultCard({
    bookmarkId: 202,
    id: 22,
    type: "OPEN_API",
    title: "교통 Open API",
    score: 3.8,
    isFree: false,
    isBookmarked: true,
    createdAt: "2026-03-20T10:00:00+09:00",
    bookmarkedAt: "2026-03-26T09:05:00+09:00",
    datasetMeta: null,
    openApiMeta: {
      provider: "서울시",
      category: "교통",
      avgResponseTime: 0.32,
      authType: "API_KEY",
      dailyLimit: 5000,
      responseFormat: "JSON",
      commercialUse: true,
      tags: ["버스", "교통"],
    },
  });

  assert.equal(card.type, "api");
  assert.equal(card.id, 22);
  assert.equal(card.bookmarkId, 202);
  assert.equal(card.name, "교통 Open API");
  assert.equal(card.category, "교통");
  assert.equal(card.provider, "서울시");
  assert.equal(card.auth, "API_KEY");
  assert.equal(card.freeQuota, "5,000/day");
  assert.equal(card.responseTime, "320ms");
  assert.equal(card.responseFormat, "JSON");
  assert.equal(card.commercialUse, true);
  assert.deepEqual(card.tags, ["버스", "교통"]);
  assert.equal(card.isBookmarked, true);
});
