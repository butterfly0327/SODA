package ssafy.E105.domain.user.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import ssafy.E105.domain.user.dto.response.MyBookmarkResponse;
import ssafy.E105.domain.user.dto.response.MyPostResponse;
import ssafy.E105.domain.user.dto.response.MyReviewResponse;
import ssafy.E105.domain.user.dto.response.PageResponse;
import ssafy.E105.domain.user.dto.response.UserProfileResponse;
import ssafy.E105.domain.user.service.UserService;
import ssafy.E105.global.common.response.ApiResponse;

@RestController
@RequiredArgsConstructor
@RequestMapping("/v1/users")
public class UserController {

    private final UserService userService;

    @GetMapping("/me")
    public ResponseEntity<ApiResponse<UserProfileResponse>> getMyProfile(
            @AuthenticationPrincipal Long userId) {
        return userService.getMyProfile(userId);
    }

    @GetMapping("/me/posts")
    public ResponseEntity<ApiResponse<PageResponse<MyPostResponse>>> getMyPosts(
            @AuthenticationPrincipal Long userId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        return userService.getMyPosts(userId, page, size);
    }

    @GetMapping("/me/reviews")
    public ResponseEntity<ApiResponse<PageResponse<MyReviewResponse>>> getMyReviews(
            @AuthenticationPrincipal Long userId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        return userService.getMyReviews(userId, page, size);
    }

    @GetMapping("/me/bookmarks")
    public ResponseEntity<ApiResponse<PageResponse<MyBookmarkResponse>>> getMyBookmarks(
            @AuthenticationPrincipal Long userId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String type,
            @RequestParam(required = false) Boolean freeOnly) {
        return userService.getMyBookmarks(userId, page, size, keyword, type, freeOnly);
    }

    @DeleteMapping("/me")
    public ResponseEntity<ApiResponse<Void>> withdraw(
            @AuthenticationPrincipal Long userId) {
        userService.withdraw(userId);
        return ResponseEntity.ok(ApiResponse.success("회원 탈퇴가 완료되었습니다.", null));
    }
}
