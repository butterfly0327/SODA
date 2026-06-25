import { create } from "zustand";

export interface ResourceReview {
	id: string;
	resourceId: number;
	resourceType: "dataset" | "api";
	resourceName: string;
	authorId?: string;
	author: string;
	rating: number;
	content: string;
	createdAt: string;
}

export interface UpsertReviewInput extends Omit<ResourceReview, "id" | "createdAt"> {
	id?: string;
	createdAt?: string;
}

interface ResourceReviewState {
	reviews: ResourceReview[];
	upsertReview: (review: UpsertReviewInput) => void;
	removeReview: (params: { id?: string; resourceId: number; authorId?: string; author?: string }) => void;
	resetState: () => void;
}

const initialResourceReviewState = {
	reviews: [] as ResourceReview[],
};

export const useResourceReviewStore = create<ResourceReviewState>()(
		(set) => ({
			...initialResourceReviewState,
			upsertReview: (review) =>
				set((state) => {
					const existing = state.reviews.find(
						(item) =>
							item.resourceId === review.resourceId &&
							(review.authorId
								? item.authorId === review.authorId
								: item.author === review.author),
					);

					if (existing) {
						return {
							reviews: state.reviews.map((item) =>
								item.id === existing.id
									? {
											...item,
											rating: review.rating,
											content: review.content.trim(),
											resourceName: review.resourceName,
											resourceType: review.resourceType,
											authorId: review.authorId,
											createdAt: review.createdAt ?? item.createdAt,
										}
									: item,
							),
						};
					}

					const now = new Date();
					const createdAt =
						review.createdAt ??
						`${now.getFullYear()}.${String(now.getMonth() + 1).padStart(2, "0")}.${String(now.getDate()).padStart(2, "0")}`;

					return {
						reviews: [
							...state.reviews,
							{
								id: review.id ?? `resource-review-${Date.now()}`,
								resourceId: review.resourceId,
								resourceType: review.resourceType,
								resourceName: review.resourceName,
								author: review.author,
								authorId: review.authorId,
								rating: review.rating,
								content: review.content.trim(),
								createdAt,
							},
						],
					};
				}),
			removeReview: (params) =>
				set((state) => ({
					reviews: state.reviews.filter((review) => {
						if (params.id) {
							return review.id !== params.id;
						}
						if (params.authorId) {
							return !(review.resourceId === params.resourceId && review.authorId === params.authorId);
						}
						if (params.author) {
							return !(review.resourceId === params.resourceId && review.author === params.author);
						}
						return true;
					}),
				})),
			resetState: () =>
				set({
					...initialResourceReviewState,
				}),
		}),
);

export function resetResourceReviewStore() {
	useResourceReviewStore.getState().resetState();
}
