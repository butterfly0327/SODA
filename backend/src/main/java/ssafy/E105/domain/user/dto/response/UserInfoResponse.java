package ssafy.E105.domain.user.dto.response;

import ssafy.E105.domain.user.entity.UserEntity;

public record UserInfoResponse(
        String userId,
        String name,
        String role
) {
    public static UserInfoResponse from(UserEntity userEntity) {
        return new UserInfoResponse(
                userEntity.getSsafyId(),
                userEntity.getName(),
                userEntity.getRole().name()
        );
    }
}