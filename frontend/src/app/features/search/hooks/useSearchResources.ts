import { useEffect, useMemo, useState } from "react";

import { apiClient } from "@/api/client";
import type { ResultCard } from "@/types/recommendation";
import {
  getResourceListRequest,
  mapResourceListResponse,
} from "@/app/lib/resourceSearchApi";

export const SEARCH_PAGE_SIZE = 20;

type ResourceTypeFilter = "dataset" | "api";
type ResourcePriceFilter = "free" | "paid";

type UseSearchResourcesOptions = {
  primeResourceBookmark: (resource: ResultCard) => void;
};

export function useSearchResources({ primeResourceBookmark }: UseSearchResourcesOptions) {
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<ResourceTypeFilter[]>([]);
  const [selectedPriceFilters, setSelectedPriceFilters] = useState<ResourcePriceFilter[]>([]);
  const [allResources, setAllResources] = useState<ResultCard[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(0);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 300);

    return () => clearTimeout(handler);
  }, [searchQuery]);

  useEffect(() => {
    let isCancelled = false;

    const fetchResources = async () => {
      setIsLoading(true);
      try {
        const request = getResourceListRequest();
        const resolvedType =
          selectedTypes.length === 1
            ? selectedTypes[0] === "dataset"
              ? "DATASET"
              : "OPEN_API"
            : "ALL";
        const freeOnly =
          selectedPriceFilters.length === 1 && selectedPriceFilters[0] === "free"
            ? true
            : undefined;

        const response = await apiClient.get(request.url, {
          params: {
            ...request.params,
            type: resolvedType,
            size: SEARCH_PAGE_SIZE,
            page: currentPage,
            keyword: debouncedQuery || undefined,
            freeOnly,
          },
        });

        if (isCancelled) return;

        const metaData = response.data as any;
        const resolvedTotalCount =
          metaData?.data?.totalCount ??
          metaData?.totalCount ??
          metaData?.data?.totalElements ??
          metaData?.page?.totalElements ??
          metaData?.data?.items?.length ??
          metaData?.items?.length ??
          0;

        setTotalCount(resolvedTotalCount);

        if (resolvedTotalCount <= 0) {
          if (!isCancelled) {
            setAllResources([]);
            setIsLoading(false);
          }
          return;
        }

        const list = mapResourceListResponse(response.data as any) as ResultCard[];
        setAllResources(list);
        setIsLoading(false);
      } catch (error) {
        console.error("Failed to fetch resources:", error);
        if (!isCancelled) setIsLoading(false);
      }
    };

    void fetchResources();

    return () => {
      isCancelled = true;
    };
  }, [currentPage, selectedTypes, selectedPriceFilters, debouncedQuery]);

  useEffect(() => {
    allResources.forEach((resource) => {
      primeResourceBookmark(resource);
    });
  }, [allResources, primeResourceBookmark]);

  const isAllFilterActive = selectedTypes.length === 0 && selectedPriceFilters.length === 0;
  const selectedFilterLabels = [
    ...selectedTypes.map((type) => (type === "dataset" ? "Dataset" : "Open API")),
    ...selectedPriceFilters.map((price) => (price === "free" ? "무료" : "유료")),
  ];

  const normalizeAllFilters = (
    nextTypes: ResourceTypeFilter[],
    nextPrices: ResourcePriceFilter[],
  ) => {
    const isEveryFilterSelected = nextTypes.length === 2 && nextPrices.length === 2;

    if (isEveryFilterSelected) {
      return {
        types: [] as ResourceTypeFilter[],
        prices: [] as ResourcePriceFilter[],
      };
    }

    return {
      types: nextTypes,
      prices: nextPrices,
    };
  };

  const toggleTypeFilter = (type: ResourceTypeFilter) => {
    const nextTypes = selectedTypes.includes(type)
      ? selectedTypes.filter((value) => value !== type)
      : [...selectedTypes, type];
    const normalizedFilters = normalizeAllFilters(nextTypes, selectedPriceFilters);
    setSelectedTypes(normalizedFilters.types);
    setSelectedPriceFilters(normalizedFilters.prices);
    setCurrentPage(0);
  };

  const togglePriceFilter = (price: ResourcePriceFilter) => {
    const nextPrices = selectedPriceFilters.includes(price)
      ? selectedPriceFilters.filter((value) => value !== price)
      : [...selectedPriceFilters, price];
    const normalizedFilters = normalizeAllFilters(selectedTypes, nextPrices);
    setSelectedTypes(normalizedFilters.types);
    setSelectedPriceFilters(normalizedFilters.prices);
    setCurrentPage(0);
  };

  const effectivePriceFilter =
    selectedPriceFilters.length === 1 ? selectedPriceFilters[0] : null;

  const priceFilteredResources =
    effectivePriceFilter === "free"
      ? allResources.filter((resource) => resource.isFree)
      : effectivePriceFilter === "paid"
        ? allResources.filter((resource) => !resource.isFree)
        : allResources;

  const sortedResources = useMemo(
    () =>
      [...priceFilteredResources].sort((a, b) => {
        if (a.type === "dataset" && b.type === "dataset") {
          return b.lastUpdate.localeCompare(a.lastUpdate);
        }
        return 0;
      }),
    [priceFilteredResources],
  );

  const isClientOnlyPriceFilter = effectivePriceFilter === "paid";
  const visibleTotalCount = isClientOnlyPriceFilter ? sortedResources.length : totalCount;
  const totalPages = Math.max(1, Math.ceil(visibleTotalCount / SEARCH_PAGE_SIZE));

  return {
    searchQuery,
    setSearchQuery,
    selectedTypes,
    selectedPriceFilters,
    isLoading,
    currentPage,
    setCurrentPage,
    isAllFilterActive,
    selectedFilterLabels,
    toggleTypeFilter,
    togglePriceFilter,
    sortedResources,
    visibleTotalCount,
    totalPages,
  };
}
