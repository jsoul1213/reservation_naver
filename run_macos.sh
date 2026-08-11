#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "오류: 이 실행 스크립트는 macOS용입니다." >&2
  exit 1
fi

VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

if [[ ! -x "$VENV_PYTHON" ]] || ! "$VENV_PYTHON" -c 'import playwright, tkinter' 2>/dev/null; then
  echo "최초 설치 또는 환경 복구를 시작합니다."
  bash "$PROJECT_DIR/setup_macos.sh"
fi

exec "$VENV_PYTHON" "$PROJECT_DIR/main.py"
