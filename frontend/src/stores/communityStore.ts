import { create } from "zustand";

export interface CommunityPost {
	id: string;
	authorId?: string;
	author: string;
	avatar: string;
	title: string;
	content: string;
	likes: number;
	comments: number;
	views: number;
	createdAt: string;
	isPopular?: boolean;
}

export interface CommunityComment {
	id: string;
	author: string;
	createdAt: string;
	content: string;
}

const normalizeAuthorName = (author: string) => author.trim();

function normalizeCreatedAt(createdAt?: string) {
	if (!createdAt) {
		return "방금 전";
	}

	if (/^\d{4}\.\d{2}\.\d{2}\s\d{2}:\d{2}$/.test(createdAt)) {
		return createdAt;
	}

	const parsedDate = new Date(createdAt);
	if (Number.isNaN(parsedDate.getTime())) {
		return createdAt;
	}

	const year = parsedDate.getFullYear();
	const month = String(parsedDate.getMonth() + 1).padStart(2, "0");
	const day = String(parsedDate.getDate()).padStart(2, "0");
	const hour = String(parsedDate.getHours()).padStart(2, "0");
	const minute = String(parsedDate.getMinutes()).padStart(2, "0");

	return `${year}.${month}.${day} ${hour}:${minute}`;
}

interface CommunityState {
	posts: CommunityPost[];
	commentsByPostId: Record<string, CommunityComment[]>;
	addPost: (
		post: Pick<CommunityPost, "title" | "content"> & {
			author?: string;
			authorId?: string;
			avatar?: string;
			postId?: number | string;
			createdAt?: string;
		},
	) => void;
	addComment: (postId: string, content: string, author?: string) => void;
	updateComment: (
		postId: string,
		commentId: string,
		content: string,
		actorName?: string,
	) => void;
	deleteComment: (
		postId: string,
		commentId: string,
		actorName?: string,
	) => void;
	resetState: () => void;
}

const initialCommunityState = {
	posts: [] as CommunityPost[],
	commentsByPostId: {} as Record<string, CommunityComment[]>,
};

export const useCommunityStore = create<CommunityState>()((set) => ({
			...initialCommunityState,
			addPost: (post) => {
				const newPostId =
					typeof post.postId === "number" || typeof post.postId === "string"
						? String(post.postId)
						: `post-${Date.now()}`;
				const authorName = post.author?.trim() || "나";
				set((state) => ({
					commentsByPostId: {
						...state.commentsByPostId,
						[newPostId]: [],
					},
					posts: [
						{
							id: newPostId,
							authorId: post.authorId,
							author: authorName,
							avatar: post.avatar ?? authorName.charAt(0),
							title: post.title,
							content: post.content,
							likes: 0,
							comments: 0,
							views: 0,
							createdAt: normalizeCreatedAt(post.createdAt),
						},
						...state.posts,
					],
				}));
			},
			addComment: (postId, content, author = "나") =>
				set((state) => {
					const targetPost = state.posts.find((post) => post.id === postId);
					if (!targetPost || !content.trim()) {
						return state;
					}
					const nextComments = [
						...(state.commentsByPostId[postId] ?? []),
						{
							id: `comment-${Date.now()}`,
							author,
							createdAt: "방금 전",
							content: content.trim(),
						},
					];

					return {
						commentsByPostId: {
							...state.commentsByPostId,
							[postId]: nextComments,
						},
						posts: state.posts.map((post) =>
							post.id === postId
								? { ...post, comments: nextComments.length }
								: post,
						),
					};
				}),
			updateComment: (postId, commentId, content, actorName = "나") =>
				set((state) => {
					if (!content.trim()) {
						return state;
					}

					const comments = state.commentsByPostId[postId] ?? [];
					const targetComment = comments.find(
						(comment) => comment.id === commentId,
					);
					if (
						!targetComment ||
						normalizeAuthorName(targetComment.author) !==
							normalizeAuthorName(actorName)
					) {
						return state;
					}

					return {
						commentsByPostId: {
							...state.commentsByPostId,
							[postId]: comments.map((comment) =>
								comment.id === commentId
									? { ...comment, content: content.trim() }
									: comment,
							),
						},
					};
				}),
			deleteComment: (postId, commentId, actorName = "나") =>
				set((state) => {
					const comments = state.commentsByPostId[postId] ?? [];
					const targetComment = comments.find(
						(comment) => comment.id === commentId,
					);
					if (
						!targetComment ||
						normalizeAuthorName(targetComment.author) !==
							normalizeAuthorName(actorName)
					) {
						return state;
					}

					const nextComments = comments.filter(
						(comment) => comment.id !== commentId,
					);
					return {
						commentsByPostId: {
							...state.commentsByPostId,
							[postId]: nextComments,
						},
						posts: state.posts.map((post) =>
							post.id === postId
								? { ...post, comments: nextComments.length }
								: post,
						),
					};
				}),
			resetState: () =>
				set({
					...initialCommunityState,
				}),
		}),
);

export function resetCommunityStore() {
	useCommunityStore.getState().resetState();
}
