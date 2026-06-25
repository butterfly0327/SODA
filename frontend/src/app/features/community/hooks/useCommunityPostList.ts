import { useEffect, useMemo, useState } from "react";

import { postApi } from "@/api/postApi";
import type { CommunityPostListPage, CommunityPostListSort } from "@/api/types";
import { useCommunityStore } from "@/stores/communityStore";
import { getHoursAgoFromCreatedAt } from "@/app/utils/communityDate";

export function useCommunityPostList() {
  const posts = useCommunityStore((state) => state.posts);
  const [postsPage, setPostsPage] = useState<CommunityPostListPage | null>(null);
  const [isLoadingPosts, setIsLoadingPosts] = useState(false);
  const [postListError, setPostListError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [size] = useState(10);
  const [sort, setSort] = useState<CommunityPostListSort>("LATEST");
  const [searchInput, setSearchInput] = useState("");
  const [searchKeyword, setSearchKeyword] = useState("");

  useEffect(() => {
    let cancelled = false;

    const fetchPostList = async () => {
      setIsLoadingPosts(true);
      setPostListError(null);
      try {
        const data = await postApi.getPostList(page, size, sort, searchKeyword || undefined);
        if (!cancelled) {
          setPostsPage(data);
        }
      } catch {
        if (!cancelled) {
          setPostListError("게시글 목록을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.");
          setPostsPage(null);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingPosts(false);
        }
      }
    };

    void fetchPostList();

    return () => {
      cancelled = true;
    };
  }, [page, searchKeyword, size, sort]);

  const fallbackVisiblePosts = useMemo(
    () =>
      [...posts].sort(
        (a, b) => getHoursAgoFromCreatedAt(a.createdAt) - getHoursAgoFromCreatedAt(b.createdAt),
      ),
    [posts],
  );

  const visiblePostsRaw = useMemo(
    () =>
      postsPage
        ? postsPage.content.map((post) => ({
            id: String(post.postId),
            title: post.title,
            content: "",
            author: post.name || "작성자 정보 없음",
            views: post.viewCount,
            likes: post.favorite,
            createdAt: post.createdAt,
          }))
        : fallbackVisiblePosts,
    [fallbackVisiblePosts, postsPage],
  );

  const visiblePosts = useMemo(
    () =>
      visiblePostsRaw.filter((post, index, allPosts) => {
        return allPosts.findIndex((candidate) => candidate.id === post.id) === index;
      }),
    [visiblePostsRaw],
  );

  const totalPages = postsPage?.totalPages ?? 1;
  const currentPage = postsPage?.page ?? page;
  const sortLabel =
    sort === "LATEST" ? "최신순" : sort === "VIEW_COUNT" ? "조회순" : "최신순";

  const submitSearch = () => {
    setPage(0);
    setSearchKeyword(searchInput.trim());
  };

  return {
    postsPage,
    isLoadingPosts,
    postListError,
    page,
    setPage,
    sort,
    setSort,
    sortLabel,
    searchInput,
    setSearchInput,
    totalPages,
    currentPage,
    visiblePosts,
    submitSearch,
  };
}
