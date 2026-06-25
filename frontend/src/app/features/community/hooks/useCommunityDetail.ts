import { useEffect, useMemo, useState } from "react";

import { postApi } from "@/api/postApi";
import { userApi } from "@/api/userApi";
import type { CommunityPostDetail } from "@/api/types";
import { getApiErrorInfo, isApiErrorStatus } from "@/app/shared/lib/apiError";

type UseCommunityDetailOptions = {
  postId: number | null;
  authStoreUserId: string | number | null | undefined;
  isAuthenticated: boolean;
  logout: () => Promise<void>;
  onNavigateCommunity: (state?: { toastMessage?: string }) => void;
  onRequestLogin: (returnTo: string) => void;
};

function formatIsoToKstLabel(value: string) {
  const parsedDate = new Date(value);
  if (Number.isNaN(parsedDate.getTime())) {
    return value;
  }

  const year = parsedDate.getFullYear();
  const month = String(parsedDate.getMonth() + 1).padStart(2, "0");
  const day = String(parsedDate.getDate()).padStart(2, "0");
  const hour = String(parsedDate.getHours()).padStart(2, "0");
  const minute = String(parsedDate.getMinutes()).padStart(2, "0");

  return `${year}.${month}.${day} ${hour}:${minute}`;
}

export function useCommunityDetail({
  postId,
  authStoreUserId,
  isAuthenticated,
  logout,
  onNavigateCommunity,
  onRequestLogin,
}: UseCommunityDetailOptions) {
  const [postDetail, setPostDetail] = useState<CommunityPostDetail | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(true);
  const [isNotFound, setIsNotFound] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeletingPost, setIsDeletingPost] = useState(false);
  const [currentUserProfileId, setCurrentUserProfileId] = useState<number | null>(null);

  useEffect(() => {
    if (postId === null) {
      setIsLoadingDetail(false);
      setIsNotFound(true);
      return;
    }

    let cancelled = false;

    const fetchDetail = async () => {
      setIsLoadingDetail(true);
      setIsNotFound(false);
      setDetailError(null);

      try {
        const detail = await postApi.getPostDetail(postId, true);
        if (!cancelled) {
          setPostDetail(detail);
        }
      } catch (error) {
        if (cancelled) {
          return;
        }

        if (isApiErrorStatus(error, 404)) {
          setIsNotFound(true);
          setPostDetail(null);
          return;
        }

        setDetailError("게시글 상세 정보를 불러오지 못했습니다.");
        setPostDetail(null);
      } finally {
        if (!cancelled) {
          setIsLoadingDetail(false);
        }
      }
    };

    void fetchDetail();

    return () => {
      cancelled = true;
    };
  }, [postId]);

  useEffect(() => {
    if (!isAuthenticated) {
      setCurrentUserProfileId(null);
      return;
    }

    let cancelled = false;

    const fetchCurrentUserProfile = async () => {
      try {
        const profile = await userApi.getMyProfile();
        if (!cancelled) {
          setCurrentUserProfileId(profile.id);
        }
      } catch {
        if (!cancelled) {
          setCurrentUserProfileId(null);
        }
      }
    };

    void fetchCurrentUserProfile();

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  const parsedAuthStoreUserId = Number(authStoreUserId);
  const currentUserId = Number.isFinite(parsedAuthStoreUserId)
    ? parsedAuthStoreUserId
    : currentUserProfileId;
  const isAuthor =
    postDetail !== null && currentUserId !== null && currentUserId === postDetail.authorId;
  const createdAtLabel = useMemo(() => {
    if (!postDetail) {
      return "";
    }
    const value = formatIsoToKstLabel(postDetail.createdAt);
    return value.endsWith(".") ? value : `${value}.`;
  }, [postDetail]);

  const handleOpenDeleteModal = () => {
    setShowDeleteModal(true);
  };

  const handleCloseDeleteModal = () => {
    setShowDeleteModal(false);
  };

  const handleDeletePost = async () => {
    if (isDeletingPost || postId === null) {
      return;
    }

    setDetailError(null);
    setIsDeletingPost(true);

    try {
      await postApi.deletePost(postId);
      setShowDeleteModal(false);
      onNavigateCommunity({
        toastMessage: "게시글 삭제가 완료되었습니다.",
      });
    } catch (error) {
      const { status, message } = getApiErrorInfo(error);

      if (status === 400) {
        onNavigateCommunity({
          toastMessage: message || "잘못된 요청입니다.",
        });
        return;
      }

      if (status === 401) {
        await logout();
        onRequestLogin(`/community/${postId}`);
        return;
      }

      if (status === 403) {
        setDetailError("작성자 본인만 게시글을 삭제할 수 있습니다.");
        return;
      }

      if (status === 404) {
        onNavigateCommunity({
          toastMessage: message || "게시글을 찾을 수 없습니다.",
        });
        return;
      }

      setDetailError(message || "게시글 삭제 중 오류가 발생했습니다.");
    } finally {
      setIsDeletingPost(false);
    }
  };

  return {
    postDetail,
    isLoadingDetail,
    isNotFound,
    detailError,
    isAuthor,
    createdAtLabel,
    showDeleteModal,
    isDeletingPost,
    setDetailError,
    handleOpenDeleteModal,
    handleCloseDeleteModal,
    handleDeletePost,
  };
}
