package ssafy.E105.global.exception;

import lombok.Getter;
import org.springframework.http.HttpStatus;

@Getter
public enum ErrorCode {

    // 공통 (400)
    INVALID_INPUT(HttpStatus.BAD_REQUEST, "잘못된 요청입니다."),
    INVALID_REDIRECT_URL(HttpStatus.BAD_REQUEST, "유효하지 않은 redirect URL입니다."),

    // 인증 (401)
    INVALID_USER(HttpStatus.UNAUTHORIZED, "유효하지 않은 사용자입니다."),
    INVALID_AUTH_CODE(HttpStatus.UNAUTHORIZED, "유효하지 않은 인가 코드입니다."),
    INVALID_TOKEN(HttpStatus.UNAUTHORIZED, "유효하지 않은 토큰입니다."),
    SUPERAPP_AUTH_FAILED(HttpStatus.UNAUTHORIZED, "인증에 실패했습니다."),
    DELETED_USER(HttpStatus.UNAUTHORIZED, "탈퇴한 회원입니다. 다시 가입해주세요."),
    ACCESS_DENIED(HttpStatus.FORBIDDEN, "접근 권한이 없습니다."),

    // 미가입 (404)
    USER_NOT_FOUND(HttpStatus.NOT_FOUND, "회원가입이 필요합니다."),

    // 중복 (409)
    DUPLICATE_USER(HttpStatus.CONFLICT, "이미 가입된 회원입니다."),

    // SSAFY 회원 아님 (400)
    NOT_SSAFY_MEMBER(HttpStatus.BAD_REQUEST, "SSAFY 회원이 아닙니다."),

    // 사용자 검증 (400)
    INVALID_EDU(HttpStatus.BAD_REQUEST, "유효하지 않은 기수입니다."),
    INVALID_REGION(HttpStatus.BAD_REQUEST, "유효하지 않은 지역입니다."),
    INVALID_RETIREYN(HttpStatus.BAD_REQUEST, "유효하지 않은 회원입니다."),
    INVALID_CHAT_MESSAGE(HttpStatus.BAD_REQUEST, "메시지는 비어 있을 수 없습니다."),
    INVALID_CONVERSATION_ID(HttpStatus.BAD_REQUEST, "유효하지 않은 대화 ID입니다."),

    // 외부 서버 (502)
    SSAFY_SERVER_ERROR(HttpStatus.BAD_GATEWAY, "SSAFY 서버와 통신에 실패했습니다."),
    FASTAPI_SERVER_ERROR(HttpStatus.BAD_GATEWAY, "추천 서버와 통신에 실패했습니다."),

    // SuperApp 추천
    SUPERAPP_RECOMMENDATION_FAILED(HttpStatus.INTERNAL_SERVER_ERROR, "추천 생성 중 오류가 발생했습니다."),
    SUPERAPP_RECOMMENDATION_TIMEOUT(HttpStatus.GATEWAY_TIMEOUT, "추천 생성 시간이 초과되었습니다."),

    // 권한/소유권
    CONVERSATION_NOT_FOUND(HttpStatus.NOT_FOUND, "대화를 찾을 수 없습니다."),
    CONVERSATION_FORBIDDEN(HttpStatus.FORBIDDEN, "해당 대화에 접근할 수 없습니다."),
    RECOMMENDATION_NOT_FOUND(HttpStatus.NOT_FOUND, "추천 작업을 찾을 수 없습니다."),
    RECOMMENDATION_FORBIDDEN(HttpStatus.FORBIDDEN, "해당 추천 작업에 접근할 수 없습니다."),

    // 리소스
    RESOURCE_NOT_FOUND(HttpStatus.NOT_FOUND, "존재하지 않는 리소스입니다."),

    // 리뷰
    DUPLICATE_REVIEW(HttpStatus.CONFLICT, "이미 리뷰를 작성하셨습니다."),
    INVALID_RATING(HttpStatus.BAD_REQUEST, "평점은 1~5 사이여야 합니다."),
    REVIEW_NOT_FOUND(HttpStatus.NOT_FOUND, "리뷰를 찾을 수 없습니다."),
    REVIEW_FORBIDDEN(HttpStatus.FORBIDDEN, "본인의 리뷰만 수정/삭제할 수 있습니다."),

    // 북마크
    DUPLICATE_BOOKMARK(HttpStatus.CONFLICT, "이미 북마크한 리소스입니다."),
    BOOKMARK_NOT_FOUND(HttpStatus.NOT_FOUND, "북마크를 찾을 수 없습니다."),
    BOOKMARK_FORBIDDEN(HttpStatus.FORBIDDEN, "본인이 등록한 북마크만 삭제할 수 있습니다."),

    // 게시글
    POST_NOT_FOUND(HttpStatus.NOT_FOUND, "게시글을 찾을 수 없습니다."),
    POST_FORBIDDEN(HttpStatus.FORBIDDEN, "본인이 작성한 게시글만 수정/삭제할 수 있습니다."),
    INVALID_POST_TITLE(HttpStatus.BAD_REQUEST, "게시글 제목은 필수입니다.");

    private final HttpStatus httpStatus;
    private final String message;

    ErrorCode(HttpStatus httpStatus, String message) {
        this.httpStatus = httpStatus;
        this.message = message;
    }
}
