# Clean Your TV — 사용자 안내

Clean Your TV는 LG webOS TV를 위한 나만의 홈 화면입니다. 이 메뉴에서는 광고 행 없이 원하는 순서로 앱을 배치할 수 있습니다. 컴퓨터나 Android 휴대전화로 설치하고, 설정이 끝나면 컴퓨터를 꺼도 됩니다.

## 1. 설치 프로그램 다운로드

기기에 맞는 그림을 누르세요. 버튼은 최신 공개 버전을 다운로드합니다. Mac은 Apple Silicon(M1 이상) 또는 Intel을 선택하세요. Apple 메뉴 → 이 Mac에 관하여에서 확인할 수 있습니다.

[![다운로드 — Windows x64](../../assets/brand/downloads/windows.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-windows-x64-desktop.zip)
[![다운로드 — macOS Apple Silicon](../../assets/brand/downloads/macos-arm64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-arm64.zip)
[![다운로드 — macOS Intel](../../assets/brand/downloads/macos-x64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-x64.zip)
[![다운로드 — Linux x64](../../assets/brand/downloads/linux.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-linux-x64.deb)
[![다운로드 — Android ARM64](../../assets/brand/downloads/android.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-android-arm64.apk)

<a id="에디션-선택"></a>

<a id="설치-전-준비"></a>

## 2. 에디션 선택

TV를 켜고 컴퓨터 또는 휴대전화와 같은 홈 네트워크에 연결하세요. 요청이 나오면 CYTV의 로컬 네트워크 접근을 허용하세요.

- **No-root** — root 권한이 없는 TV입니다. 아래 순서대로 Developer Mode를 준비하세요.
- **Root** — 이미 SSH root 접근이 가능한 TV입니다. 설치 프로그램은 TV를 루팅하지 않습니다. 이 TV에서는 Developer Mode를 켜지 말고 SSH 접근과 복구 데이터를 보존하세요.

### Developer Mode 설정 (No-root)

Developer Mode를 사용하면 root 없이 TV에 CYTV 앱을 설치할 수 있습니다.

1. TV에서 LG Apps를 열고 Developer Mode를 검색하여 설치하세요.
2. Developer Mode를 열고 LG Developer 계정으로 로그인하세요. 계정이 없으면 [LG Developer](https://webostv.developer.lge.com)에서 만드세요.
3. Dev Mode Status를 켜세요. TV가 재시작되면 Developer Mode를 다시 여세요.
4. Key Server를 켜고 Developer Mode를 열어 두세요. 표시된 IP Address를 CYTV의 TV 주소로 입력하세요.
5. TV의 Developer Mode에 표시된 6자리 Passphrase를 입력하세요. 대소문자를 구분하세요.

LG 계정 비밀번호가 아닌 TV 화면의 코드를 사용하세요. 코드가 보이지 않으면 Key Server를 켜세요.

페어링은 별도 단계입니다. TV에서 요청하면 리모컨으로 CYTV를 승인하세요.

타이머가 끝나기 전에 Developer Mode를 열고 TV가 인터넷에 연결된 상태에서 EXTEND를 누르세요. 만료되면 LG가 이 앱들을 삭제할 수 있습니다.

<a id="설치와-언어-선택"></a>

## 3. 설치 프로그램 열기

- **Windows x64:** `cytv-windows-x64-desktop.zip`을 다운로드하고 파일 탐색기에서 **모두 추출**을 선택한 다음 `cytv-desktop/cytv-desktop.exe`를 여세요. `_internal` 폴더를 옆에 그대로 두세요.
- **macOS 13 이상:** Apple Silicon은 `cytv-macos-arm64.zip`, Intel은 `cytv-macos-x64.zip`을 푸세요. `cytv.app`을 응용 프로그램 폴더로 옮겨 열고 로컬 네트워크 접근을 허용하세요. 신뢰할 수 있는 다운로드가 차단되면 개인정보 보호 및 보안 → 확인 없이 열기를 사용하세요. Gatekeeper를 끄지 마세요.
- **Linux x64:** Ubuntu 22.04 이상, Debian 12 이상 또는 Mint 21 이상에서 `cytv-linux-x64.deb`를 그래픽 패키지 관리자로 설치하고 앱 메뉴에서 Clean Your TV를 여세요. 라이브러리 설치에 인터넷이 필요할 수 있습니다. Linux ARM 패키지는 없습니다.

**Android ARM64:** Android 7 이상, WebView/Chrome 108 이상인 64비트 ARM 휴대전화가 필요합니다. 다운로드한 APK를 열고 요청이 나오면 해당 출처의 앱 설치를 허용하세요. CYTV를 열고 오른쪽 위에서 언어를 선택하세요. 앱 삭제나 데이터 초기화 없이 업데이트하세요.

데스크톱 설치 마법사는 처음에 시스템 언어를 사용하고 직접 선택한 언어를 저장합니다. TV에서는 **설정 → 언어**에서 언어를 고르거나 시스템 언어를 따르는 자동 옵션을 선택하세요. 설치 프로그램과 TV의 언어 설정은 별개입니다. 지원 코드는 [언어 목록](../LANGUAGES.md)을 참조하세요.

## 4. TV에 설치

1. CYTV에서 **내 TV 설정**을 선택하세요. 컴퓨터에서는 검색된 TV를 선택하고 Android에서는 TV IP 주소를 입력하세요. 검색되지 않으면 주소를 직접 입력하세요.
2. **No-root** 또는 **Root**를 선택하고 TV가 맞는지 확인하세요.
3. No-root는 Developer Mode 화면의 코드를 입력하고 TV의 요청을 승인하세요. Root는 기존 SSH 인증 정보를 사용하세요. 신뢰하는 네트워크에서 본인 TV의 새 SSH 신원만 승인하세요. 저장된 키가 바뀌면 중지하고 원인을 확인하세요.
4. 마법사의 안내를 따르세요. 끝날 때까지 TV를 켜 두고 네트워크를 바꾸거나 CYTV를 닫지 마세요. Android 앱을 강제 종료하지 마세요. Root는 복구 준비 직후 Home 제어를 켭니다.

## 5. 리모컨 확인

1. TV에서 다른 앱을 열고 **Home**을 짧게 누르세요. Clean Your TV가 열려야 합니다. 마법사에서 실제로 본 결과를 선택하고, 확인하지 않았다면 건너뛰세요.
2. 방향키, OK, 뒤로, 음량과 소리를 확인하세요. 대기/깨우기와 전원을 분리한 뒤 시작하는 동작은 따로 확인하세요. 설치 성공만으로 이 동작들이 확인되지는 않습니다.

<a id="사용과-복구"></a>

## 6. 사용과 복구

방향키로 선택하고 OK로 실행합니다. OK를 길게 눌러 순서를 바꿉니다. 뒤로를 짧게 누르면 앱의 탐색과 종료 확인이 유지됩니다. Home 제어가 활성화되면 짧은 Home으로 런처를 엽니다. 뒤로를 1.2초 동안 누르면 LG Home이 한 번 열립니다. Home 제어 스위치와 설정은 바뀌지 않습니다.

**2초 안에 Home을 세 번 짧게 누르세요.** 매번 버튼을 놓아야 합니다. 설정을 지우지 않고 LG Home으로 복귀하며 Home 제어를 중지합니다.

No-root: Home 제어를 다시 시작하려면 Home Helper를 열고 Helper 시작을 선택한 다음 확인하세요. 저장된 Home 화면 선택은 유지됩니다. Root는 Home 설정에서 **Home 변경**을 켜서 재개하세요. **LG Home 열기**는 Home의 연결 대상을 바꾸지 않고 LG Home을 한 번 엽니다. LG Home을 계속 사용할 기본 대상으로 복원하려면 **Home 변경**을 끄세요. 두 제어 프로그램을 동시에 실행하지 마세요. 문제가 반복되면 LG Home을 유지하세요.

## 도움이 필요하신가요?

설치가 중단되면 같은 저장된 연결로 **TV 상태 확인**을 먼저 선택하세요. 마법사가 제공하는 복구 작업으로만 계속하세요. 상태를 알 수 없으면 진단 보고서를 저장하고 중지하세요. 복구 데이터를 보존하고 무작정 재설치하지 마세요.

복구 중에는 Home 제어를 끈 상태로 두고 원래 진단 보고서와 저장된 연결을 보존하세요. 검사와 변경은 각각 따로 확인하세요. 설치된 버전에 맞는 자세한 복구 안내를 따르고, 강제로 재설치하거나 복구 상태를 지우지 마세요.

TV 모델, 펌웨어, No-root 또는 Root, 설치 기기, 실패한 단계와 오류 메시지를 알려 주세요. 보고서를 공유하기 전에 비밀번호, 키, 주소와 개인 정보를 제거하세요. 보고서는 자동 공개되지 않습니다.

[문제 신고](../FEEDBACK.md) · [자세한 복구 — 영어](../RECOVERY.md) · [업데이트 및 삭제 — 영어](../MAINTENANCE.md) · [다른 언어](../LANGUAGES.md)

향후 빌드에서는 4K가 선택되었거나 재생 중이고 입력 미리보기가 켜진 테마에서만 안내와 “HDMI 미리보기 끄기” 버튼이 표시됩니다. HDMI 미리보기 중에는 4K 동영상 배경이 일시적으로 1080p 정지 이미지로 바뀝니다. 배경을 4K로 유지하려면 입력 미리보기를 끄세요.

### 후보 빌드: 간단한 제거

위 다운로드 버튼은 계속 공개 버전을 제공합니다. 다음 후보 빌드에서는 동일한 저장된 TV 연결로 유지관리의 **Clean Your TV 제거**를 선택하세요. 한 번 확인하면 존재하는 알려진 프로젝트 앱과 파일을 제거하고 없는 항목은 건너뜁니다. 부분 설치 후에도 사용할 수 있습니다.

안내가 나오면 TV 전원을 분리했다가 다시 연결하고 네트워크를 기다린 후 **다시 시도**를 선택하세요. 대기 모드나 Quick Start는 완전한 재시작이 아니며 CYTV가 TV를 자동으로 재시작하지 않습니다. 연결이 끊기면 확인 후 별도 복구 마법사 없이 같은 제거를 다시 시도하세요. 접근이 거부되면 요청된 Root 연결을 사용하고 TV가 사용 중이면 기다린 후 다시 시도하세요. 최종 정리가 검증된 후에만 성공으로 표시됩니다. 키와 원본 보고서를 보관하세요. 위 비상 제어와 공유 동의는 계속 적용됩니다.

이 후보 버전에서는 설치 실패나 중단 후 복구를 바로 선택할 수 있습니다. No-root 설치를 계속할 수 없으면 전체 제거를 한 번 확인하세요. 일시적인 연결 끊김이나 CYTV 작업 중에는 제거를 최대 세 번 시도합니다. Root 권한이 필요하면 같은 TV에서 **Root로 연결**을 선택하세요. 검증된 Root 정리는 차단된 No-root 제거도 완료합니다. Root 활성화 실패 시 활성화를 반복하지 않고 LG Home 복원과 검증을 시도합니다. 미완료 작업을 취소해도 진단 보고서와 복구 작업이 유지됩니다. 비상 정지 상태는 변경하지 않습니다.

<!-- Legacy anchors retained for existing links. Detailed references: -->
<a id="root용-선택적-python-런타임"></a>
<a id="하드웨어-검증-범위"></a>
<a id="120의-lg-펌웨어-차단"></a>
<a id="130의-새-기능-데스크톱-복구-안내"></a>
<a id="130의-새-기능--12"></a>
<a id="미출시-후보-homebrew를-통한-root-설치"></a>
<a id="미출시-후보-hdmi-사운드-복원-root"></a>
<a id="테마-154"></a>
<a id="설정-카테고리-미출시-후보"></a>
<a id="자동-그래픽-해상도-후보"></a>
<a id="업데이트와-제거"></a>
<a id="도움말과-자세한-안내"></a>
<a id="테마"></a>
<a id="설정-카테고리-154"></a>
<a id="자동-그래픽-해상도-160"></a>
<a id="저장-공간"></a>

자세한 영어 참고 문서: [요구사항](../COMPATIBILITY.md) · [리모컨](../CONTROLS.md) · [테마](../THEMES.md) · [업데이트](../UPDATES.md).
