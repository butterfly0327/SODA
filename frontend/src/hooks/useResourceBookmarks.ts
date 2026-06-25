import axios from "axios";
import { useCallback, useState } from "react";

import {
  normalizeBookmarkResourceType,
  resolveBookmarkIdForResource,
  toggleResourceBookmark,
} from "@/app/lib/resourceBookmarkApi";
import {
  buildResourceBookmarkKey,
  useResourceBookmarkStore,
} from "@/stores/resourceBookmarkStore";
import { useAuthStore } from "@/stores/authStore";

type BookmarkableResource = {
  id?: number;
  type: "dataset" | "api" | "DATASET" | "OPEN_API";
  name?: string;
  title?: string;
  isBookmarked?: boolean;
  bookmarkId?: number | null;
};

function toTarget(resource: BookmarkableResource) {
  if (typeof resource.id !== "number" || !Number.isFinite(resource.id)) {
    return null;
  }

  const resourceType = normalizeBookmarkResourceType(resource.type);
  const title = resource.name ?? resource.title;

  return {
    resourceId: resource.id,
    resourceType,
    title,
  };
}

export function useResourceBookmarks() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const entries = useResourceBookmarkStore((state) => state.entries);
  const primeBookmarkState = useResourceBookmarkStore((state) => state.primeBookmarkState);
  const setBookmarkState = useResourceBookmarkStore((state) => state.setBookmarkState);
  const seedBookmarks = useResourceBookmarkStore((state) => state.seedBookmarks);
  const clearBookmarkState = useResourceBookmarkStore((state) => state.clearBookmarkState);

  const [bookmarkError, setBookmarkError] = useState<string | null>(null);
  const [pendingBookmarkKey, setPendingBookmarkKey] = useState<string | null>(null);

  const primeResourceBookmark = useCallback(
    (resource: BookmarkableResource) => {
      const target = toTarget(resource);
      if (!target) {
        return;
      }

      primeBookmarkState({
        resourceId: target.resourceId,
        resourceType: target.resourceType,
        isBookmarked: resource.isBookmarked ?? false,
        bookmarkId: resource.bookmarkId ?? null,
      });
    },
    [primeBookmarkState],
  );

  const isBookmarked = useCallback(
    (resource: BookmarkableResource) => {
      const target = toTarget(resource);
      if (!target) {
        return false;
      }

      const entry = entries[buildResourceBookmarkKey(target.resourceType, target.resourceId)];
      return entry?.isBookmarked ?? Boolean(resource.isBookmarked);
    },
    [entries],
  );

  const isBookmarkPending = useCallback(
    (resource: BookmarkableResource) => {
      const target = toTarget(resource);
      if (!target) {
        return false;
      }

      return (
        pendingBookmarkKey ===
        buildResourceBookmarkKey(target.resourceType, target.resourceId)
      );
    },
    [pendingBookmarkKey],
  );

  const markBookmarkRemoved = useCallback(
    (resource: BookmarkableResource) => {
      const target = toTarget(resource);
      if (!target) {
        return;
      }

      clearBookmarkState(target.resourceType, target.resourceId);
    },
    [clearBookmarkState],
  );

  const toggleBookmark = useCallback(
    async (resource: BookmarkableResource) => {
      if (!isAuthenticated) {
        setBookmarkError("로그인이 필요합니다. 다시 로그인해주세요.");
        return null;
      }

      const target = toTarget(resource);
      if (!target) {
        setBookmarkError("북마크 대상 리소스 정보를 확인할 수 없습니다.");
        return null;
      }

      const key = buildResourceBookmarkKey(target.resourceType, target.resourceId);
      const entry = entries[key];
      const effectiveTarget = {
        ...target,
        bookmarkId: entry?.bookmarkId ?? resource.bookmarkId ?? null,
        isBookmarked: entry?.isBookmarked ?? Boolean(resource.isBookmarked),
      };

      setBookmarkError(null);
      setPendingBookmarkKey(key);

      try {
        const result = await toggleResourceBookmark(effectiveTarget);
        setBookmarkState({
          resourceId: target.resourceId,
          resourceType: target.resourceType,
          isBookmarked: result.isBookmarked,
          bookmarkId: result.bookmarkId,
        });
        return result;
      } catch (error) {
        if (axios.isAxiosError<{ message?: string }>(error)) {
          const status = error.response?.status;
          const message = error.response?.data?.message;

          if (status === 409) {
            const bookmarkId = await resolveBookmarkIdForResource(effectiveTarget);
            setBookmarkState({
              resourceId: target.resourceId,
              resourceType: target.resourceType,
              isBookmarked: true,
              bookmarkId,
            });
            return {
              isBookmarked: true,
              bookmarkId,
            };
          }

          if (status === 404 && effectiveTarget.isBookmarked) {
            clearBookmarkState(target.resourceType, target.resourceId);
            return {
              isBookmarked: false,
              bookmarkId: null,
            };
          }

          if (status === 400) {
            setBookmarkError(message || "북마크 요청 값이 올바르지 않습니다.");
          } else if (status === 401) {
            setBookmarkError(message || "로그인이 만료되었습니다. 다시 로그인해주세요.");
          } else if (status === 403) {
            setBookmarkError(message || "북마크 권한이 없습니다.");
          } else if (status === 404) {
            setBookmarkError(message || "존재하지 않는 리소스입니다.");
          } else {
            setBookmarkError(message || "북마크 처리에 실패했습니다.");
          }
          return null;
        }

        setBookmarkError("북마크 처리에 실패했습니다.");
        return null;
      } finally {
        setPendingBookmarkKey(null);
      }
    },
    [
      clearBookmarkState,
      entries,
      isAuthenticated,
      setBookmarkState,
    ],
  );

  return {
    bookmarkError,
    clearBookmarkError: () => setBookmarkError(null),
    isBookmarked,
    isBookmarkPending,
    primeResourceBookmark,
    seedBookmarks,
    markBookmarkRemoved,
    toggleBookmark,
  };
}
