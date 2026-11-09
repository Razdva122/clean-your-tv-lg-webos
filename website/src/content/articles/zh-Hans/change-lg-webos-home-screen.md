---
lang: zh-Hans
topic: change-lg-webos-home-screen
title: "如何更换 LG webOS 电视的主屏幕"
description: "使用 Clean Your TV 自定义 LG webOS 主屏幕，了解启动器能改变什么、如何选择版本，以及安装前需要检查的事项。"
updated: '2026-11-09'
---

Clean Your TV 是 LG webOS 电视的替代主屏幕。你可以按自己的习惯排列应用，选择主题，并自定义程序坞。完成设置后，它直接在电视上运行，电脑可以关机。能否接管 Home 键取决于电视、固件、遥控器和安装方式。

## 可以自定义哪些内容？

启动器改变的是查找和打开电视应用的界面。你可以整理常用应用，并选择 Classic、Liquid Glass 或 Ribbon 等布局。安装前可通过[浏览器演示](/clean-your-tv-lg-webos/demo/)比较布局。演示中的电视操作是模拟的，无法测试与你家电视的兼容性。

替代启动器不会更换 webOS 固件、解锁付费流媒体，也不会移除其他应用内的广告。画面设置、输入源和流媒体服务仍是电视的独立部分。如果你主要想让主屏幕更清爽，请阅读[广告方面有哪些变化](/clean-your-tv-lg-webos/zh-Hans/articles/lg-tv-home-screen-ads/)。

## 应该选择哪种安装方式？

已启用 LG 开发者模式的电视应使用 No-root。电视端的 Home Helper 会在受支持的环境中处理 Home 键。开发者模式必须保持启用；会话过期可能导致侧载应用被移除。

只有电视已经拥有可用的 root 权限，且满足运行环境和服务要求时，才应使用 Root。Clean Your TV 安装程序不会为电视获取 root 权限。不要在现有的 root 环境上启用开发者模式，也不要同时运行两种 Home 键路由方式。[版本指南](/clean-your-tv-lg-webos/zh-Hans/articles/root-vs-no-root/)说明了两者的取舍。

## 更改现有设置前

1. 记录准确的型号、固件、webOS 版本和遥控器类型，并与[要求及电视实测记录](/clean-your-tv-lg-webos/zh-Hans/compatibility/)对照。每份报告只适用于其记录的配置。
2. 按照[安装指南](/clean-your-tv-lg-webos/zh-Hans/install/)操作，使用其中链接的正式发布安装程序。设置期间，电视和安装设备应处于能够互相通信的网络中。
3. 设置后先检查应用启动和 Home 键，再分别检查声音、待机与唤醒，以及完全关机后的冷启动。软件包安装成功并不等于这些行为都已验证。

## 如何返回 LG Home？

当前受支持的版本使用两秒内短按 Home 键三次来触发紧急退出。Home Helper 0.6.13 及更早版本则需要长按 Home 键两秒。临时打开一次 LG Home 与停用持续的 Home 键路由是两件事，请按照已安装版本对应的[恢复说明](/clean-your-tv-lg-webos/zh-Hans/help/#home-button)操作。更改启动行为之前，先确保有可用的恢复途径。

## 来源与后续阅读

- [项目版本与按键操作参考](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [项目安装说明与前提条件](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/INSTALL.md)
- [开发者模式：让 No-root 配置保持可用](/clean-your-tv-lg-webos/zh-Hans/articles/lg-developer-mode/)
