package ssafy.E105.domain.user.dto.response;

public record TokenResponse(
        String accessToken,
        String refreshToken
) {}