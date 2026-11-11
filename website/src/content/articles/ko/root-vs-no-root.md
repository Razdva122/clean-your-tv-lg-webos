---
lang: ko
topic: root-vs-no-root
title: "LG webOS 런처의 Root와 No-root 비교"
description: "LG webOS TV에 맞는 Clean Your TV 에디션을 선택하세요. 설치 전 접근 권한, 개발자 모드 유지, Home 조작과 복구 방법을 비교합니다."
updated: '2026-11-09'
---

LG TV에서 개발자 모드를 사용한다면 No-root를 선택하세요. Root는 이미 정상 작동하는 루트 접근 권한과 호환 서비스가 있을 때만 선택하세요. 두 Clean Your TV 에디션은 같은 홈 인터페이스를 제공하며 설치 후 TV에서 실행됩니다. 설치 프로그램은 루트 권한을 얻거나 펌웨어를 플래시하지 않습니다.

## No-root에는 무엇이 필요한가요?

No-root는 설정 시 LG 개발자 모드, Key Server와 로컬 페어링을 사용합니다. Home Helper가 TV에서 실행되며 기기와 펌웨어가 지원하는 경우 Home 버튼을 처리합니다. 일상적인 사용 중에는 컴퓨터나 휴대전화를 켜 둘 필요가 없습니다.

계속 유지해야 하는 조건은 개발자 모드입니다. 세션 만료 전에 연장하세요. LG는 개발자 모드를 끄거나 세션이 만료되면 이를 통해 설치한 앱이 제거될 수 있다고 안내합니다. 프로젝트의 자동 갱신 옵션은 선택적 베타 기능이며 기본값은 꺼짐입니다. 동작을 보장하는 기능으로 여기지 마세요. 이 에디션을 사용하기 전에 [개발자 모드 안내](/clean-your-tv-lg-webos/ko/articles/lg-developer-mode/)를 읽어 보세요.

## Root에는 무엇이 필요한가요?

Root는 기존의 루트 SSH 접근 권한, 호환되는 TV 서비스와 지원되는 입력·런타임 기능을 사용합니다. 루트 권한만으로 호환성이 보장되지는 않습니다. 설치 프로그램이 환경을 확인하므로, 통과하지 못한 사전 요구 사항을 우회하거나 시스템 런타임을 교체해 억지로 통과시키지 마세요.

Root에는 별도 패키지와 Home 라우팅 방식이 있습니다. 이미 루팅된 환경 위에 개발자 모드를 켜지 말고, Root 라우팅을 사용하기 전에 No-root Home Helper를 정지하세요. 에디션 선택은 이미 가진 접근 권한에 맞추는 일이며, TV를 루팅해 주는 버튼을 고르는 일이 아닙니다.

## 유지 관리와 복구 비교

- **일상 사용:** 두 에디션 모두 TV에서 실행되며 런처에서 앱과 테마를 사용할 수 있습니다.
- **No-root 유지 관리:** 개발자 모드를 활성 상태로 유지하고 Helper에 필요한 페어링과 연결을 유지하세요.
- **Root 유지 관리:** 독립적인 복구 서비스와 그에 필요한 런타임을 사용할 수 있게 유지하세요. 업데이트 가능 여부는 설치한 에디션과 지원되는 업데이트 경로에 따라 달라집니다. 루트 권한만으로 OTA가 활성화되지는 않습니다.
- **긴급 종료:** 현재 지원되는 에디션은 2초 안에 Home 버튼을 세 번 짧게 누릅니다. Home Helper 0.6.13 이하는 대신 2초 동안 길게 누릅니다.

긴급 정지 후 지속적인 라우팅을 다시 시작하려면 명시적인 작업이 필요합니다. No-root에서는 Home Helper를 열어 Start Helper를 선택하고, Root에서는 Home 설정의 Change Home을 사용하세요. [에디션 비교](/clean-your-tv-lg-webos/ko/editions/)와 [복구 도움말](/clean-your-tv-lg-webos/ko/help/#home-button)을 참고하세요.

## 설치 전에 TV 확인하기

정확한 모델명, 펌웨어, webOS와 리모컨 정보를 준비하고 [호환성 페이지](/clean-your-tv-lg-webos/ko/compatibility/)를 읽으세요. 보고된 결과는 특정 구성에 관한 것입니다. 설정 후 Home, 앱 실행, 소리, 대기 모드와 완전히 껐다 켜기를 각각 테스트하세요. 패키지가 설치되었다고 해서 모두 작동한다는 뜻은 아닙니다.

[정식 배포 설치 프로그램과 설치 안내](/clean-your-tv-lg-webos/ko/install/)를 사용하세요. 이미 정상 작동하는 환경에서 에디션을 바꾸려면 다른 에디션을 덮어 설치하지 말고 문서의 전환 및 제거 절차를 따르세요.

## 출처와 다음 단계

- [프로젝트 에디션 비교](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [프로젝트 요구 사항 및 알려진 제한](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/COMPATIBILITY.md)
- [다른 홈 화면으로 바뀌는 점](/clean-your-tv-lg-webos/ko/articles/change-lg-webos-home-screen/)
