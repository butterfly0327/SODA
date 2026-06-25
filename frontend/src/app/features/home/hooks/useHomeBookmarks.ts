import { useCallback, useEffect, useMemo, useState } from "react";

import { bookmarkApi } from "@/api/bookmarkApi";
import { userApi } from "@/api/userApi";
import { getApiErrorInfo, getApiErrorMessage } from "@/app/shared/lib/apiError";
import type { Project } from "@/stores/chatStore";
import type { ResultCard } from "@/types/recommendation";

type UseHomeBookmarksOptions = {
  isAuthenticated: boolean;
  projects: Project[];
  currentProjectId: string | null;
  currentConversationProjectId: string | null;
  addProject: (project: Project) => void;
  setCurrentProject: (id: string | null) => void;
  toggleProjectSavedResource: (
    projectId: string,
    item: { name: string; type: "dataset" | "api" },
  ) => void;
};

function buildBookmarkKey(result: Pick<ResultCard, "type" | "id">) {
  return `${result.type}:${String(result.id)}`;
}

export function useHomeBookmarks({
  isAuthenticated,
  projects,
  currentProjectId,
  currentConversationProjectId,
  addProject,
  setCurrentProject,
  toggleProjectSavedResource,
}: UseHomeBookmarksOptions) {
  const [bookmarkError, setBookmarkError] = useState<string | null>(null);
  const [remoteBookmarks, setRemoteBookmarks] = useState<Record<string, number>>({});

  useEffect(() => {
    if (!isAuthenticated) {
      setRemoteBookmarks({});
      return;
    }

    let cancelled = false;

    const loadBookmarks = async () => {
      try {
        const page = await userApi.getMyBookmarks(0, 200);
        if (cancelled) {
          return;
        }

        const nextLookup = page.content.reduce<Record<string, number>>((acc, item) => {
          const type = item.type === "DATASET" ? "dataset" : "api";
          acc[`${type}:${item.id}`] = item.bookmarkId;
          return acc;
        }, {});
        setRemoteBookmarks(nextLookup);
      } catch {
        if (!cancelled) {
          setRemoteBookmarks({});
        }
      }
    };

    void loadBookmarks();

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  const getTargetProjectId = useCallback(
    () => currentConversationProjectId ?? currentProjectId,
    [currentConversationProjectId, currentProjectId],
  );

  const ensureBookmarkProjectId = useCallback(() => {
    const existingTargetProjectId = getTargetProjectId();
    if (existingTargetProjectId) {
      return existingTargetProjectId;
    }

    const bookmarkProject = projects.find((project) => project.name === "북마크");
    if (bookmarkProject) {
      return bookmarkProject.id;
    }

    const bookmarkProjectId = `proj-bookmark-${Date.now()}`;
    addProject({
      id: bookmarkProjectId,
      name: "북마크",
      createdAt: Date.now(),
      recentSearches: [],
      savedResources: [],
      comparisons: [],
    });
    setCurrentProject(null);
    return bookmarkProjectId;
  }, [addProject, getTargetProjectId, projects, setCurrentProject]);

  const isSavedInProject = useCallback(
    (result: ResultCard, projectId: string | null) => {
      if (!projectId) {
        return false;
      }

      const project = projects.find((proj) => proj.id === projectId);
      const savedResources = project?.savedResources ?? [];
      return savedResources.some(
        (resource) => resource.name === result.name && resource.type === result.type,
      );
    },
    [projects],
  );

  const isBookmarked = useCallback(
    (result: ResultCard) => {
      const targetProjectId =
        getTargetProjectId() ?? projects.find((project) => project.name === "북마크")?.id ?? null;
      return Boolean(remoteBookmarks[buildBookmarkKey(result)]) || isSavedInProject(result, targetProjectId);
    },
    [getTargetProjectId, isSavedInProject, projects, remoteBookmarks],
  );

  const handleToggleBookmark = useCallback(
    async (result: ResultCard) => {
      if (!isAuthenticated) {
        setBookmarkError("로그인이 필요합니다. 다시 로그인해주세요.");
        return;
      }

      const targetProjectId = getTargetProjectId();
      const bookmarkProjectId = ensureBookmarkProjectId();
      const projectTargetId = targetProjectId ?? bookmarkProjectId;

      setBookmarkError(null);

      const parsedResourceId = Number(result.id);
      if (!Number.isFinite(parsedResourceId)) {
        setBookmarkError("북마크 대상 리소스 정보를 확인할 수 없습니다.");
        return;
      }

      const bookmarkKey = buildBookmarkKey(result);
      const remoteBookmarkId = remoteBookmarks[bookmarkKey];
      const locallySaved = isSavedInProject(result, projectTargetId);

      if (remoteBookmarkId) {
        try {
          await bookmarkApi.deleteBookmark(remoteBookmarkId);
          setRemoteBookmarks((prev) => {
            const next = { ...prev };
            delete next[bookmarkKey];
            return next;
          });

          if (locallySaved) {
            toggleProjectSavedResource(projectTargetId, {
              name: result.name,
              type: result.type,
            });
          }
          return;
        } catch (error) {
          setBookmarkError(getApiErrorMessage(error, "북마크 해제에 실패했습니다."));
          return;
        }
      }

      try {
        const createdBookmark = await bookmarkApi.createBookmark({
          resourceType: result.type === "dataset" ? "DATASET" : "OPEN_API",
          resourceId: parsedResourceId,
        });
        setRemoteBookmarks((prev) => ({
          ...prev,
          [bookmarkKey]: createdBookmark.bookmarkId,
        }));
      } catch (error) {
        const { status, message } = getApiErrorInfo(error);

        if (status === 409) {
          try {
            const page = await userApi.getMyBookmarks(0, 200);
            const nextLookup = page.content.reduce<Record<string, number>>((acc, item) => {
              const type = item.type === "DATASET" ? "dataset" : "api";
              acc[`${type}:${item.id}`] = item.bookmarkId;
              return acc;
            }, {});
            setRemoteBookmarks(nextLookup);
          } catch {
            setBookmarkError(message || "이미 북마크된 리소스입니다.");
          }
          return;
        }

        if (status === 400) {
          setBookmarkError(message || "북마크 요청 값이 올바르지 않습니다.");
          return;
        }

        if (status === 404) {
          setBookmarkError(message || "존재하지 않는 리소스입니다.");
          return;
        }

        if (status === 401) {
          setBookmarkError(message || "로그인이 만료되었습니다. 다시 로그인해주세요.");
          return;
        }

        setBookmarkError(message || "북마크 등록에 실패했습니다.");
        return;
      }

      if (!locallySaved) {
        toggleProjectSavedResource(projectTargetId, {
          name: result.name,
          type: result.type,
        });
      }
    },
    [
      ensureBookmarkProjectId,
      getTargetProjectId,
      isAuthenticated,
      isSavedInProject,
      remoteBookmarks,
      toggleProjectSavedResource,
    ],
  );

  const canBookmark = isAuthenticated;
  const canCompare = useMemo(() => Boolean(getTargetProjectId()), [getTargetProjectId]);

  return {
    bookmarkError,
    canBookmark,
    canCompare,
    isBookmarked,
    handleToggleBookmark,
  };
}
