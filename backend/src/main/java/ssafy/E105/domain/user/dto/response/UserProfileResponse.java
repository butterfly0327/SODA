package ssafy.E105.domain.user.dto.response;

public record UserProfileResponse(
        Long id,
        String name,
        String email,
        String createdAt,
        long postCount,
        long reviewCount,
        long bookmarkCount
) {
}
