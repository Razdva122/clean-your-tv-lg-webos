# Clean Your TV — 用户指南

Clean Your TV 为 LG webOS 提供个人主屏幕：按自己的顺序排列应用，此菜单没有推广内容行。使用电脑或 Android 手机安装，设置完成后即可关闭电脑。

## 1. 下载安装程序

点击适合设备的图片。按钮下载最新已发布版本。Mac 请选择 Apple Silicon（M1 或更新）或 Intel，可在 Apple 菜单 → 关于本机中查看。

[![下载 — Windows x64](../../assets/brand/downloads/windows.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-windows-x64-desktop.zip)
[![下载 — macOS Apple Silicon](../../assets/brand/downloads/macos-arm64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-arm64.zip)
[![下载 — macOS Intel](../../assets/brand/downloads/macos-x64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-x64.zip)
[![下载 — Linux x64](../../assets/brand/downloads/linux.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-linux-x64.deb)
[![下载 — Android ARM64](../../assets/brand/downloads/android.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-android-arm64.apk)

<a id="选择版本"></a>

<a id="安装之前"></a>

## 2. 选择版本

打开电视，将电视与电脑或手机连接到同一家庭网络。出现提示时，允许 CYTV 访问本地网络。

- **No-root** — 电视没有 root 权限时选择。按下方步骤设置 Developer Mode。
- **Root** — 已有 SSH root 访问权限时选择。安装程序不会为电视获取 root。请勿在此电视上开启 Developer Mode；保留 SSH 访问和恢复数据。

### 设置 Developer Mode（No-root）

Developer Mode 让 CYTV 可以在没有 root 的电视上安装应用。

1. 在电视上打开 LG Apps，搜索并安装 Developer Mode。
2. 打开 Developer Mode 并登录 LG Developer 账号。如需注册，请访问 [LG Developer](https://webostv.developer.lge.com)。
3. 开启 Dev Mode Status。电视将重启，然后请重新打开 Developer Mode。
4. 开启 Key Server 并保持 Developer Mode 打开。将其中的 IP Address 填入 CYTV 的电视地址栏。
5. 输入电视上 Developer Mode 显示的六位 Passphrase，注意区分大小写。

请使用电视上的代码，而非 LG 账号密码。如未显示代码，请开启 Key Server。

配对是单独的步骤：电视提示时，请用遥控器允许 CYTV 连接。

请保持 Developer Mode 有效：计时结束前打开它，并在电视联网时按 EXTEND。过期后 LG 可能会删除这些应用。

<a id="安装与选择语言"></a>

## 3. 打开安装程序

- **Windows x64：**下载 `cytv-windows-x64-desktop.zip`，在资源管理器中选择“全部解压缩”，然后打开 `cytv-desktop/cytv-desktop.exe`。保留旁边的 `_internal` 文件夹。
- **macOS 13+：**解压 `cytv-macos-arm64.zip`（Apple Silicon）或 `cytv-macos-x64.zip`（Intel），将 `cytv.app` 移到“应用程序”后打开。允许本地网络访问。若被阻止，仅对可信项目下载使用“隐私与安全性 → 仍要打开”；不要禁用 Gatekeeper。
- **Linux x64：**在 Ubuntu 22.04+、Debian 12+ 或 Mint 21+ 中，用图形软件包安装程序打开 `cytv-linux-x64.deb`，安装后从应用菜单启动 Clean Your TV。桌面库可能需要联网下载。不含 Linux ARM。

**Android ARM64：**需要 Android 7+、WebView/Chrome 108+ 的 64 位 ARM 手机。打开下载的 APK，按 Android 提示允许从该来源安装。打开 CYTV，在右上角选择语言。更新时不要卸载应用或清除数据。

桌面向导自动选择系统语言，也可手动选择并保存。电视端在**设置 → 语言**中选择，或使用系统/自动选项。安装程序与电视偏好独立。完整代码见[语言索引](../LANGUAGES.md)。

## 4. 安装到电视

1. 在 CYTV 中选择**设置我的电视**。电脑端选择搜索到的电视；Android 端输入电视 IP 地址。如果搜索未找到电视，请手动输入地址。
2. 选择 **No-root** 或 **Root**，继续前确认电视是否正确。
3. No-root：输入 Developer Mode 的代码并在电视上允许连接。Root：使用现有 SSH 凭据。仅在可信网络中为自己的电视确认新 SSH 身份。如果已保存的密钥发生变化，请停止并检查原因。
4. 按向导提示操作。完成前保持电视开启，不要切换网络或关闭 CYTV。不要强行停止 Android 应用。Root 在准备好恢复后立即启用 Home 控制。

## 5. 检查遥控器

1. 在电视上打开另一个应用，短按一次 **Home**。应打开 Clean Your TV。在向导中填写实际看到的结果；未测试时请跳过。
2. 检查方向键、OK、返回、音量和声音。分别测试待机唤醒及断电后的启动。安装成功本身不会验证这些操作。

<a id="日常使用与恢复"></a>

## 6. 日常使用与恢复

方向键选择磁贴，OK 打开，按住 OK 调整顺序。短按返回保留应用本身的导航和退出确认。启用 Home 控制时，短按 Home 打开 Clean Your TV。按住返回 1.2 秒会临时打开 LG Home 一次，不改变 Home 控制开关和设置。

**两秒内按 Home 三次，每次都松开**，即可返回 LG Home 并停止 Home 控制，偏好设置保留。

No-root: 要重新启动 Home 控制，请打开 Home Helper，选择启动 Helper 并确认。已保存的主屏幕选择会保留。 Root：在 Home 设置中启用 **更改 Home（Change Home）** 恢复。**打开 LG Home（Open LG Home）** 只打开 LG Home 一次，不更改路由。要持续使用 LG Home，请关闭 **更改 Home（Change Home）**。不要同时运行两种控制器。若故障重复出现，请保持 LG Home 启用。

## 需要帮助？

安装中断后，请使用原先保存的连接，先选择**检查电视状态**。仅通过向导提供的恢复操作继续。如果状态未知，请保存诊断报告并停止；保留恢复数据，不要盲目重复安装。

恢复期间请保持 Home 控制关闭，保留原始诊断报告和已保存的连接。检查与更改须分别确认。请按照适用于已安装版本的详细恢复说明操作；不要强制重新安装或清除恢复状态。

求助时请提供电视型号、固件、No-root 或 Root、安装设备、出错步骤和错误消息。共享报告前移除密码、密钥、地址和个人信息。报告不会自动公开。

[报告问题](../FEEDBACK.md) · [详细恢复说明（英文）](../RECOVERY.md) · [更新或卸载（英文）](../MAINTENANCE.md) · [其他语言](../LANGUAGES.md)

在后续构建中，只有主题支持且已开启输入源预览，并且选择或正在播放 4K 时，才会显示此提示和“关闭 HDMI 预览”按钮。 HDMI 预览期间，4K 视频壁纸会暂时切换为 1080p 静态图片。关闭输入源预览可让壁纸保持 4K。

### 候选版本：简单移除

上方按钮仍提供已发布版本。在下一个候选版本中，请使用同一保存的电视连接，在维护中选择**卸载 Clean Your TV**。确认一次后，移除实际存在的已知项目应用和文件，跳过不存在的项目；部分安装后也可使用。

出现提示时，请断开电视电源后重新连接，等待网络恢复，然后选择**重试**。待机或 Quick Start 不等于完全重启；CYTV 不会自动重启电视。连接中断时，请检查连接并重试同一移除目标，无需另一个恢复向导。访问被拒绝时，请使用要求的 Root 连接；电视忙碌时，请稍候再试。只有验证最终清理后才显示成功。请保留密钥和原始报告。上述紧急控制及分享同意要求仍有效。

<!-- Legacy anchors retained for existing links. Detailed references: -->
<a id="v110-起的可选-root-python"></a>
<a id="120-的-lg-固件更新阻止功能"></a>
<a id="130-新增功能"></a>
<a id="130-新增功能--12"></a>
<a id="未发布候选版通过-homebrew-设置-root"></a>
<a id="未发布候选版本hdmi-声音恢复root"></a>
<a id="主题-154"></a>
<a id="设置分类未发布候选版本"></a>
<a id="自动图形分辨率候选版本"></a>
<a id="更新与移除"></a>
<a id="帮助与详细说明"></a>
<a id="主题"></a>
<a id="设置分类150"></a>
<a id="自动图形分辨率160"></a>
<a id="存储空间"></a>

详细英文参考：[要求](../COMPATIBILITY.md) · [遥控器](../CONTROLS.md) · [主题](../THEMES.md) · [更新](../UPDATES.md)。

> 未发布候选版本：实验性 Root Home 根据 Qt SDK 6–9 的能力检查选择，不使用型号列表。硬件兼容性及普通 OTA 尚未验证。其他 Home 集成保持不变；安全停止或电源停止后，须明确重新启用 Home 控制。 [#364](../development/C1-NATIVE-GATE.md#unpublished-capability-based-compositor-admission-364).
