#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "이 빌드 스크립트는 macOS에서 실행해야 합니다." >&2
  exit 1
fi

bash "$PROJECT_DIR/setup_macos.sh"

VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
"$VENV_PYTHON" -m pip install -r requirements-dev.txt

# Keep Chromium under the Playwright package so --collect-all can bundle it.
PLAYWRIGHT_BROWSERS_PATH=0 "$VENV_PYTHON" -m playwright install chromium
PLAYWRIGHT_PACKAGE_DIR="$("$VENV_PYTHON" -c 'import pathlib, playwright; print(pathlib.Path(playwright.__file__).parent)')"
BUNDLED_BROWSER_DIR="$PLAYWRIGHT_PACKAGE_DIR/driver/package/.local-browsers"

if [[ ! -d "$BUNDLED_BROWSER_DIR" ]]; then
  echo "오류: 앱에 포함할 Chromium 폴더를 찾지 못했습니다: $BUNDLED_BROWSER_DIR" >&2
  exit 1
fi

PLAYWRIGHT_BROWSERS_PATH=0 "$VENV_PYTHON" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name ReservationMonitor \
  --osx-bundle-identifier com.reservationmonitor.app \
  --collect-all playwright \
  --add-data "$BUNDLED_BROWSER_DIR:playwright/driver/package/.local-browsers" \
  main.py

echo "완료: dist/ReservationMonitor.app"
