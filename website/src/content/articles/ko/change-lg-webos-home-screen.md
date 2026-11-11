---
lang: ko
topic: change-lg-webos-home-screen
title: "LG webOS TV의 홈 화면을 바꾸는 방법"
description: "Clean Your TV로 LG webOS 홈 화면을 꾸며 보세요. 런처가 바꾸는 부분, 에디션 선택 방법과 설치 전 확인 사항을 알아봅니다."
updated: '2026-11-09'
---

Clean Your TV는 LG webOS TV용 대체 홈 화면입니다. 앱을 원하는 순서로 배치하고, 테마와 맞춤 설정 가능한 독을 사용할 수 있습니다. 설정을 마치면 TV에서 실행되므로 컴퓨터를 꺼도 됩니다. Home 버튼을 처리할 수 있는지는 TV, 펌웨어, 리모컨과 설치 방식에 따라 다릅니다.

## 무엇을 바꿀 수 있나요?

런처는 TV 앱을 찾아 실행하는 화면을 바꿉니다. 즐겨찾기를 정리하고 Classic, Liquid Glass, Ribbon 등의 레이아웃을 선택할 수 있습니다. 설치 전에 [브라우저 데모](/clean-your-tv-lg-webos/demo/)에서 레이아웃을 비교해 보세요. 데모의 TV 조작은 시뮬레이션이므로 실제 TV와의 호환성을 확인할 수는 없습니다.

대체 런처는 webOS 펌웨어를 교체하거나 유료 스트리밍을 무료로 이용하게 해 주지 않으며, 다른 앱 안의 광고를 제거하지도 않습니다. 화면 설정, 입력과 스트리밍 서비스는 TV의 별도 기능으로 남습니다. 더 조용한 홈 화면이 목적이라면 [광고와 관련해 달라지는 점](/clean-your-tv-lg-webos/ko/articles/lg-tv-home-screen-ads/)을 읽어 보세요.

## 어떤 설치 방식을 선택해야 하나요?

LG 개발자 모드가 활성화된 TV에는 No-root를 사용하세요. TV에서 실행되는 Home Helper가 지원되는 환경에서 Home 버튼을 처리합니다. 개발자 모드는 계속 활성 상태여야 하며, 세션이 만료되면 직접 설치한 앱이 제거될 수 있습니다.

Root는 TV에 이미 정상 작동하는 루트 접근 권한이 있고 런타임 및 서비스 요구 사항을 충족할 때만 사용하세요. Clean Your TV 설치 프로그램은 TV에 루트 권한을 부여하지 않습니다. 이미 루팅된 환경 위에 개발자 모드를 켜거나 두 Home 라우팅 방식을 동시에 실행하지 마세요. [에디션 안내](/clean-your-tv-lg-webos/ko/articles/root-vs-no-root/)에서 각 방식의 차이를 확인할 수 있습니다.

## 현재 설정을 바꾸기 전에

1. 정확한 모델명, 펌웨어, webOS 버전과 리모컨 종류를 기록하세요. [요구 사항 및 TV 사용 결과](/clean-your-tv-lg-webos/ko/compatibility/)와 비교하세요. 각 보고서는 기록된 구성에만 적용됩니다.
2. [설치 안내](/clean-your-tv-lg-webos/ko/install/)를 따르고 그곳에 연결된 정식 배포 설치 프로그램을 사용하세요. 설정 중에는 TV와 설치 기기가 서로 통신할 수 있는 네트워크에 있어야 합니다.
3. 설정 후 앱 실행과 Home 동작을 확인하고, 소리, 대기 모드 진입·복귀, 완전히 껐다 켜기도 각각 확인하세요. 패키지 설치 성공만으로 이런 동작이 검증되지는 않습니다.

## LG Home으로 돌아가려면 어떻게 하나요?

현재 지원되는 에디션에서는 2초 안에 Home 버튼을 세 번 짧게 누르면 긴급 종료가 실행됩니다. Home Helper 0.6.13 이하의 이전 버전에서는 Home 버튼을 2초 동안 길게 누릅니다. LG Home을 한 번 여는 것과 지속적인 Home 라우팅을 끄는 것은 서로 다른 작업입니다. 설치한 에디션에 맞는 [복구 안내](/clean-your-tv-lg-webos/ko/help/#home-button)를 따르세요. 시작 동작을 바꾸기 전에 복구 경로를 확보해 두세요.

## 출처와 다음 단계

- [프로젝트 에디션 및 조작 참고 문서](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [프로젝트 설치 및 사전 요구 사항](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/INSTALL.md)
- [개발자 모드: No-root 환경을 계속 사용하기](/clean-your-tv-lg-webos/ko/articles/lg-developer-mode/)
