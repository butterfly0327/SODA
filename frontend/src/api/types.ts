import type {
  ChatMessageDto,
  CommunityPostDetailResponseDto,
  CommunityPostListPageResponseDto,
  CommunityPostListSortDto,
  ConversationDetailDto,
  ConversationListItemDto,
  CreateBookmarkRequestDto,
  CreateBookmarkResponseDto,
  CreateCommunityPostRequestDto,
  CreateCommunityPostResponseDto,
  UpdateCommunityPostRequestDto,
  UpdateCommunityPostResponseDto,
  LoginRequestDto,
  LoginResponseDto,
  MyBookmarksPageResponseDto,
  MyPostsPageResponseDto,
  MyProfileResponseDto,
  MyReviewsPageResponseDto,
  ResourceDetailDto,
  RecommendationDetailDto,
  SendMessageAcceptedResponseDto,
  SendMessageRequestDto,
  SendMessageResponseDto,
} from './contracts';

export type ChatMessage = Pick<ChatMessageDto, 'role' | 'content'>;
export type SendChatMessageRequest = SendMessageRequestDto;
export type SendChatMessageAcceptedResponse = SendMessageAcceptedResponseDto;
export type SendChatMessageResponse = SendMessageResponseDto;
export type RecommendationDetail = RecommendationDetailDto;
export type ConversationListItem = ConversationListItemDto;
export type ConversationDetail = ConversationDetailDto;
export type ResourceDetail = ResourceDetailDto;
export type MyProfile = MyProfileResponseDto;
export type MyPostsPage = MyPostsPageResponseDto;
export type MyReviewsPage = MyReviewsPageResponseDto;
export type MyBookmarksPage = MyBookmarksPageResponseDto;
export type CreateBookmarkRequest = CreateBookmarkRequestDto;
export type CreateBookmarkResponse = CreateBookmarkResponseDto;
export type CreateCommunityPostRequest = CreateCommunityPostRequestDto;
export type CreateCommunityPostResponse = CreateCommunityPostResponseDto;
export type UpdateCommunityPostRequest = UpdateCommunityPostRequestDto;
export type UpdateCommunityPostResponse = UpdateCommunityPostResponseDto;
export type CommunityPostListPage = CommunityPostListPageResponseDto;
export type CommunityPostListSort = CommunityPostListSortDto;
export type CommunityPostDetail = CommunityPostDetailResponseDto;

export type User = LoginResponseDto['user'] & {
  avatar?: string;
};

export type LoginRequest = LoginRequestDto;

export type LoginResponse = LoginResponseDto & {
  user: User;
};
