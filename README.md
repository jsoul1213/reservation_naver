# Reservation Monitor

Python + Playwright로 지정된 네이버 예약 페이지를 반복 확인하고, 선택한 날짜와 회차가
`SOLD_OUT → AVAILABLE`로 바뀌면 macOS 알림·사운드·이메일로 알려주는 프로그램입니다.
자동 예약, 좌석 선택, 결제, CAPTCHA·대기열·로그인 우회는 하지 않습니다.

## 결론: 실행만 하면 자동으로 되는가?

새 Mac에서는 최초 1회 설치가 필요합니다. 이 프로젝트에서는 설치 과정을 스크립트로
자동화했습니다.

| 상황 | 해야 할 일 |
|---|---|
| 새 Mac에서 최초 실행 | 터미널에서 `bash run_macos.sh` 실행 |
| 두 번째 실행부터 | `bash run_macos.sh` 실행 |
| GUI가 열린 뒤 | `모니터링 시작` 버튼 클릭 |
| 터미널 없이 사용 | 한 번 `.app`을 빌드한 뒤 Finder에서 실행 |

`run_macos.sh`는 필요한 환경이 없으면 자동으로 다음 작업을 수행합니다.

1. `.venv` Python 가상환경 생성
2. 필요한 Python 패키지 설치
3. Playwright Chromium 설치
4. 단위 테스트 실행
5. GUI 및 Chromium 실행 점검
6. 모두 성공하면 프로그램 GUI 실행

단, Mac이 꺼지거나 잠자기 상태가 되거나, 프로그램 또는 Playwright 브라우저를 닫으면
감시는 중단됩니다. 프로그램이 자동으로 표를 예약하는 것은 아니며, 알림을 받은 뒤
사용자가 직접 예약해야 합니다.

## 1. 새 Mac 준비

필요한 환경은 다음과 같습니다.

- macOS 14 Sonoma 이상(현재 Playwright 공식 지원 범위)
- 인터넷 연결
- Python 3.10 이상
- 프로젝트 폴더를 저장할 여유 공간
- Chromium 다운로드와 `.app` 빌드를 위한 추가 디스크 공간

Python이 없다면 [Python 공식 macOS 다운로드](https://www.python.org/downloads/macos/)에서
macOS installer를 설치하세요. Python 3.13 계열을 권장합니다. 설치 후 터미널에서 다음
명령이 동작해야 합니다.

```bash
python3 --version
```

예상 출력은 `Python 3.13.x`와 비슷합니다. 시스템에 임의로 포함된 오래된 Python보다
python.org 설치본 사용을 권장합니다. Playwright의 현재 공식 지원 환경도
[Playwright Python 설치 문서](https://playwright.dev/python/docs/intro)에서 확인할 수
있습니다.

## 2. 프로젝트 폴더로 이동

Finder에서 프로젝트 폴더를 확인한 뒤 터미널에서 해당 폴더로 이동합니다. 폴더를
터미널 창으로 끌어다 놓으면 경로를 쉽게 입력할 수 있습니다.

```bash
cd "/Users/사용자이름/프로젝트가_있는_폴더/개발 test"
```

경로에 공백이나 한글이 있으면 반드시 큰따옴표로 감싸세요.

## 3. 가장 간단한 설치 및 실행

다음 한 줄을 실행합니다.

```bash
bash run_macos.sh
```

최초 실행은 Python 패키지와 Chromium을 다운로드하므로 인터넷 속도에 따라 몇 분이
걸릴 수 있습니다. `설치 완료` 메시지 뒤 GUI가 열리면 정상입니다. 이후 실행에서도
같은 명령을 사용하면 이미 설치된 환경을 재사용합니다.

설치만 먼저 수행하고 싶다면 다음 명령을 사용합니다.

```bash
bash setup_macos.sh
```

## 4. 기본 설정

처음 실행할 때 이미 다음 값이 설정되어 있습니다.

| 항목 | 기본값 | 설명 |
|---|---:|---|
| 예약 URL | 제공된 2026-08-15 네이버 예약 URL | 감시 대상 |
| 확인 주기 | 3초 | 최소값 2초 |
| macOS 알림 | 켜짐 | Notification Center 알림 |
| 사운드 | 켜짐 | Glass 시스템 사운드 |
| 이메일 | 꺼짐 | SMTP 설정 후 선택적으로 사용 |
| 브라우저 | 화면에 표시 | 직접 로그인할 수 있도록 headless 비활성화 |
| 사용자 CSS 선택자 | 비어 있음 | 현재 대상은 코드에 맞춤 판정이 적용되어 불필요 |

GUI에서 URL이 다음 주소인지 확인합니다.

```text
https://booking.naver.com/booking/12/bizes/1693898/items/7874774?startDateTime=2026-08-15T00%3A00%3A00%2B09%3A00
```

확인 주기는 3초를 권장합니다. 2초보다 짧게 설정할 수 없으며, 서비스 부하와 이용
정책을 고려해 지나치게 짧은 주기를 사용하지 마세요.

## 5. 실제 모니터링 시작

1. GUI에서 URL과 확인 주기를 확인합니다.
2. `macOS 알림`과 `사운드`가 선택되어 있는지 확인합니다.
3. `모니터링 시작`을 누릅니다.
4. Playwright Chromium 창이 열립니다.
5. 네이버 로그인이 필요하면 그 브라우저에서 사용자가 직접 로그인합니다.
6. GUI의 현재 상태와 로그를 확인합니다.

정상 매진 상태에서는 다음과 같이 표시됩니다.

```text
현재 상태: SOLD_OUT
```

상태의 의미는 다음과 같습니다.

- `SOLD_OUT`: 선택한 날짜 또는 회차가 매진
- `AVAILABLE`: 선택 가능한 회차가 확인됨
- `UNKNOWN`: 페이지 오류, 로그인 대기 또는 DOM 구조를 확실히 판정할 수 없음

프로그램을 켠 직후 이미 `AVAILABLE`이면 기준 상태만 저장하고 알림을 보내지 않습니다.
이후 `SOLD_OUT → AVAILABLE`로 변할 때만 한 번 알립니다. `AVAILABLE`이 계속 유지되는
동안에는 중복 알림을 보내지 않으며, 다시 매진되었다가 풀리면 새 알림을 보냅니다.

Playwright 브라우저 창을 임의로 닫지 말고 GUI의 `중지` 버튼으로 끝내세요. 오류로
브라우저가 종료되면 프로그램은 반복 오류를 감지해 브라우저 재시작을 시도합니다.

## 6. 최초 로그인과 세션

로그인은 자동화하지 않습니다. 처음 로그인 화면이 나오면 Playwright 브라우저에서
직접 로그인해야 합니다. 로그인 화면을 감지하면 프로그램은 입력을 방해하지 않도록
페이지 새로고침을 멈춥니다.

로그인 세션은 다음 전용 폴더에 보관됩니다.

```text
~/.reservation_monitor/browser_profile
```

네이버 비밀번호는 소스 코드나 설정 파일에 저장하지 않습니다. 프로필 폴더는 개인
로그인 세션을 포함할 수 있으므로 다른 사람에게 전달하지 마세요.

## 7. macOS 알림 권한

최초 알림 때 macOS가 권한을 묻는다면 허용합니다. 알림이 보이지 않으면 다음 위치를
확인합니다.

```text
시스템 설정 → 알림 → Python 또는 ReservationMonitor → 알림 허용
```

집중 모드가 켜져 있으면 알림이나 사운드가 표시되지 않을 수 있습니다. 설치 후 실제
예약 페이지에 접속하지 않고 로컬 알림만 시험하려면 다음 명령을 실행합니다.

```bash
.venv/bin/python doctor.py --notify
```

알림과 Glass 사운드가 한 번 실행되면 정상입니다.

## 8. 이메일 알림 설정 — 선택 사항

이메일을 사용하지 않아도 macOS 알림과 사운드는 정상 작동합니다. 이메일이 필요할
때만 GUI에서 `이메일`을 켜고 다음 값을 입력합니다.

| 항목 | Gmail 예시 |
|---|---|
| SMTP 서버 | `smtp.gmail.com` |
| SMTP 포트 | `587` |
| SMTP 사용자 | 본인 Gmail 주소 |
| 보내는 주소 | 본인 Gmail 주소 |
| 수신 주소 | 알림을 받을 주소 |
| SMTP 앱 비밀번호 | Google에서 발급한 앱 비밀번호 |

일반 Gmail 비밀번호를 입력하지 마세요. SMTP 앱 비밀번호는 설정 파일에 저장되지
않으며 프로그램을 새로 실행하면 다시 입력해야 합니다. 환경 변수로 전달하려면 다음과
같이 실행할 수 있습니다.

```bash
export RESERVATION_MONITOR_SMTP_PASSWORD='앱-비밀번호'
bash run_macos.sh
```

이메일은 macOS 알림과 사운드 이후 별도 스레드에서 발송되므로 이메일 실패가 로컬
알림을 막지 않습니다.

## 9. 터미널 없이 `.app` 만들기

`.app`은 반드시 실제 Mac에서 빌드해야 합니다. PyInstaller는 다른 운영체제용 앱을
교차 빌드하지 않으므로 Windows에서 macOS 앱을 만들 수 없습니다.

프로젝트 폴더에서 다음 한 줄을 실행합니다.

```bash
bash build_macos.sh
```

빌드 스크립트가 다음 과정을 자동으로 수행합니다.

1. 기본 설치 및 테스트
2. PyInstaller 설치
3. 앱 내부에 포함할 Playwright Chromium 설치
4. `ReservationMonitor.app` 생성

완료된 앱의 위치는 다음과 같습니다.

```text
dist/ReservationMonitor.app
```

터미널에서 바로 열어보려면 다음을 실행합니다.

```bash
open dist/ReservationMonitor.app
```

정상 동작을 확인한 뒤 Finder의 `응용 프로그램` 폴더로 앱을 복사할 수 있습니다.
처음 열 때 Gatekeeper 경고가 나타나면 Finder에서 앱을 Control-클릭하고 `열기`를
선택하세요. 다른 사람에게 정식 배포하려면 Apple Developer ID 코드 서명과
notarization이 별도로 필요합니다. 빌드 옵션은
[PyInstaller 공식 문서](https://pyinstaller.org/en/stable/usage.html)를 참고하세요.

## 10. Mac 잠자기 방지 — 선택 사항

Mac이 잠자면 페이지 감시도 멈춥니다. 장시간 감시 중에만 잠자기를 방지하려면 다음과
같이 실행할 수 있습니다.

```bash
caffeinate -i bash run_macos.sh
```

이 터미널 명령과 프로그램을 종료하면 잠자기 방지 상태도 해제됩니다. 디스플레이는
꺼져도 되지만 시스템 자체가 잠자지 않아야 합니다.

## 11. 설정과 로그 위치

```text
설정: ~/.reservation_monitor/config.json
로그: ~/.reservation_monitor/reservation_monitor.log
세션: ~/.reservation_monitor/browser_profile/
```

SMTP 비밀번호는 `config.json`에 기록하지 않습니다. 문제가 생기면 로그의 마지막
`Current state`, `Monitoring cycle failed`, `Browser restart` 메시지를 확인하세요.

## 12. 환경 점검과 테스트

Naver에 접속하지 않고 GUI, Python, Playwright Chromium만 점검합니다.

```bash
.venv/bin/python doctor.py
```

전체 단위 테스트와 컴파일 검사는 다음과 같습니다.

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall .
```

## 13. 자주 발생하는 문제

### `python3: command not found`

Python 공식 macOS installer를 설치하고 터미널을 새로 연 뒤 다시 실행합니다.

### `Tkinter가 없습니다`

현재 Python 배포판에 GUI 구성 요소가 빠진 경우입니다. python.org의 macOS installer로
Python을 다시 설치하는 방법을 권장합니다.

### `Executable doesn't exist` 또는 Chromium 실행 실패

다음 명령으로 환경을 복구합니다.

```bash
bash setup_macos.sh
```

### GUI 상태가 계속 `UNKNOWN`

- Playwright 브라우저에 로그인 화면이 있는지 확인합니다.
- URL이 기본 URL과 동일한지 확인합니다.
- 인터넷 연결과 GUI 로그를 확인합니다.
- 네이버가 페이지 구조를 변경한 경우 `예약 가능 CSS`와 `매진 CSS` 보정이 필요할 수
  있습니다.

`UNKNOWN`은 안전을 위해 예약 가능으로 취급하지 않으며 알림도 보내지 않습니다.

### 프로그램을 두 번 실행했더니 브라우저가 열리지 않음

Playwright 프로필은 동시에 한 프로그램만 사용할 수 있습니다. 실행 중인
Reservation Monitor와 Playwright Chromium을 모두 종료한 뒤 하나만 실행하세요.

### 설정을 처음 상태로 되돌리고 싶음

프로그램을 종료한 뒤 설정 파일 이름을 변경합니다. 로그인 세션은 유지됩니다.

```bash
mv ~/.reservation_monitor/config.json ~/.reservation_monitor/config.backup.json
```

다음 실행 때 기본 설정 파일이 새로 생성됩니다.

## 14. 현재 대상의 판정 방식

현재 대상 페이지의 실제 DOM을 확인해 다음 신호를 사용합니다.

- 선택 날짜: `[data-click-code="calendar.date"][aria-selected="true"]`
- 회차 영역: `[data-click-code="calendar.time"]`
- 매진: 선택 날짜의 `매진` 문구 또는 날짜·회차의 `unselectable` 상태
- 예약 가능: 회차 안에 `unselectable`, `disabled`, `aria-disabled`가 없는 버튼
- 상단의 `role="tab"`인 `예약하기`는 재고와 관계없으므로 판정에서 제외

충돌하는 상태 신호가 있거나 구조를 확실히 확인하지 못하면 `UNKNOWN`으로 처리합니다.
페이지 구조를 임의로 추측해 `AVAILABLE`로 알리지 않습니다.

## 15. 프로젝트 파일

```text
main.py                  GUI 진입점
gui.py                   Tkinter 화면과 사용자 입력
monitor.py               중단 가능한 백그라운드 감시 루프
browser.py               Playwright 세션과 오류 복구
reservation_checker.py   네이버 DOM 판정과 상태 전환 추적
notification.py          macOS·사운드·이메일 실행 순서
email_notifier.py        SMTP 이메일 발송
config.py                기본 설정, 검증, JSON 저장
logger.py                파일 및 GUI 로그
doctor.py                로컬 GUI·Chromium·알림 환경 점검
setup_macos.sh           최초 환경 자동 설치
run_macos.sh             환경 자동 복구 후 실행
build_macos.sh           macOS .app 자동 빌드
tests/                   단위 테스트
```

## 이용 시 유의사항

프로그램과 Playwright 브라우저를 실행해 둔 동안에만 감시합니다. 네이버의 이용약관과
서비스 정책을 준수하고, 요청 주기를 불필요하게 짧게 설정하지 마세요. 이 프로그램은
알림까지만 제공하며 실제 예약 성공을 보장하지 않습니다.

cd "프로젝트 폴더 경로"
bash run_macos.sh

bash build_macos.sh
open dist/ReservationMonitor.app
