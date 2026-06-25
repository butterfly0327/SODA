import type { ResultCard } from "../../types/recommendation";

export type ResourceCardDetailItem = {
  label: string;
  value: string;
};

export type ResourceCardViewModel = {
  type: "dataset" | "api";
  title: string;
  topMeta: string[];
  detailItems: ResourceCardDetailItem[];
  tags?: string[];
  isBookmarked: boolean;
  isBookmarkPending: boolean;
};

function formatDate(value: string | undefined): string {
  if (!value) {
    return "-";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleDateString("ko-KR");
}

function formatBooleanLabel(value: boolean | null | undefined) {
  if (value === true) {
    return "가능";
  }

  if (value === false) {
    return "불가능";
  }

  return "-";
}

function formatPriceLabel(value: boolean | null | undefined) {
  if (value === true) {
    return "무료";
  }

  if (value === false) {
    return "유료";
  }

  return "-";
}

function formatScore(score: number | undefined) {
  if (typeof score !== "number" || Number.isNaN(score)) {
    return "-";
  }

  return score.toFixed(1);
}

export function buildSearchResourceCardModel(
  resource: ResultCard,
  options: {
    isBookmarked: boolean;
    isBookmarkPending: boolean;
  },
): ResourceCardViewModel {
  if (resource.type === "dataset") {
    return {
      type: "dataset",
      title: resource.name,
      topMeta: [
        `출처: ${resource.source || "제공처 미상"}`,
        `업데이트: ${formatDate(resource.lastUpdate)}`,
      ],
      detailItems: [
        {
          label: "도메인",
          value:
            resource.domains && resource.domains.length > 0
              ? resource.domains.join(", ")
              : "-",
        },
        {
          label: "공개 상태",
          value: resource.reliability || "-",
        },
        {
          label: "상용 사용",
          value: formatBooleanLabel(resource.commercialUseAllowed),
        },
        {
          label: "비용",
          value: formatPriceLabel(resource.isFree),
        },
      ],
      tags: resource.tags ?? [],
      isBookmarked: options.isBookmarked,
      isBookmarkPending: options.isBookmarkPending,
    };
  }

  return {
    type: "api",
    title: resource.name,
    topMeta: [
      `카테고리: ${resource.category || "-"}`,
      `제공: ${resource.provider || resource.source || "정보 없음"}`,
    ],
    detailItems: [
      {
        label: "인증 방식",
        value: resource.auth || "API Key",
      },
      {
        label: "응답 형식",
        value: resource.responseFormat || "JSON",
      },
      {
        label: "상용 사용",
        value: formatBooleanLabel(resource.commercialUse),
      },
      {
        label: "비용",
        value: formatPriceLabel(resource.isFree),
      },
    ],
    tags: resource.tags ?? [],
    isBookmarked: options.isBookmarked,
    isBookmarkPending: options.isBookmarkPending,
  };
}
