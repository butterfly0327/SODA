package ssafy.E105.domain.user.entity;

import jakarta.persistence.*;
import lombok.*;
import ssafy.E105.global.common.entity.BaseTimeEntity;
import ssafy.E105.global.common.enums.Region;
import ssafy.E105.global.common.enums.Role;

@Entity
@Table(name = "users")
@Getter
@Builder
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
public class UserEntity extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "ssafy_id", nullable = false, unique = true, length = 100)
    private String ssafyId;  // SSAFY OAuth 고유 ID

    @Column(nullable = false, length = 100)
    private String name;

    @Column(nullable = false, length = 100)
    private String email;

    @Column(length = 50)
    private String edu;  // 기수

    @Enumerated(EnumType.STRING)
    @Column(name = "ent_regn_cd", length = 50)
    private Region entRegnCd;  // 지역

    @Builder.Default
    @Column(name = "retire_yn", length = 10)
    private String retireYn = "F";

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 10)
    private Role role;

    @Builder.Default
    @Column(name = "is_deleted", nullable = false)
    private boolean isDeleted = false;

    public UserEntity(String ssafyId, String name, String email,
                      String edu, Region entRegnCd, String retireYn, Role role) {
        this.ssafyId = ssafyId;
        this.name = name;
        this.email = email;
        this.edu = edu;
        this.entRegnCd = entRegnCd;
        this.retireYn = retireYn;
        this.role = role;
        this.isDeleted = false;
    }

    public void delete() {
        this.isDeleted = true;
    }

    public void restore() {
        this.isDeleted = false;
    }

    public boolean isDeleted() {
        return isDeleted;
    }

}
