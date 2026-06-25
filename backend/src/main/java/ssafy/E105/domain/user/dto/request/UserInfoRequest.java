package ssafy.E105.domain.user.dto.request;

public record UserInfoRequest(
        String userId,
        String name,
        String email,
        String edu,
        String entRegnCd,
        String retireYn,
        String clss
) {}