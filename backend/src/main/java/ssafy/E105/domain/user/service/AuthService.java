package ssafy.E105.domain.user.service;

import lombok.extern.slf4j.Slf4j;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.HttpStatusCode;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;
import ssafy.E105.domain.user.dto.request.CallbackRequest;
import ssafy.E105.domain.user.dto.response.*;
import ssafy.E105.domain.user.entity.UserEntity;
import ssafy.E105.domain.user.repository.UserRepository;
import ssafy.E105.global.auth.jwt.JwtTokenProvider;
import ssafy.E105.global.common.enums.Role;
import ssafy.E105.global.common.response.ApiResponse;
import ssafy.E105.global.exception.CustomException;
import ssafy.E105.global.exception.ErrorCode;

import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;
import java.util.stream.Stream;

@Service
@RequiredArgsConstructor
@Slf4j
public class AuthService {

    @Value("${ssafy.redirect-urls:${SSAFY_REDIRECT_URLS:${SSAFY_REDIRECT_URL:http://localhost/callback}}}")
    private String allowedRedirectUrl;

    @Value("${ssafy.client-id}")
    private String clientId;

    @Value("${ssafy.client-secret}")
    private String clientSecret;

    @Value("${ssafy.token-url}")
    private String tokenUrl;

    @Value("${ssafy.user-info-url}")
    private String userInfoUrl;

    private final WebClient webClient;
    private final JwtTokenProvider jwtTokenProvider;
    private final RedisTemplate<String, String> redisTemplate;
    private final UserRepository userRepository;

    public ResponseEntity<ApiResponse<CallbackResponse>> callback(CallbackRequest request) {
        String redirectUrl = request.redirectUrl() == null ? "" : request.redirectUrl().trim();

        // 1. redirect URL 검증
        if (!isAllowedRedirectUrl(redirectUrl)) {
            throw new CustomException(ErrorCode.INVALID_REDIRECT_URL);
        }

        // 2. SSAFY 서버에 Access Token 요청
        String ssafyAccessToken = getSsafyAccessToken(request.code(), redirectUrl);

        // 3. SSAFY Access Token으로 사용자 정보 조회
        SsafyUserInfo userInfo = getSsafyUserInfo(ssafyAccessToken);

        // 4. SSAFY 회원 여부 검증
        if (userInfo == null || userInfo.userId() == null || userInfo.userId().isBlank()) {
            throw new CustomException(ErrorCode.NOT_SSAFY_MEMBER);
        }

        // 5. DB에서 회원 조회, 없으면 저장
        UserEntity user = userRepository.findBySsafyId(userInfo.userId())
                .orElseGet(() -> userRepository.save(
                        UserEntity.builder()
                                .ssafyId(userInfo.userId())
                                .name(userInfo.name())
                                .email(userInfo.email())
                                .role(Role.USER)
                                .build()
                ));

        // 5.5 탈퇴한 회원 복구 (재가입)
        if (user.isDeleted()) {
            user.restore();
            user = userRepository.save(user);
            log.info("탈퇴한 회원 복구 - userId: {}, ssafyId: {}", user.getId(), user.getSsafyId());
        }

        // 6. JWT 발급 후 200
        String accessToken = jwtTokenProvider.createAccessToken(user.getId(), user.getRole());
        String refreshToken = jwtTokenProvider.createRefreshToken(user.getId());

        redisTemplate.opsForValue().set(
                String.valueOf(user.getId()),
                refreshToken,
                jwtTokenProvider.getRefreshTokenExpiration(),
                TimeUnit.MILLISECONDS
        );

        return ResponseEntity.ok(
                ApiResponse.success("로그인이 성공하였습니다.",
                        new CallbackResponse(accessToken, refreshToken)));
    }

    private String getSsafyAccessToken(String code, String redirectUrl) {
        try {
            Map response = webClient.post()
                    .uri(tokenUrl)
                    .contentType(MediaType.APPLICATION_FORM_URLENCODED)
                    .bodyValue("grant_type=authorization_code"
                            + "&client_id=" + clientId
                            + "&client_secret=" + clientSecret
                            + "&redirect_uri=" + redirectUrl
                            + "&code=" + code)
                    .retrieve()
                    .onStatus(
                            HttpStatusCode::isError,
                            clientResponse -> clientResponse.bodyToMono(String.class)
                                    .defaultIfEmpty("")
                                    .flatMap(body -> Mono.error(mapTokenError(clientResponse.statusCode(), body)))
                    )
                    .bodyToMono(Map.class)
                    .block();

            return (String) response.get("access_token");
        } catch (CustomException e) {
            throw e;
        } catch (WebClientResponseException e) {
            log.error("SSAFY token API 호출 실패 - status={}, body={}", e.getStatusCode(), sanitizeBody(e.getResponseBodyAsString()));
            throw new CustomException(ErrorCode.SSAFY_SERVER_ERROR);
        } catch (Exception e) {
            log.error("SSAFY token API 처리 중 예외 발생", e);
            throw new CustomException(ErrorCode.SSAFY_SERVER_ERROR);
        }
    }

    private boolean isAllowedRedirectUrl(String redirectUrl) {
        return getAllowedRedirectUrls().contains(redirectUrl);
    }

    private Set<String> getAllowedRedirectUrls() {
        return Stream.of(allowedRedirectUrl.split(","))
                .map(String::trim)
                .filter(value -> !value.isBlank())
                .collect(Collectors.toSet());
    }

    private SsafyUserInfo getSsafyUserInfo(String ssafyAccessToken) {
        try {
            return webClient.get()
                    .uri(userInfoUrl)
                    .header("Authorization", "Bearer " + ssafyAccessToken)
                    .retrieve()
                    .onStatus(
                            HttpStatusCode::isError,
                            clientResponse -> clientResponse.bodyToMono(String.class)
                                    .defaultIfEmpty("")
                                    .flatMap(body -> {
                                        log.error(
                                                "SSAFY user info API 호출 실패 - status={}, body={}",
                                                clientResponse.statusCode(),
                                                sanitizeBody(body)
                                        );
                                        return Mono.error(new CustomException(ErrorCode.SSAFY_SERVER_ERROR));
                                    })
                    )
                    .bodyToMono(SsafyUserInfo.class)
                    .block();
        } catch (CustomException e) {
            throw e;
        } catch (WebClientResponseException e) {
            log.error("SSAFY user info API 호출 실패 - status={}, body={}", e.getStatusCode(), sanitizeBody(e.getResponseBodyAsString()));
            throw new CustomException(ErrorCode.SSAFY_SERVER_ERROR);
        } catch (Exception e) {
            log.error("SSAFY user info API 처리 중 예외 발생", e);
            throw new CustomException(ErrorCode.SSAFY_SERVER_ERROR);
        }
    }

    private CustomException mapTokenError(HttpStatusCode statusCode, String body) {
        String sanitizedBody = sanitizeBody(body);
        log.error("SSAFY token API 호출 실패 - status={}, body={}", statusCode, sanitizedBody);

        if (statusCode.is4xxClientError() && sanitizedBody.contains("invalid_grant")) {
            return new CustomException(ErrorCode.INVALID_AUTH_CODE);
        }

        return new CustomException(ErrorCode.SSAFY_SERVER_ERROR);
    }

    private String sanitizeBody(String body) {
        if (body == null) {
            return "";
        }

        String normalized = body.replaceAll("\\s+", " ").trim();
        if (normalized.length() <= 300) {
            return normalized;
        }

        return normalized.substring(0, 300) + "...";
    }

    public ResponseEntity<ApiResponse<ReissueResponse>> reissue(String authorizationHeader) {

        // 1. 헤더에서 Refresh Token 추출
        if (authorizationHeader == null || !authorizationHeader.startsWith("Bearer ")) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
        String refreshToken = authorizationHeader.substring(7);

        // 2. Refresh Token 유효성 검증
        if (!jwtTokenProvider.validateRefreshToken(refreshToken)) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }

        // 3. Refresh Token에서 userId 추출
        Long userId = jwtTokenProvider.getUserId(refreshToken);

        // 4. Redis에서 Refresh Token 조회 및 일치 여부 확인
        String storedRefreshToken = redisTemplate.opsForValue().get(String.valueOf(userId));
        if (storedRefreshToken == null || !storedRefreshToken.equals(refreshToken)) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }

        // 5. 유저 조회
        UserEntity user = userRepository.findById(userId)
                .orElseThrow(() -> new CustomException(ErrorCode.INVALID_USER));

        // 6. 새로운 Access Token 발급
        String accessToken = jwtTokenProvider.createAccessToken(user.getId(), user.getRole());

        return ResponseEntity.ok(
                ApiResponse.success("Access Token 재발급이 완료되었습니다.",
                        new ReissueResponse(accessToken))
        );
    }

    public ResponseEntity<ApiResponse<Void>> logout(Long userId) {

        // Redis에서 Refresh Token 삭제
        redisTemplate.delete(String.valueOf(userId));

        return ResponseEntity.ok(
                ApiResponse.success("로그아웃이 완료되었습니다.")
        );
    }
}
