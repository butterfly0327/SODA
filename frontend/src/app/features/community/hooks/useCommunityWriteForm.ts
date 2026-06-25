import { useEffect, useMemo, useState } from "react";

import { apiClient } from "@/api/client";
import { postApi } from "@/api/postApi";
import type { CommunityPostDetail } from "@/api/types";
import type { CommunityPost } from "@/stores/communityStore";
import { getApiErrorInfo, getApiErrorMessage } from "@/app/shared/lib/apiError";
import {
  getResourceListRequest,
  mapResourceListResponse,
  type SearchResourceCard,
} from "@/app/lib/resourceSearchApi";
import { resolveReferenceSearchPlan } from "@/app/lib/communityReferenceSearch";

export type ReferenceTab = "dataset" | "api";

export type SelectedReference = {
  id: number;
  name: string;
};

type UseCommunityWriteFormOptions = {
  routeId: string | undefined;
  userName: string | null | undefined;
  userId: string | number | null | undefined;
  addPost: (post: Pick<CommunityPost, "title" | "content"> & {
    author?: string;
    authorId?: string;
    avatar?: string;
    postId?: number | string;
    createdAt?: string;
  }) => void;
  logout: () => Promise<void>;
  onNavigateCommunity: (state?: { toastMessage?: string; focusPostId?: string }) => void;
  onNavigatePostDetail: (postId: number) => void;
  onRequestLogin: (returnTo: string) => void;
};

function mapDetailReferences(detail: CommunityPostDetail) {
  const datasetReferences = detail.datasetReferences ?? [];
  const openApiReferences = detail.openApiReferences ?? [];

  return {
    datasetIds: datasetReferences.map((reference) => reference.id),
    openApiIds: openApiReferences.map((reference) => reference.id),
    selectedDatasetRefs: datasetReferences.map((reference) => ({
      id: reference.id,
      name: reference.name,
    })),
    selectedOpenApiRefs: openApiReferences.map((reference) => ({
      id: reference.id,
      name: reference.name,
    })),
  };
}

export function useCommunityWriteForm({
  routeId,
  userName,
  userId,
  addPost,
  logout,
  onNavigateCommunity,
  onNavigatePostDetail,
  onRequestLogin,
}: UseCommunityWriteFormOptions) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [datasetIds, setDatasetIds] = useState<number[]>([]);
  const [openApiIds, setOpenApiIds] = useState<number[]>([]);
  const [selectedDatasetRefs, setSelectedDatasetRefs] = useState<SelectedReference[]>([]);
  const [selectedOpenApiRefs, setSelectedOpenApiRefs] = useState<SelectedReference[]>([]);
  const [referenceTab, setReferenceTab] = useState<ReferenceTab>("dataset");
  const [searchKeyword, setSearchKeyword] = useState("");
  const [resourceResults, setResourceResults] = useState<SearchResourceCard[]>([]);
  const [isSearchingResources, setIsSearchingResources] = useState(false);
  const [resourceSearchError, setResourceSearchError] = useState("");
  const [error, setError] = useState("");
  const [isSubmittingPost, setIsSubmittingPost] = useState(false);
  const [isLoadingPostForEdit, setIsLoadingPostForEdit] = useState(false);

  const editPostId = useMemo(() => {
    if (!routeId) return null;
    const parsed = Number(routeId);
    return Number.isFinite(parsed) ? parsed : null;
  }, [routeId]);

  const isEditMode = editPostId !== null;

  useEffect(() => {
    if (!isEditMode || editPostId === null) {
      return;
    }

    let cancelled = false;

    const fetchPostForEdit = async () => {
      setIsLoadingPostForEdit(true);
      setError("");

      try {
        const detail = await postApi.getPostDetail(editPostId, false);
        if (cancelled) {
          return;
        }

        const mapped = mapDetailReferences(detail);
        setTitle(detail.title ?? "");
        setContent(detail.content ?? "");
        setDatasetIds(mapped.datasetIds);
        setOpenApiIds(mapped.openApiIds);
        setSelectedDatasetRefs(mapped.selectedDatasetRefs);
        setSelectedOpenApiRefs(mapped.selectedOpenApiRefs);
      } catch (requestError) {
        if (cancelled) {
          return;
        }

        const { status, message } = getApiErrorInfo(requestError);

        if (status === 404) {
          setError("수정할 게시글을 찾을 수 없습니다.");
          return;
        }

        setError(message || "게시글 정보를 불러오지 못했습니다.");
      } finally {
        if (!cancelled) {
          setIsLoadingPostForEdit(false);
        }
      }
    };

    void fetchPostForEdit();

    return () => {
      cancelled = true;
    };
  }, [editPostId, isEditMode]);

  const executeResourceSearch = async () => {
    setResourceSearchError("");
    setIsSearchingResources(true);

    try {
      const request = getResourceListRequest();
      const searchPlan = resolveReferenceSearchPlan(referenceTab, searchKeyword);
      const response = await apiClient.get(request.url, {
        params: {
          ...request.params,
          type: searchPlan.resolvedType,
          size: searchPlan.pageSize,
          page: searchPlan.page,
          keyword: searchPlan.keyword,
        },
      });

      const payload = response.data as any;
      const pageItems = mapResourceListResponse(payload);
      setResourceResults(pageItems.filter((item) => item.type === referenceTab));
    } catch (requestError) {
      setResourceSearchError(
        getApiErrorMessage(requestError, "리소스 검색에 실패했습니다. 잠시 후 다시 시도해주세요."),
      );
      setResourceResults([]);
    } finally {
      setIsSearchingResources(false);
    }
  };

  const handleAddReference = (resource: SearchResourceCard) => {
    if (resource.type === "dataset") {
      if (datasetIds.includes(resource.id)) {
        return;
      }

      setDatasetIds((previous) => [...previous, resource.id]);
      setSelectedDatasetRefs((previous) => [...previous, { id: resource.id, name: resource.name }]);
      return;
    }

    if (openApiIds.includes(resource.id)) {
      return;
    }

    setOpenApiIds((previous) => [...previous, resource.id]);
    setSelectedOpenApiRefs((previous) => [...previous, { id: resource.id, name: resource.name }]);
  };

  const handleRemoveReference = (type: ReferenceTab, referenceId: number) => {
    if (type === "dataset") {
      setDatasetIds((previous) => previous.filter((idValue) => idValue !== referenceId));
      setSelectedDatasetRefs((previous) => previous.filter((item) => item.id !== referenceId));
      return;
    }

    setOpenApiIds((previous) => previous.filter((idValue) => idValue !== referenceId));
    setSelectedOpenApiRefs((previous) => previous.filter((item) => item.id !== referenceId));
  };

  const submitPost = async () => {
    if (isSubmittingPost) {
      return;
    }

    setError("");

    if (!title.trim()) {
      setError("제목을 입력해주세요.");
      return;
    }

    if (!content.trim()) {
      setError("내용을 입력해주세요.");
      return;
    }

    setIsSubmittingPost(true);

    try {
      const payload = {
        title: title.trim(),
        content: content.trim(),
        datasetIds,
        openApiIds,
      };

      if (isEditMode && editPostId !== null) {
        const updatedPost = await postApi.updatePost(editPostId, payload);
        onNavigatePostDetail(updatedPost.postId);
        return;
      }

      const createdPost = await postApi.createPost(payload);

      const authorName = userName?.trim() || "나";
      addPost({
        postId: createdPost.postId,
        title: payload.title,
        content: payload.content,
        author: authorName,
        authorId: userId ? String(userId) : undefined,
        avatar: authorName.charAt(0),
        createdAt: createdPost.createdAt,
      });

      onNavigateCommunity({
        toastMessage: "등록 완료",
        focusPostId: String(createdPost.postId),
      });
    } catch (requestError) {
      const { status, message } = getApiErrorInfo(requestError);

      if (status === 400) {
        setError(
          message ||
            (isEditMode
              ? "게시글 수정 요청이 올바르지 않습니다."
              : "게시글 제목은 필수입니다."),
        );
        return;
      }

      if (status === 401) {
        await logout();
        onRequestLogin(isEditMode && routeId ? `/community/${routeId}/edit` : "/community/new");
        return;
      }

      if (status === 403) {
        setError(message || "본인이 작성한 게시글만 수정/삭제할 수 있습니다.");
        return;
      }

      if (status === 404) {
        setError(message || "게시글을 찾을 수 없습니다.");
        return;
      }

      setError(
        message ||
          (isEditMode ? "게시글 수정 중 오류가 발생했습니다." : "게시글 등록 중 오류가 발생했습니다."),
      );
    } finally {
      setIsSubmittingPost(false);
    }
  };

  return {
    title,
    setTitle,
    content,
    setContent,
    datasetIds,
    openApiIds,
    selectedDatasetRefs,
    selectedOpenApiRefs,
    referenceTab,
    setReferenceTab,
    searchKeyword,
    setSearchKeyword,
    resourceResults,
    isSearchingResources,
    resourceSearchError,
    error,
    setError,
    isSubmittingPost,
    isLoadingPostForEdit,
    editPostId,
    isEditMode,
    executeResourceSearch,
    handleAddReference,
    handleRemoveReference,
    submitPost,
  };
}
