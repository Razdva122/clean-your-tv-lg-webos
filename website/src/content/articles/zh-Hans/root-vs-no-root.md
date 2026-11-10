---
lang: zh-Hans
topic: root-vs-no-root
title: "LG webOS 启动器：Root 与 No-root 如何选择"
description: "为 LG webOS 电视选择合适的 Clean Your TV 版本，在安装前比较访问权限、开发者模式维护、Home 键控制和恢复方式。"
updated: '2026-11-09'
---

如果 LG 电视使用开发者模式，请选择 No-root。只有电视已经拥有可用的 root 权限和兼容服务时，才选择 Root。两个 Clean Your TV 版本提供相同的主屏幕界面，安装后都在电视上运行。安装程序不会获取 root 权限，也不会刷写固件。

## No-root 有哪些要求？

No-root 在设置时使用 LG 开发者模式、Key Server 和本地配对。Home Helper 在电视上运行，并在设备和固件支持时处理 Home 键。日常使用不需要一直开着电脑或手机。

需要持续维护的是开发者模式：请在会话过期前延长有效期。LG 提醒，通过开发者模式安装的应用可能在模式关闭或会话过期后被移除。项目的自动续期选项是可选的测试功能，默认关闭，不应把它当作保证。使用此版本前，请阅读[开发者模式指南](/clean-your-tv-lg-webos/zh-Hans/articles/lg-developer-mode/)。

## Root 有哪些要求？

Root 使用现有的 root SSH 访问权限、兼容的电视服务，以及受支持的输入和运行环境功能。仅有 root 权限并不能证明兼容。安装程序会检查环境；不要绕过未通过的前提条件，也不要通过替换系统运行环境强行通过检查。

Root 使用独立的软件包和 Home 键路由方式。不要在现有的 root 环境上启用开发者模式，使用 Root 路由前应停止 No-root Home Helper。选择版本是根据已经具备的访问权限来决定，而不是选择一个能为电视获取 root 权限的按钮。

## 维护和恢复有什么不同？

- **日常使用：** 两个版本都在电视上运行，通过启动器使用应用和主题。
- **No-root 维护：** 保持开发者模式有效，并保留 Helper 所需的配对与连接条件。
- **Root 维护：** 保持独立恢复服务及其所需运行环境可用。能否更新取决于已安装版本和受支持的更新途径；仅有 root 权限不会启用 OTA。
- **紧急退出：** 当前受支持的版本使用两秒内短按 Home 键三次。Home Helper 0.6.13 及更早版本则使用长按两秒。

紧急停止后，必须主动操作才能重新启动持续路由。No-root 需打开 Home Helper 并选择 Start Helper；Root 需在 Home 设置中使用 Change Home。请参阅[版本比较](/clean-your-tv-lg-webos/zh-Hans/editions/)和[恢复帮助](/clean-your-tv-lg-webos/zh-Hans/help/#home-button)。

## 安装前检查电视

准备好准确的型号、固件、webOS 和遥控器信息，再阅读[兼容性页面](/clean-your-tv-lg-webos/zh-Hans/compatibility/)。实测结果对应特定配置。设置后请分别测试 Home 键、应用启动、声音、待机和冷启动。软件包能安装，不代表所有功能都能正常工作。

使用[正式发布的安装程序和安装指南](/clean-your-tv-lg-webos/zh-Hans/install/)。如果已有可用配置并打算切换版本，请按照文档中的迁移和移除步骤操作，不要将一个版本直接覆盖安装到另一个版本上。

## 来源与后续阅读

- [项目版本比较](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [项目要求与已知限制](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/COMPATIBILITY.md)
- [更换主屏幕带来的变化](/clean-your-tv-lg-webos/zh-Hans/articles/change-lg-webos-home-screen/)
