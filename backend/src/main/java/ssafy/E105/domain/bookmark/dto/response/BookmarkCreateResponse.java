package ssafy.E105.domain.bookmark.dto.response;

public record BookmarkCreateResponse(
        Long bookmarkId,
        String resourceType,
        Long resourceId,
        String bookmarkedAt
) {
}
