package ssafy.E105.global.common.response;

import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.springframework.http.HttpStatus;

@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ApiResponse<T> {

    private int status;
    private String message;
    private T data;

    private ApiResponse(HttpStatus httpStatus, String message, T data) {
        this.status = httpStatus.value();
        this.message = message;
        this.data = data;
    }

    public static <T> ApiResponse<T> success(String message, T data) {
        return new ApiResponse<>(HttpStatus.OK, message, data);
    }

    public static <T> ApiResponse<T> success(String message) {
        return new ApiResponse<>(HttpStatus.OK, message, null);
    }

    public static <T> ApiResponse<T> created(String message, T data) {
        return new ApiResponse<>(HttpStatus.CREATED, message, data);
    }

    public static <T> ApiResponse<T> accepted(String message, T data) {
        return new ApiResponse<>(HttpStatus.ACCEPTED, message, data);
    }

    public static <T> ApiResponse<T> fail(HttpStatus httpStatus, String message) {
        return new ApiResponse<>(httpStatus, message, null);
    }

    public static <T> ApiResponse<T> fail(HttpStatus httpStatus, String message, T data) {
        return new ApiResponse<>(httpStatus, message, data);
    }
}
