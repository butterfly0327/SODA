import {
	AlignCenter,
	AlignLeft,
	AlignRight,
	ArrowLeft,
	Bold,
	Image,
	Italic,
	Link2,
	List,
	ListOrdered,
	Quote,
	Strikethrough,
	Underline,
	X,
} from "lucide-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useAuthStore } from "../../stores/authStore";
import { useCommunityStore } from "../../stores/communityStore";
import { useCommunityWriteForm } from "@/app/features/community/hooks/useCommunityWriteForm";
import {
	REFERENCE_SEARCH_PAGE_SIZE,
} from "../lib/communityReferenceSearch";
import { beginSsafyLoginFlow } from "../lib/ssafyLoginFlow";
import { Layout } from "../components/Layout";

export function CommunityWritePage() {
	const navigate = useNavigate();
	const { id } = useParams<{ id: string }>();
	const user = useAuthStore((state) => state.user);
	const logout = useAuthStore((state) => state.logout);
	const addPost = useCommunityStore((state) => state.addPost);
	const {
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
		isSubmittingPost,
		isLoadingPostForEdit,
		editPostId,
		isEditMode,
		executeResourceSearch,
		handleAddReference,
		handleRemoveReference,
		submitPost,
	} = useCommunityWriteForm({
		routeId: id,
		userName: user?.name,
		userId: user?.id,
		addPost,
		logout,
		onNavigateCommunity: (state) => navigate("/community", { state }),
		onNavigatePostDetail: (postId) => navigate(`/community/${postId}`, { replace: true }),
		onRequestLogin: (returnTo) => beginSsafyLoginFlow(returnTo),
	});
	const communityPrimaryButtonClass =
		"h-10 cursor-pointer rounded-lg border border-[#4f76df] bg-[#4f76df] px-4 text-sm text-white transition-colors hover:bg-[#4f76df] hover:text-white";
	const communityCompactPrimaryButtonClass =
		"h-9 cursor-pointer rounded-lg border border-[#4f76df] bg-[#4f76df] px-3 text-xs text-white transition-colors hover:bg-[#4f76df] hover:text-white";
	const activeReferenceFilterClass =
		"border border-[#4f76df] bg-[#4f76df] text-white hover:bg-[#4f76df] hover:text-white";
	const inactiveReferenceFilterClass =
		"border border-border bg-white text-muted-foreground hover:bg-muted hover:text-muted-foreground";

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		await submitPost();
	};

	return (
		<Layout>
			<main className="flex-1 overflow-y-auto">
				<div className="max-w-3xl mx-auto px-6 py-8">
					<Button
						variant="ghost"
						onClick={() =>
							navigate(isEditMode && editPostId !== null ? `/community/${editPostId}` : "/community")
						}
					className="mb-4 h-auto rounded-lg px-2 py-2 text-muted-foreground hover:bg-sidebar-accent/50 hover:text-muted-foreground"
				>
						<ArrowLeft className="w-4 h-4 mr-2" />
						{isEditMode ? "게시글로 돌아가기" : "커뮤니티로 돌아가기"}
					</Button>

					<form onSubmit={handleSubmit} className="space-y-5">
						{error && (
							<div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
								{error}
							</div>
						)}
					<section className="overflow-hidden border-y border-border bg-white">
						<div className="grid border-b border-border md:grid-cols-[180px_minmax(0,1fr)]">
							<div className="flex items-center gap-1 bg-white px-4 py-4 text-sm font-medium text-foreground md:border-r md:border-border">
								<span className="text-red-500">*</span>
								<Label htmlFor="post-title" className="cursor-text">
									제목
								</Label>
							</div>
							<div className="bg-white px-4 py-3 md:px-5">
							<Input
								id="post-title"
								value={title}
								onChange={(e) => setTitle(e.target.value)}
								placeholder="제목을 입력하세요"
								className="h-11 rounded-none border-border bg-white shadow-none focus:outline-none focus-visible:outline-none focus-visible:ring-0 focus-visible:ring-transparent focus-visible:border-border"
							/>
							</div>
						</div>

						<div className="grid border-b border-border md:grid-cols-[180px_minmax(0,1fr)]">
							<div className="flex items-start gap-1 bg-white px-4 py-4 text-sm font-medium text-foreground md:border-r md:border-border">
								<span className="pt-0.5 text-red-500">*</span>
								<Label htmlFor="post-content" className="cursor-text">
									내용
								</Label>
							</div>
							<div className="bg-white px-4 py-3 md:px-5">
								<div className="border border-border bg-white">
									<div className="flex flex-wrap items-center gap-1 border-b border-border bg-muted/20 px-2 py-1.5 text-muted-foreground">
										<button type="button" className="rounded p-1 hover:bg-muted" aria-label="굵게">
											<Bold className="h-4 w-4" />
										</button>
										<button type="button" className="rounded p-1 hover:bg-muted" aria-label="기울임">
											<Italic className="h-4 w-4" />
										</button>
										<button type="button" className="rounded p-1 hover:bg-muted" aria-label="밑줄">
											<Underline className="h-4 w-4" />
										</button>
										<button type="button" className="rounded p-1 hover:bg-muted" aria-label="취소선">
											<Strikethrough className="h-4 w-4" />
										</button>
										<div className="mx-1 h-4 w-px bg-border" />
										<button type="button" className="rounded p-1 hover:bg-muted" aria-label="순서 없는 목록">
											<List className="h-4 w-4" />
										</button>
										<button type="button" className="rounded p-1 hover:bg-muted" aria-label="순서 있는 목록">
											<ListOrdered className="h-4 w-4" />
										</button>
										<button type="button" className="rounded p-1 hover:bg-muted" aria-label="인용">
											<Quote className="h-4 w-4" />
										</button>
										<div className="mx-1 h-4 w-px bg-border" />
										<button type="button" className="rounded p-1 hover:bg-muted" aria-label="좌측 정렬">
											<AlignLeft className="h-4 w-4" />
										</button>
										<button type="button" className="rounded p-1 hover:bg-muted" aria-label="가운데 정렬">
											<AlignCenter className="h-4 w-4" />
										</button>
										<button type="button" className="rounded p-1 hover:bg-muted" aria-label="우측 정렬">
											<AlignRight className="h-4 w-4" />
										</button>
										<div className="mx-1 h-4 w-px bg-border" />
										<button type="button" className="rounded p-1 hover:bg-muted" aria-label="링크">
											<Link2 className="h-4 w-4" />
										</button>
										<button type="button" className="rounded p-1 hover:bg-muted" aria-label="이미지">
											<Image className="h-4 w-4" />
										</button>
									</div>
									<Textarea
										id="post-content"
										value={content}
										onChange={(e) => setContent(e.target.value)}
										placeholder="내용을 입력하세요"
										rows={14}
										className="min-h-[380px] resize-y rounded-none border-0 bg-white shadow-none focus-visible:ring-0"
									/>
								</div>
							</div>
						</div>

						<div className="grid md:grid-cols-[180px_minmax(0,1fr)]">
							<div className="flex items-start bg-white px-4 py-4 text-sm font-medium text-foreground md:border-r md:border-border">
								<Label className="cursor-default">참조 리소스 검색</Label>
							</div>
							<div className="bg-white px-4 py-4 md:px-5">
								<div className="space-y-4 rounded-none border border-border bg-[#f9fafc] p-4">
								<div className="flex flex-wrap items-center justify-end gap-2">
									<Button
										type="button"
										onClick={() => setReferenceTab("dataset")}
										className={`h-9 min-w-[92px] cursor-pointer rounded-xl px-4 text-sm font-medium transition-colors ${
											referenceTab === "dataset" ? activeReferenceFilterClass : inactiveReferenceFilterClass
										}`}
									>
										데이터셋
									</Button>
									<Button
										type="button"
										onClick={() => setReferenceTab("api")}
										className={`h-9 min-w-[92px] cursor-pointer rounded-xl px-4 text-sm font-medium transition-colors ${
											referenceTab === "api" ? activeReferenceFilterClass : inactiveReferenceFilterClass
										}`}
									>
										Open API
									</Button>
								</div>

								<div className="flex items-center gap-2">
									<Input
											value={searchKeyword}
											onChange={(event) => setSearchKeyword(event.target.value)}
											onKeyDown={(event) => {
												if (event.key === "Enter") {
													event.preventDefault();
													void executeResourceSearch();
												}
											}}
											placeholder="키워드를 검색하세요"
											className="h-9 w-full rounded-lg border border-border bg-white px-4 text-foreground shadow-none placeholder:text-muted-foreground focus:outline-none focus-visible:outline-none focus-visible:ring-0 focus-visible:ring-transparent focus-visible:border-border"
										/>
									<Button
										type="button"
										onClick={() => void executeResourceSearch()}
										disabled={isSearchingResources}
										className={`${communityCompactPrimaryButtonClass} disabled:cursor-not-allowed disabled:opacity-70`}
									>
										검색
									</Button>
								</div>

								<p className="text-xs text-muted-foreground">
									참조 리소스 검색은 상위 {REFERENCE_SEARCH_PAGE_SIZE}개 결과만 표시합니다.
								</p>

								{resourceSearchError && (
										<div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
											{resourceSearchError}
										</div>
									)}

									{resourceResults.length > 0 ? (
										<div className="max-h-80 space-y-2 overflow-y-auto rounded-none border border-border bg-background p-2">
											{resourceResults.map((resource) => {
												const isSelected =
													resource.type === "dataset"
														? datasetIds.includes(resource.id)
														: openApiIds.includes(resource.id);

												return (
													<button
														type="button"
														key={`${resource.type}-${resource.id}`}
														onClick={() => handleAddReference(resource)}
														disabled={isSelected}
													className={`flex w-full items-center gap-2 rounded-sm px-3 py-2 text-left text-sm transition-colors ${
														isSelected
															? "cursor-not-allowed bg-muted text-muted-foreground"
															: "bg-card hover:bg-muted"
													}`}
												>
													<span className="min-w-0 flex-1 truncate">{resource.name}</span>
													<span className="min-w-[58px] shrink-0 whitespace-nowrap text-right text-xs text-muted-foreground">
														{resource.type === "dataset" ? "데이터셋" : "Open API"}
													</span>
												</button>
												);
											})}
										</div>
									) : (
										<div className="text-sm text-muted-foreground">검색 결과가 없습니다.</div>
									)}

									<div className="space-y-3">
										<div className="space-y-2">
											<div className="text-sm font-medium text-foreground">선택된 데이터셋</div>
											{selectedDatasetRefs.length > 0 ? (
												<div className="flex flex-wrap gap-2">
													{selectedDatasetRefs.map((reference) => (
														<span
															key={`dataset-ref-${reference.id}`}
															className="inline-flex items-center gap-1 rounded-full border border-border bg-background px-3 py-1 text-xs"
														>
															{reference.name}
															<button
																type="button"
																onClick={() => handleRemoveReference("dataset", reference.id)}
																className="text-muted-foreground hover:text-foreground"
															>
																<X className="h-3.5 w-3.5" />
															</button>
														</span>
													))}
												</div>
											) : (
												<div className="text-sm text-muted-foreground">선택된 데이터셋 없습니다.</div>
											)}
										</div>

										<div className="space-y-2">
											<div className="text-sm font-medium text-foreground">선택된 Open API</div>
											{selectedOpenApiRefs.length > 0 ? (
												<div className="flex flex-wrap gap-2">
													{selectedOpenApiRefs.map((reference) => (
														<span
															key={`open-api-ref-${reference.id}`}
															className="inline-flex items-center gap-1 rounded-full border border-border bg-background px-3 py-1 text-xs"
														>
															{reference.name}
															<button
																type="button"
																onClick={() => handleRemoveReference("api", reference.id)}
																className="text-muted-foreground hover:text-foreground"
															>
																<X className="h-3.5 w-3.5" />
															</button>
														</span>
													))}
												</div>
											) : (
												<div className="text-sm text-muted-foreground">선택된 Open API가 없습니다.</div>
											)}
										</div>
									</div>

								</div>
							</div>
						</div>
					</section>

						<div className="grid pt-2 md:grid-cols-[180px_minmax(0,1fr)]">
							<div />
							<div className="mt-10 flex justify-end gap-3 px-4 md:px-5">
							<Button
								type="button"
								className={communityPrimaryButtonClass}
								onClick={() =>
									navigate(isEditMode && editPostId !== null ? `/community/${editPostId}` : "/community")
								}
								>
									취소
								</Button>
							<Button
								type="submit"
								disabled={!title.trim() || !content.trim() || isSubmittingPost || isLoadingPostForEdit}
								className={`${communityPrimaryButtonClass} disabled:opacity-70 disabled:cursor-not-allowed`}
							>
									{isEditMode ? "게시글 수정" : "게시글 등록"}
								</Button>
							</div>
						</div>
					</form>
				</div>
			</main>
		</Layout>
	);
}
