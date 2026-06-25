package ssafy.E105.domain.post.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import ssafy.E105.domain.post.dto.request.CreatePostRequest;
import ssafy.E105.domain.post.dto.request.UpdatePostRequest;
import ssafy.E105.domain.post.dto.response.PostCreateResponse;
import ssafy.E105.domain.post.dto.response.PostDetailResponse;
import ssafy.E105.domain.post.dto.response.PostListResponse;
import ssafy.E105.domain.post.dto.response.PostUpdateResponse;
import ssafy.E105.domain.post.enums.PostSortType;
import ssafy.E105.domain.post.service.PostService;
import ssafy.E105.global.common.response.ApiResponse;

@RestController
@RequiredArgsConstructor
@RequestMapping("/v1/posts")
public class PostController {

    private final PostService postService;

    @PostMapping
    public ResponseEntity<ApiResponse<PostCreateResponse>> createPost(
            @RequestBody CreatePostRequest request,
            @AuthenticationPrincipal Long userId
    ) {
        return postService.createPost(request, userId);
    }

    @GetMapping
    public ResponseEntity<ApiResponse<PostListResponse>> getPostList(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(defaultValue = "LATEST") PostSortType sort,
            @RequestParam(required = false) String keyword
    ) {
        return postService.getPostList(page, size, sort, keyword);
    }

    @GetMapping("/{postId}")
    public ResponseEntity<ApiResponse<PostDetailResponse>> getPostDetail(
            @PathVariable Long postId,
            @RequestParam(defaultValue = "true") boolean increaseViewCount
    ) {
        return postService.getPostDetail(postId, increaseViewCount);
    }

    @PatchMapping("/{postId}")
    public ResponseEntity<ApiResponse<PostUpdateResponse>> updatePost(
            @PathVariable Long postId,
            @RequestBody UpdatePostRequest request,
            @AuthenticationPrincipal Long userId
    ) {
        return postService.updatePost(postId, request, userId);
    }

    @DeleteMapping("/{postId}")
    public ResponseEntity<ApiResponse<Void>> deletePost(
            @PathVariable Long postId,
            @AuthenticationPrincipal Long userId
    ) {
        return postService.deletePost(postId, userId);
    }
}
