package ssafy.E105.domain.bookmark.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import ssafy.E105.domain.bookmark.dto.request.BookmarkRequest;
import ssafy.E105.domain.bookmark.dto.response.BookmarkCreateResponse;
import ssafy.E105.domain.bookmark.service.BookmarkService;
import ssafy.E105.global.common.response.ApiResponse;

@RestController
@RequestMapping("/v1/bookmarks")
public class BookmarkController {

    private final BookmarkService bookmarkService;

    public BookmarkController(BookmarkService bookmarkService) {
        this.bookmarkService = bookmarkService;
    }

    @PostMapping
    public ResponseEntity<ApiResponse<BookmarkCreateResponse>> createBookmark(
            @RequestBody BookmarkRequest request,
            @AuthenticationPrincipal Long userId
    ) {
        return bookmarkService.createBookmark(request, userId);
    }

    @DeleteMapping("/{bookmarkId}")
    public ResponseEntity<ApiResponse<Void>> deleteBookmark(
            @PathVariable Long bookmarkId,
            @AuthenticationPrincipal Long userId
    ) {
        return bookmarkService.deleteBookmark(bookmarkId, userId);
    }
}
