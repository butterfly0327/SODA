package ssafy.E105.domain.user.dto.response;

public record CallbackResponse(
        String accessToken,
        String refreshToken
) {
}
