#!/bin/bash
# ============================================================
# install-hooks.sh — Git Hook 자동 설치 스크립트
# ============================================================
#
# 사용법:
#   프로젝트 루트에서 실행
#   $ bash scripts/init/install-hooks.sh
#
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK_SOURCE="$SCRIPT_DIR/prepare-commit-msg"
HOOK_TARGET=".git/hooks/prepare-commit-msg"

# Git 저장소인지 확인
if [ ! -d ".git" ]; then
    echo "❌ .git 디렉토리가 없습니다. 프로젝트 루트에서 실행하세요."
    exit 1
fi

# Hook 설치
cp "$HOOK_SOURCE" "$HOOK_TARGET"
chmod +x "$HOOK_TARGET"

echo "✅ Git Hook 설치 완료"
echo ""
echo "커밋 메시지 예시:"
echo "  feat[#31]: docker-compose.dev.yml 생성"
echo "  → 자동 변환: feat[S14P21E105-31]: docker-compose.dev.yml 생성"
echo ""
echo "지원 패턴:"
echo "  feat[#31]: 단일 이슈"
echo "  feat[#31,#32]: 다중 이슈"
echo "  fix[#31]: 버그 수정"
echo "  chore[#31]: 기타 작업"
