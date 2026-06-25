package ssafy.E105.domain.user.dto.request;

public record CallbackRequest(
        String code,
        String redirectUrl
) {}