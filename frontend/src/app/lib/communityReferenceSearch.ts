export type ReferenceSearchTab = "dataset" | "api";

export const REFERENCE_SEARCH_PAGE_SIZE = 20;

export function resolveReferenceSearchPlan(
  referenceTab: ReferenceSearchTab,
  rawKeyword: string,
) {
  const keyword = rawKeyword.trim() || undefined;

  return {
    resolvedType: referenceTab === "dataset" ? "DATASET" : "OPEN_API",
    keyword,
    pageSize: REFERENCE_SEARCH_PAGE_SIZE,
    page: 0,
    fetchAllPages: false,
  } as const;
}
