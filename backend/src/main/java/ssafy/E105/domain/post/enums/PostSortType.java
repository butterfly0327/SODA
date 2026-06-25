package ssafy.E105.domain.post.enums;

import org.springframework.data.domain.Sort;

public enum PostSortType {
    LATEST,
    VIEW_COUNT,
    FAVORITE;

    public Sort toSort() {
        return switch (this) {
            case LATEST -> Sort.by(Sort.Direction.DESC, "createdAt");
            case VIEW_COUNT -> Sort.by(Sort.Direction.DESC, "viewCount").and(Sort.by(Sort.Direction.DESC, "createdAt"));
            case FAVORITE -> Sort.by(Sort.Direction.DESC, "favorite").and(Sort.by(Sort.Direction.DESC, "createdAt"));
        };
    }
}
