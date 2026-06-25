import {
	ArrowLeft,
	Code,
	Database,
	Eye,
} from "lucide-react";
import { useMemo } from "react";
import { useNavigate, useParams } from "react-router";
import { apiClient } from "@/api/client";
import { Button } from "@/components/ui/button";
import type { ResultCard } from "../../types/recommendation";
import { useAuthStore } from "../../stores/authStore";
import {
	buildResourceDetailPath,
	mergeResourceDetail,
} from "../lib/resourceSearchApi";
import { beginSsafyLoginFlow } from "../lib/ssafyLoginFlow";
import { Layout } from "../components/Layout";
import { RecommendationDetailPanel } from "@/app/features/recommendation-detail/components/RecommendationDetailPanel";
import { useResizableDetailPanel } from "@/app/shared/hooks/useResizableDetailPanel";
import { useCommunityDetail } from "@/app/features/community/hooks/useCommunityDetail";
import { EmptyState } from "../components/StateView";

export function CommunityDetailPage() {
	const navigate = useNavigate();
	const { id } = useParams<{ id: string }>();
	const {
		selectedDetail,
		setSelectedDetail,
		panelWidth,
		isResizing,
		startResizing,
		isNarrowViewport,
		closeDetail,
	} = useResizableDetailPanel<ResultCard>();
	const user = useAuthStore((state) => state.user);
	const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
	const logout = useAuthStore((state) => state.logout);

	const postId = useMemo(() => {
		if (!id) return null;
		const parsed = Number(id);
		return Number.isFinite(parsed) ? parsed : null;
	}, [id]);

	const {
		postDetail,
		isLoadingDetail,
		isNotFound,
		detailError,
		isAuthor,
		createdAtLabel,
		showDeleteModal,
		isDeletingPost,
		handleOpenDeleteModal,
		handleCloseDeleteModal,
		handleDeletePost,
	} = useCommunityDetail({
		postId,
		authStoreUserId: user?.id,
		isAuthenticated,
		logout,
		onNavigateCommunity: (state) =>
			navigate("/community", {
				replace: true,
				state,
			}),
		onRequestLogin: (returnTo) => beginSsafyLoginFlow(returnTo),
	});

	if (isLoadingDetail) {
		return (
			<Layout>
				<main className="flex-1 overflow-y-auto">
					<div className="max-w-4xl mx-auto px-6 py-10" />
				</main>
			</Layout>
		);
	}

	if (isNotFound || !postDetail) {
		return (
			<Layout>
				<main className="flex-1 overflow-y-auto">
					<div className="max-w-4xl mx-auto px-6 py-10">
						<EmptyState
							title="게시글을 찾을 수 없습니다."
							description="목록으로 돌아가 다시 선택해 주세요."
						/>
						<div className="mt-6 flex justify-center">
							<Button onClick={() => navigate("/community")} className="h-10 px-8 rounded-none">
								목록
							</Button>
						</div>
					</div>
				</main>
			</Layout>
		);
	}

	const datasetAttachments = postDetail.datasetReferences ?? [];
	const openApiAttachments = postDetail.openApiReferences ?? [];

	const handleOpenReferenceDetail = async (
		type: "dataset" | "api",
		id: number,
		name: string,
	) => {
		const baseDetail: ResultCard =
			type === "dataset"
				? {
					id,
					type: "dataset",
					name,
					score: 0,
					source: "Unknown",
					taskMatch: 0,
					classCount: 0,
					sampleCount: "N/A",
					missingRate: 0,
					reliability: "Medium",
					lastUpdate: "",
					isFree: false,
				}
				: {
					id,
					type: "api",
					name,
					score: 0,
					category: "General",
					responseTime: "N/A",
					auth: "Unknown",
					freeQuota: "N/A",
					availability: "N/A",
					isFree: false,
				};

		setSelectedDetail(baseDetail);

		try {
			const endpoint = buildResourceDetailPath(baseDetail);
			const response = await apiClient.get(endpoint);
			if (response.data?.data) {
				setSelectedDetail((previous) => {
					if (!previous || previous.id !== id || previous.type !== type) {
						return previous;
					}
					return mergeResourceDetail(previous, response.data.data);
				});
			}
		} catch {
			// 상세 패널은 기본 정보로도 열려 있어야 하므로 실패 시 무시
		}
	};

	return (
		<Layout>
			<main className="relative flex flex-1 min-h-0 overflow-hidden">
				<div className="flex-1 min-w-0 overflow-y-auto">
					<div className="max-w-4xl mx-auto px-6 py-8">
					<Button
						type="button"
						variant="ghost"
						onClick={() => navigate("/community")}
						className="mb-4 h-auto rounded-lg px-2 py-2 text-muted-foreground hover:bg-sidebar-accent/50 hover:text-muted-foreground"
					>
						<ArrowLeft className="w-4 h-4 mr-2" />
						커뮤니티로 돌아가기
					</Button>

					{detailError && (
						<div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
							{detailError}
						</div>
					)}

					<div className="border-t border-border border-t-black">
						<section className="px-5 py-5 border-b border-border">
							<div className="flex items-start justify-between gap-4">
								<div className="min-w-0">
									<h1 className="truncate text-2xl leading-tight font-semibold text-foreground md:text-3xl">
										{postDetail.title}
									</h1>
									<div className="mt-3 flex items-center gap-4 text-sm text-muted-foreground">
										<span>{postDetail.name || "작성자 정보 없음"}</span>
										<span>|</span>
										<span>{createdAtLabel}</span>
									</div>
								</div>

								<div className="flex items-center gap-5 pt-10 text-sm text-muted-foreground shrink-0">
									<span className="flex items-center gap-1.5">
										<Eye className="w-5 h-5" />
										{postDetail.viewCount}
									</span>
								</div>
							</div>
						</section>

						<section className="px-6 py-8 border-b border-border">
							<p className="whitespace-pre-line text-base leading-[1.7] text-foreground">
								{postDetail.content}
							</p>
						</section>

						<section className="px-6 py-5 border-b border-border space-y-6">
							<div>
								<div className="mb-2 text-sm font-medium text-foreground">데이터셋 참조</div>
								{datasetAttachments.length === 0 ? (
									<p className="text-sm text-muted-foreground">첨부된 데이터셋이 없습니다.</p>
								) : (
									<div className="space-y-3">
								{datasetAttachments.map((item) => (
									<button
										type="button"
										key={`dataset-${item.id}`}
										onClick={() => handleOpenReferenceDetail("dataset", item.id, item.name)}
										className="w-full cursor-pointer rounded-xl border border-border bg-white p-4 text-left shadow-sm transition-shadow hover:shadow-md"
									>
										<div className="min-w-0 flex items-center gap-3">
											<div className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ds-resource-dataset-icon">
												<Database className="w-5 h-5" />
											</div>
											<h3 className="text-lg font-semibold text-foreground truncate">{item.name}</h3>
										</div>
									</button>
								))}
							</div>
						)}
							</div>

							<div>
								<div className="mb-2 text-sm font-medium text-foreground">Open API 참조</div>
								{openApiAttachments.length === 0 ? (
									<p className="text-sm text-muted-foreground">첨부된 Open API가 없습니다.</p>
								) : (
									<div className="space-y-3">
								{openApiAttachments.map((item) => (
									<button
										type="button"
										key={`open-api-${item.id}`}
										onClick={() => handleOpenReferenceDetail("api", item.id, item.name)}
										className="w-full cursor-pointer rounded-xl border border-border bg-white p-4 text-left shadow-sm transition-shadow hover:shadow-md"
									>
										<div className="min-w-0 flex items-center gap-3">
											<div className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ds-resource-api-icon">
												<Code className="w-5 h-5 text-black" />
											</div>
											<h3 className="text-lg font-semibold text-foreground truncate">{item.name}</h3>
										</div>
									</button>
								))}
							</div>
						)}
							</div>
						</section>
					</div>

					<div className="mt-10 flex justify-center gap-3">
						{isAuthor && (
							<>
							<Button
								onClick={handleOpenDeleteModal}
								className="h-10 cursor-pointer rounded-lg border border-[#4f76df] bg-[#4f76df] px-4 text-sm text-white transition-colors hover:bg-[#4f76df] hover:text-white"
							>
									삭제
								</Button>
							</>
						)}
						<Button onClick={() => navigate("/community")} className="h-10 cursor-pointer rounded-lg border border-[#4f76df] bg-[#4f76df] px-4 text-sm text-white transition-colors hover:bg-[#4f76df] hover:text-white">
							목록
						</Button>
						{isAuthor && (
							<Button
								onClick={() => navigate(`/community/${postDetail.postId}/edit`)}
								className="h-10 cursor-pointer rounded-lg border border-[#4f76df] bg-[#4f76df] px-4 text-sm text-white transition-colors hover:bg-[#4f76df] hover:text-white"
							>
								수정
							</Button>
						)}
					</div>
					</div>
				</div>

				{selectedDetail && !isNarrowViewport && (
					<>
						<button
							type="button"
							className={`w-1 cursor-col-resize transition-colors focus-visible:outline-none ${
								isResizing ? 'bg-[#dfe4ea]' : 'bg-border/60 hover:bg-[#dfe4ea] focus-visible:bg-[#dfe4ea]'
							}`}
							onPointerDown={startResizing}
							aria-label="상세 패널 너비 조절"
						/>
						<div
							style={{ width: `${panelWidth}px` }}
							className="min-w-[320px] max-w-[760px] h-full"
						>
							<RecommendationDetailPanel
								data={selectedDetail}
								onClose={closeDetail}
							/>
						</div>
					</>
				)}

				{showDeleteModal && (
					<div className="absolute inset-0 z-50 flex items-center justify-center px-4">
						<div className="w-full max-w-[320px] rounded-[16px] bg-white px-5 pb-5 pt-6 shadow-[0_14px_30px_rgba(15,23,42,0.16)]">
							<div className="mb-4 flex justify-center">
								<div className="flex h-8 w-8 items-center justify-center rounded-full border border-[#f5c8cf] bg-[#fff5f6]">
									<div className="flex h-5 w-5 items-center justify-center rounded-full border border-[#efb0ba] bg-white">
										<span className="text-[14px] font-bold leading-none text-[#e57373]">!</span>
									</div>
								</div>
							</div>

							<h3 className="text-center text-[18px] font-bold tracking-[-0.01em] text-[#111827]">
								게시글 삭제
							</h3>

							<p className="mt-2.5 text-center text-[13px] leading-relaxed text-[#6b7280]">
								작성하신 게시글을 삭제하시겠습니까?
								<br />
								삭제된 글은 다시 복구할 수 없습니다.
							</p>

							<div className="mt-5 grid grid-cols-2 gap-2.5">
								<Button
									onClick={handleCloseDeleteModal}
									disabled={isDeletingPost}
									className="h-10 rounded-lg border-0 bg-[#eceef1] text-[14px] font-medium text-[#111827] hover:bg-[#e4e7eb]"
								>
									취소
								</Button>
								<Button
									onClick={handleDeletePost}
									disabled={isDeletingPost}
									className="h-10 rounded-lg border-0 bg-[#E57373] text-[14px] font-medium text-white hover:bg-[#db6c6c]"
								>
									삭제하기
								</Button>
							</div>
						</div>
					</div>
				)}
			</main>

			{selectedDetail && isNarrowViewport && (
				<div className="fixed inset-0 z-50">
					<button
						type="button"
						className="absolute inset-0 bg-black/30"
						onClick={closeDetail}
						aria-label="상세 패널 닫기"
					/>
					<div className="absolute inset-y-0 right-0 w-full max-w-[440px] bg-white shadow-2xl">
						<RecommendationDetailPanel
							data={selectedDetail}
							onClose={closeDetail}
						/>
					</div>
				</div>
			)}

		</Layout>
	);
}
