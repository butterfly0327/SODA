package ssafy.E105.global.auth.jwt;

import io.jsonwebtoken.*;
import io.jsonwebtoken.security.Keys;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import ssafy.E105.global.common.enums.Role;
import ssafy.E105.global.exception.CustomException;
import ssafy.E105.global.exception.ErrorCode;

import javax.crypto.SecretKey;
import java.util.Base64;
import java.util.Date;

@Slf4j
@Component
@RequiredArgsConstructor
public class JwtTokenProvider {

    @Value("${jwt.secret}")
    private String secretKey;

    @Value("${jwt.access-token-expiration}")
    private long accessTokenExpiration;

    @Value("${jwt.refresh-token-expiration}")
    private long refreshTokenExpiration;

    private SecretKey key;

    @PostConstruct
    protected void init() {
        byte[] keyBytes = Base64.getDecoder().decode(secretKey);
        this.key = Keys.hmacShaKeyFor(keyBytes);
    }

    public long getRefreshTokenExpiration() {
        return refreshTokenExpiration;
    }

    // Access Token 생성
    public String createAccessToken(Long userId, Role role) {
        Date now = new Date();
        Date validity = new Date(now.getTime() + accessTokenExpiration);

        return Jwts.builder()
                .subject(String.valueOf(userId))
                .claim("role", role.name())
                .issuedAt(now)
                .expiration(validity)
                .signWith(key)
                .compact();
    }

    // Refresh Token 생성
    public String createRefreshToken(Long userId) {
        Date now = new Date();
        Date validity = new Date(now.getTime() + refreshTokenExpiration);

        return Jwts.builder()
                .subject(String.valueOf(userId))
                .claim("type", "refresh")
                .issuedAt(now)
                .expiration(validity)
                .signWith(key)
                .compact();
    }

    // 토큰에서 userId 추출
    public Long getUserId(String token) {
        return Long.parseLong(parseClaims(token).getSubject());
    }

    // 토큰에서 role 추출
    public Role getRole(String token) {
        return Role.valueOf(parseClaims(token).get("role", String.class));
    }

    // Access Token 유효성 검증
    public boolean validateToken(String token) {
        try {
            parseClaims(token);
            return true;
        } catch (ExpiredJwtException e) {
            log.error("만료된 토큰입니다: {}", e.getMessage());
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        } catch (JwtException | IllegalArgumentException e) {
            log.error("유효하지 않은 토큰입니다: {}", e.getMessage());
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
    }

    // Refresh Token 검증
    public boolean validateRefreshToken(String token) {
        try {
            Claims claims = parseClaims(token);
            String type = claims.get("type", String.class);
            if (!"refresh".equals(type)) {
                log.error("Refresh Token이 아닙니다");
                return false;
            }
            return true;
        } catch (ExpiredJwtException e) {
            log.error("만료된 Refresh Token입니다");
            return false;
        } catch (JwtException | IllegalArgumentException e) {
            log.error("유효하지 않은 Refresh Token입니다");
            return false;
        }
    }

    // 만료된 토큰에서 userId 추출 (재발급용)
    public Long getUserIdFromExpiredToken(String token) {
        try {
            return Long.parseLong(parseClaims(token).getSubject());
        } catch (ExpiredJwtException e) {
            return Long.parseLong(e.getClaims().getSubject());
        }
    }

    private Claims parseClaims(String token) {
        return Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }
}