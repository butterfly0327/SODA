import {
	CheckCircle2,
	ChevronDown,
	Eye,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useClickOutside } from "../../hooks/useClickOutside";
import { useCommunityPostList } from "@/app/features/community/hooks/useCommunityPostList";
import { Layout } from "../components/Layout";
import { PagePagination } from "../components/PagePagination";
import { EmptyState } from "../components/StateView";
import { formatCreatedAt } from "../utils/communityDate";

export function CommunityPage() {
	const navigate = useNavigate();
	const location = useLocation();
	const {
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
	} = useCommunityPostList();
	const [isSortMenuOpen, setIsSortMenuOpen] = useState(false);
	const [toastMessage, setToastMessage] = useState("");
	const [isToastVisible, setIsToastVisible] = useState(false);
	const [focusedPostId, setFocusedPostId] = useState<string | null>(null);
	const postRefs = useRef<Record<string, HTMLButtonElement | null>>({});
	const [pendingFocusPostId, setPendingFocusPostId] = useState<string | null>(
		null,
	);
	const sortMenuRef = useRef<HTMLDivElement>(null);

	useClickOutside({
		ref: sortMenuRef,
		enabled: isSortMenuOpen,
		onOutsideClick: () => setIsSortMenuOpen(false),
		onEscape: () => setIsSortMenuOpen(false),
	});

	useEffect(() => {
		const state = location.state as {
			toastMessage?: string;
			focusPostId?: string;
		} | null;
		if (!state) {
			return;
		}

		if (state.toastMessage) {
			setToastMessage(state.toastMessage);
			setIsToastVisible(true);
		}

		if (state.focusPostId) {
			setFocusedPostId(state.focusPostId);
			setPendingFocusPostId(state.focusPostId);
		}

		navigate(
			{
				pathname: location.pathname,
				search: location.search,
				hash: location.hash,
			},
			{ replace: true, state: null },
		);
	}, [
		location.state,
		location.pathname,
		location.search,
		location.hash,
		navigate,
	]);

	useEffect(() => {
		if (!toastMessage) {
			return;
		}

		const fadeOutTimer = setTimeout(() => {
			setIsToastVisible(false);
		}, 1800);

		const removeTimer = setTimeout(() => {
			setToastMessage("");
		}, 2000);

		return () => {
			clearTimeout(fadeOutTimer);
			clearTimeout(removeTimer);
		};
	}, [toastMessage]);

	useEffect(() => {
		if (!pendingFocusPostId) {
			return;
		}

		let retries = 0;
		let retryTimer: ReturnType<typeof setTimeout> | null = null;
		let cancelled = false;

		const tryScroll = () => {
			if (cancelled) {
				return;
			}

			const target = postRefs.current[pendingFocusPostId];
			if (target) {
				target.scrollIntoView({ behavior: "smooth", block: "center" });
				setPendingFocusPostId(null);
				return;
			}

			if (retries >= 8) {
				setPendingFocusPostId(null);
				return;
			}

			retries += 1;
			retryTimer = setTimeout(tryScroll, 80);
		};

		tryScroll();

		return () => {
			cancelled = true;
			if (retryTimer) {
				clearTimeout(retryTimer);
			}
		};
	}, [pendingFocusPostId]);

	useEffect(() => {
		if (!focusedPostId) {
			return;
		}

		const clearTimer = setTimeout(() => {
			setFocusedPostId((current) =>
				current === focusedPostId ? null : current,
			);
		}, 2200);

		return () => {
			clearTimeout(clearTimer);
		};
	}, [focusedPostId]);

	const postsWithFavoriteState = visiblePosts;

	return (
		<Layout>
			{toastMessage && (
				<div
					className={`fixed right-6 bottom-6 z-50 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm font-medium text-emerald-700 shadow-lg transition-all duration-200 ${
						isToastVisible
							? "opacity-100 translate-y-0"
							: "opacity-0 translate-y-2"
					}`}
				>
					<CheckCircle2 className="w-4 h-4 text-emerald-600" />
					<span>{toastMessage}</span>
				</div>
			)}
			<main className="flex-1 overflow-y-auto">
				<div className="max-w-4xl mx-auto px-6 py-8">
					{postListError && (
						<div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
							{postListError}
						</div>
					)}
					{/* 헤더 */}
					<div className="mb-6">
						<h1 className="mb-6 text-3xl font-bold text-foreground">커뮤니티</h1>
						<p className="text-muted-foreground">
							SODA 사용자들과 지식과 경험을 공유하세요
						</p>
					</div>

					{/* 정렬 고정(최신순)/글쓰기 */}
					<div className="mb-4 pb-2">
						<div className="flex items-center gap-3">
							<div className="relative" ref={sortMenuRef}>
								<button
									type="button"
									onClick={() => setIsSortMenuOpen((prev) => !prev)}
									aria-haspopup="menu"
									aria-expanded={isSortMenuOpen}
									aria-controls="community-sort-menu"
									className="flex h-10 cursor-pointer items-center gap-2 rounded-lg border border-border bg-white px-4 text-sm font-medium text-foreground shadow-sm transition-colors hover:bg-muted"
								>
									<span>{sortLabel}</span>
									<ChevronDown
										className={`w-4 h-4 transition-transform ${isSortMenuOpen ? "rotate-180" : ""}`}
									/>
								</button>

								{isSortMenuOpen && (
									<div
										id="community-sort-menu"
										role="menu"
										aria-label="게시글 정렬 선택"
										className="absolute left-0 top-full z-50 mt-2 w-36 rounded-xl border border-border bg-white p-1 shadow-sm"
									>
										<div className="space-y-1">
											{([
												{ value: "LATEST", label: "최신순" },
												{ value: "VIEW_COUNT", label: "조회순" },
											] as const).map((option) => (
												<button
													key={option.value}
													type="button"
													role="menuitem"
													onClick={() => {
														setPage(0);
														setSort(option.value);
														setIsSortMenuOpen(false);
													}}
													className={`w-full cursor-pointer rounded-lg px-3 py-2 text-left text-sm transition-colors ${
														sort === option.value
															? "bg-[#dfe4ea] text-foreground hover:bg-[#dfe4ea] hover:text-foreground"
															: "text-muted-foreground hover:bg-muted hover:text-foreground"
													}`}
												>
													{option.label}
												</button>
											))}
										</div>
									</div>
								)}
							</div>
							<div className="ml-auto flex items-center gap-3">
								<Button
									onClick={() => navigate("/community/new")}
									className="h-10 cursor-pointer rounded-lg border border-[#4f76df] bg-[#4f76df] px-4 text-sm text-white transition-colors hover:bg-[#4f76df] hover:text-white"
								>
									글쓰기
								</Button>
							</div>
						</div>
					</div>

					{/* 게시글 목록 */}
					<div className="border-t border-b border-border border-t-black divide-y divide-border">
						{postsWithFavoriteState.length === 0 && !isLoadingPosts ? (
							<EmptyState
								title="게시글이 없습니다."
								description="첫 게시글을 작성해 보세요."
							/>
						) : (
							postsWithFavoriteState.map((post) => (
								<button
									type="button"
									key={post.id}
									ref={(element) => {
										postRefs.current[post.id] = element;
									}}
									onClick={() => navigate(`/community/${post.id}`)}
									className={`w-full text-left px-2 md:px-3 py-6 transition-colors cursor-pointer ${
										focusedPostId === post.id ? "bg-brand-soft/10" : ""
									}`}
								>
									<div className="space-y-4">
										<div className="min-w-0">
											<h3 className="text-lg font-semibold text-foreground mb-1 truncate">
												{post.title}
											</h3>
											{post.content ? (
												<p className="text-sm text-muted-foreground line-clamp-2">
													{post.content}
												</p>
											) : null}
										</div>

										<div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
											<div className="flex items-center min-w-0">
												<div className="text-xs md:text-sm text-muted-foreground truncate">
													{post.author} | {formatCreatedAt(post.createdAt)}
												</div>
											</div>

											<div className="flex flex-wrap justify-start md:justify-end items-center gap-4 text-sm text-muted-foreground md:shrink-0">
												<span className="flex items-center gap-1.5">
													<Eye className="w-4 h-4" />
													{post.views}
												</span>
											</div>
										</div>
									</div>
								</button>
							))
						)}
					</div>

					<div className="mt-6 space-y-4">
						<PagePagination
							currentPage={currentPage}
							totalPages={totalPages}
							totalItems={postsPage?.totalElements ?? postsWithFavoriteState.length}
							variant="community"
							onPageChange={setPage}
						/>

						<div className="mx-auto flex w-full max-w-md items-center gap-1.5">
							<Input
								type="text"
								value={searchInput}
								onChange={(event) => setSearchInput(event.target.value)}
								onKeyDown={(event) => {
									if (event.key === "Enter") {
										submitSearch();
									}
								}}
								placeholder="제목, 내용"
								className="h-9 rounded-lg border border-border bg-white px-3 text-xs placeholder:text-muted-foreground focus:outline-none focus-visible:outline-none focus-visible:ring-0 focus-visible:ring-transparent focus-visible:border-border"
							/>
							<Button
								type="button"
								onClick={submitSearch}
								className="h-9 min-w-[84px] cursor-pointer rounded-lg border border-[#4f76df] bg-[#4f76df] px-3.5 text-xs font-semibold text-white hover:bg-[#4f76df]"
							>
								검색
							</Button>
						</div>
					</div>
				</div>
			</main>
		</Layout>
	);
}
