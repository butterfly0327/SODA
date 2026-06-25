import { apiClient } from "./client";
import type { ApiResponse } from "./contracts";
import type {
	CommunityPostDetail,
	CommunityPostListPage,
	CommunityPostListSort,
	CreateCommunityPostRequest,
	CreateCommunityPostResponse,
	UpdateCommunityPostRequest,
	UpdateCommunityPostResponse,
} from "./types";

export const postApi = {
	createPost: async (
		payload: CreateCommunityPostRequest,
	): Promise<CreateCommunityPostResponse> => {
		const response = await apiClient.post<
			ApiResponse<CreateCommunityPostResponse>
		>(
			"/posts",
			payload,
		);
		return response.data.data;
	},

	getPostList: async (
		page = 0,
		size = 10,
		sort: CommunityPostListSort = "LATEST",
		keyword?: string,
	): Promise<CommunityPostListPage> => {
		const response = await apiClient.get<ApiResponse<CommunityPostListPage>>(
			"/posts",
			{
				params: { page, size, sort, keyword },
			},
		);
		return response.data.data;
	},

	getPostDetail: async (
		postId: number,
		increaseViewCount = true,
	): Promise<CommunityPostDetail> => {
		const response = await apiClient.get<ApiResponse<CommunityPostDetail>>(
			`/posts/${postId}`,
			{
				params: { increaseViewCount },
			},
		);
		return response.data.data;
	},

	updatePost: async (
		postId: number,
		payload: UpdateCommunityPostRequest,
	): Promise<UpdateCommunityPostResponse> => {
		const response = await apiClient.patch<ApiResponse<UpdateCommunityPostResponse>>(`/posts/${postId}`, payload);
		return response.data.data;
	},

	deletePost: async (postId: number): Promise<void> => {
		await apiClient.delete<ApiResponse<null>>(`/posts/${postId}`);
	},
};
