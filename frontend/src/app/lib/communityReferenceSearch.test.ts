import test from "node:test";
import assert from "node:assert/strict";

import {
  REFERENCE_SEARCH_PAGE_SIZE,
  resolveReferenceSearchPlan,
} from "./communityReferenceSearch.ts";

test("resolveReferenceSearchPlan uses a single-page capped search for dataset references", () => {
  assert.deepEqual(resolveReferenceSearchPlan("dataset", " 데이터 "), {
    resolvedType: "DATASET",
    keyword: "데이터",
    pageSize: REFERENCE_SEARCH_PAGE_SIZE,
    page: 0,
    fetchAllPages: false,
  });
});

test("resolveReferenceSearchPlan uses a single-page capped search for open api references", () => {
  assert.deepEqual(resolveReferenceSearchPlan("api", ""), {
    resolvedType: "OPEN_API",
    keyword: undefined,
    pageSize: REFERENCE_SEARCH_PAGE_SIZE,
    page: 0,
    fetchAllPages: false,
  });
});
