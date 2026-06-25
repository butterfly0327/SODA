package ssafy.E105.domain.user.dto.request;

public record SignupRequest(
        String ssafyUid,
        String name,
        String email,
        String edu,
        String region
) {}