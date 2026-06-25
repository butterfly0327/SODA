package ssafy.E105.domain.user.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;
import ssafy.E105.domain.user.dto.request.CallbackRequest;
import ssafy.E105.domain.user.dto.response.CallbackResponse;
import ssafy.E105.domain.user.dto.response.ReissueResponse;
import ssafy.E105.domain.user.service.AuthService;
import ssafy.E105.global.common.response.ApiResponse;

@RestController
@RequiredArgsConstructor
@RequestMapping("/v1/auth")
public class AuthController {

    private final AuthService authService;

    @PostMapping("/callback")
    public ResponseEntity<ApiResponse<CallbackResponse>> callback(
            @RequestBody CallbackRequest request) {
        return authService.callback(request);
    }

    @PostMapping("/reissue")
    public ResponseEntity<ApiResponse<ReissueResponse>> reissue(
            @RequestHeader("Authorization") String authorizationHeader) {
        return authService.reissue(authorizationHeader);
    }

    @PostMapping("/logout")
    public ResponseEntity<ApiResponse<Void>> logout() {
        Long userId = (Long) SecurityContextHolder.getContext()
                .getAuthentication()
                .getPrincipal();
        return authService.logout(userId);
    }
}
