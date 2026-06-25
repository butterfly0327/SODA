# S2 Nginx Failover Runbook

## 1. Status

이 문서는 **현재 아키텍처에서 비활성 문서**다.

기준 문서:

- `C:\Users\SSAFY\Desktop\soda\docs\Infrastructure.md`
- `C:\Users\SSAFY\Desktop\soda\infra\S1_S2_INFRA_PLAN.md`
- `C:\Users\SSAFY\Desktop\soda\docs\adr\ADR-003-rabbitmq-redis-for-async-processing.md`

현재 구조:

- `S1`: `prod active + dev active`
- `S2`: `async / ops`
- 외부 ingress는 `S1 nginx` 하나만 사용
- `dev`는 `S1` 단일 서버에서 운영
- 자동 failover는 현재 범위에 포함하지 않음

## 2. Scope

현재 운영에는 적용되지 않는다.

포함:

- 과거 설계에서 고려했던 `S2 nginx` 기반 failover 아이디어

비포함:

- 현재 운영 절차
- 현재 장애 대응 runbook
- broker 고가용성
- multi-AZ 라우팅 전략

## 3. Preconditions

현재 결정은 다음과 같다.

1. `S2 nginx`는 두지 않는다.
2. `S2`는 `async / ops` 전용으로 유지한다.
3. 외부 ingress는 `S1 nginx` 하나만 사용한다.
4. 자동 failover는 현재 범위에 포함하지 않는다.

## 4. Health Check Targets

다음 조건이 충족되면 이 문서를 새 구조로 다시 작성한다.

1. `LB` 또는 `DNS failover`를 실제로 도입한다.
2. 동일 도메인 기준 자동 전환이 요구사항으로 확정된다.
3. `S2`에 다시 ingress를 둘 명확한 이유가 생긴다.

## 5. Automatic Failover Flow

## 5. Notes

- 현재 운영 문서는 `C:\\Users\\SSAFY\\Desktop\\soda\\docs\\Infrastructure.md`와 `C:\\Users\\SSAFY\\Desktop\\soda\\infra\\S1_S2_INFRA_PLAN.md`를 기준으로 본다.
- 이 파일은 기록 보존용이며, 실행 runbook으로 사용하지 않는다.
