---
lang: zh-Hans
topic: lg-developer-mode
title: "No-root webOS 启动器与 LG 开发者模式"
description: "了解 Clean Your TV No-root 为什么需要 LG 开发者模式、会话过期如何影响侧载应用，以及启动器消失后该检查什么。"
updated: '2026-11-09'
---

LG 开发者模式允许你在不获取电视 root 权限的情况下安装和测试 webOS TV 应用。Clean Your TV No-root 使用这种访问方式，并配合电视端的 Home Helper 工作。开发者模式的会话有时限：请在 LG 的 Developer Mode 应用中查看剩余时间，并在过期前延长会话，以便继续使用侧载应用。

## 开发者模式提供什么？

开发者模式提供开发访问权限，并不提供 root 权限，也不保证 Home 键辅助工具能在所有型号上工作。Clean Your TV 仍会检查运行环境和输入方面的要求。普通商店应用、侧载应用与已获取 root 权限的系统使用不同的访问途径。

No-root 只能用于合适的开发者模式环境。如果电视已经拥有 root 权限，不要再在其上启用开发者模式。请先阅读 [Root 与 No-root 的比较](/clean-your-tv-lg-webos/zh-Hans/articles/root-vs-no-root/)和[兼容性要求](/clean-your-tv-lg-webos/zh-Hans/compatibility/)。

## 准备电视和安装设备

具体步骤请遵循[当前安装指南](/clean-your-tv-lg-webos/zh-Hans/install/)。你需要 LG 的 Developer Mode 应用、所需的 LG 开发者账户登录，以及用于配对的 Key Server。电视与电脑或受支持的 Android 设备应连接到可以互相通信的网络。即使两台设备都能上网，访客网络或客户端隔离仍可能阻止设置。

妥善保管配对密钥和连接信息，不要公开。请使用指南中链接的正式发布安装程序，不要把任意下载的 IPK 文件视为完整的 Home 键设置方案。安装完成后，启动器和 Helper 都在电视上运行，电脑可以关机。

## 保持会话有效

打开 LG 的 Developer Mode 应用，检查会话剩余时间，并在具备所需连接的情况下延长会话。应遵循 LG 当前的说明，不要依赖旧文章中写死的小时数。尝试续期不代表续期成功：操作后请再次检查显示的剩余时间。

Clean Your TV 提供可选的自动续期测试功能，默认关闭。即使启用，也应继续检查实际的开发者模式状态。它不会取消 LG 的会话要求，也不能让已关闭的模式永久有效。

## 启动器消失，或 Home 键打开 LG Home，怎么办？

反复重装之前，先检查开发者模式。LG 文档说明，关闭开发者模式或让会话过期可能会卸载开发应用。会话过期与 Home Helper 紧急停止、配对问题或安装中断是不同情况。

如果开发应用已被移除，请按文档恢复开发者模式，再根据实际状态使用安装程序的引导设置或恢复功能。如果应用仍在，但 Home 键路由已停止，请查看 [Home 键帮助](/clean-your-tv-lg-webos/zh-Hans/help/#home-button)。如果之前的操作中断，请使用[恢复指南](/clean-your-tv-lg-webos/zh-Hans/help/#interrupted)，不要删除系统文件。恢复后应单独验证 Home 键行为。

## 来源与后续阅读

- [LG：使用 Developer Mode 应用](https://webostv.developer.lge.com/develop/getting-started/developer-mode-app)
- [项目 No-root 安装指南](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/INSTALL.md)
- [项目恢复参考](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/RECOVERY.md)
