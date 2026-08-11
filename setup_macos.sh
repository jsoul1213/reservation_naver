#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "오류: 이 설치 스크립트는 macOS에서 실행해야 합니다." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "오류: Python 3가 없습니다. https://www.python.org/downloads/macos/ 에서 설치하세요." >&2
  exit 1
fi

python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' || {
  echo "오류: Python 3.10 이상이 필요합니다. 현재 버전: $(python3 --version)" >&2
  exit 1
}

python3 -c 'import tkinter' 2>/dev/null || {
  echo "오류: 현재 Python에 Tkinter가 없습니다." >&2
  echo "python.org의 macOS용 Python 설치 프로그램 사용을 권장합니다." >&2
  exit 1
}

echo "[1/5] Python 가상환경 준비"
python3 -m venv .venv

VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

echo "[2/5] Python 패키지 설치"
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r requirements.txt

echo "[3/5] Playwright Chromium 설치"
"$VENV_PYTHON" -m playwright install chromium

echo "[4/5] 프로그램 단위 테스트"
"$VENV_PYTHON" -m unittest discover -s tests -v

echo "[5/5] GUI 및 브라우저 실행 환경 점검"
"$VENV_PYTHON" doctor.py

echo
echo "설치 완료"
echo "실행 명령: bash run_macos.sh"
