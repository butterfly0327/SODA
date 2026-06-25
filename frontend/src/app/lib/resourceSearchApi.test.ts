import test from "node:test";
import assert from "node:assert/strict";

import {
  buildResourceDetailPath,
  getResourceListRequest,
  mapResourceListResponse,
  mergeResourceDetail,
} from "./resourceSearchApi.ts";

test("getResourceListRequest uses the public resources endpoint", () => {
  assert.deepEqual(getResourceListRequest(), {
    url: "/resources",
    params: {
      type: "ALL",
      sort: "SCORE",
    },
  });
});

test("mapResourceListResponse maps dataset and open api resources for SearchPage", () => {
  const resources = mapResourceListResponse({
    status: 200,
    message: "ok",
    data: {
      totalCount: 2,
      items: [
        {
          id: 11,
          type: "DATASET",
          title: "서울시 인구 데이터",
          score: 87,
          isFree: true,
          isBookmarked: true,
          createdAt: "2026-03-10T10:00:00",
          datasetMeta: {
            publisherName: "서울시",
            sourceUpdatedAt: "2026-03-12",
            sampleCount: 12345,
            domains: ["행정", "인구"],
            accessType: "OPEN",
            commercialUseAllowed: true,
            tags: ["서울", "통계"],
          },
          openApiMeta: null,
        },
        {
          id: 22,
          type: "OPEN_API",
          title: "교통 Open API",
          score: 91,
          isFree: false,
          isBookmarked: false,
          createdAt: "2026-03-11T11:00:00",
          datasetMeta: null,
          openApiMeta: {
            provider: "서울시",
            category: "교통",
            avgResponseTime: 0.42,
            authType: "API_KEY",
            dailyLimit: 1000,
            responseFormat: "JSON",
            commercialUse: true,
            tags: ["버스", "도로"],
          },
        },
      ],
    },
  });

  assert.deepEqual(resources, [
    {
      id: 11,
      bookmarkId: null,
      type: "dataset",
      name: "서울시 인구 데이터",
      source: "서울시",
      projectType: "기타",
      taskMatch: 0,
      score: 87,
      domains: ["행정", "인구"],
      tags: ["서울", "통계"],
      commercialUseAllowed: true,
      classCount: 0,
      sampleCount: "12.3K",
      missingRate: 0,
      reliability: "OPEN",
      lastUpdate: "2026-03-12",
      isFree: true,
      isBookmarked: true,
    },
    {
      id: 22,
      bookmarkId: null,
      type: "api",
      name: "교통 Open API",
      category: "교통",
      provider: "서울시",
      projectType: "기타",
      score: 91,
      responseTime: "420ms",
      auth: "API_KEY",
      freeQuota: "1,000/day",
      responseFormat: "JSON",
      commercialUse: true,
      tags: ["버스", "도로"],
      availability: "JSON",
      isFree: false,
      isBookmarked: false,
    },
  ]);
});

test("buildResourceDetailPath matches the backend resource detail route", () => {
  assert.equal(buildResourceDetailPath({ type: "dataset", id: 11 }), "/resources/DATASET/11");
  assert.equal(buildResourceDetailPath({ type: "api", id: 22 }), "/resources/OPEN_API/22");
});

test("mergeResourceDetail keeps bookmark state from the detail response", () => {
  const merged = mergeResourceDetail(
    {
      id: 22,
      type: "api",
      name: "교통 Open API",
      category: "교통",
      projectType: "기타",
      score: 91,
      responseTime: "420ms",
      auth: "API_KEY",
      freeQuota: "1,000/day",
      availability: "N/A",
      isFree: false,
      isBookmarked: false,
    },
    {
      id: 22,
      type: "OPEN_API",
      title: "교통 Open API",
      score: 95,
      isFree: true,
      isBookmarked: true,
      createdAt: "2026-03-11T11:00:00",
      datasetDetail: null,
      openApiDetail: {
        description: "실시간 교통 API",
        provider: "서울시",
        baseUrl: "https://example.com",
        docsUrl: "https://example.com/docs",
        authType: "API_KEY",
        category: "교통",
        tags: [],
        rateLimit: null,
        dailyLimit: 500,
        pricingNote: null,
        commercialUse: true,
        requiresApproval: false,
        responseFormat: "JSON",
        avgResponseTime: 0.21,
      },
    },
  );

  assert.equal(merged.isBookmarked, true);
});
