# Clean Your TV — 用户指南

仅限 Root Edition：在安装程序的最后一页设置 Home 主屏幕名称。留空可保留当前名称。命令行使用 `--tv-name`。

尚未发布的安装程序变更：新安装前，电脑安装程序会检查 GitHub 上是否有更新的稳定版本。选择“打开 GitHub 并下载最新版本”会停止当前安装并打开下载页面；选择“不，安装此版本”才会明确继续。检查失败时仍可继续。未完成的操作和恢复流程会跳过检查。

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

对于 Root，安装程序会检查并选择可用的 Home 控制方式。如果无法确认兼容性，安装将停止；请勿绕过失败的检查。

如果安装程序提供 **No-root** 选项，可以使用现有的 root SSH 连接继续。此选项无需 Developer Mode。

**No-root → Root:** 如果在完整移除后重新安装了 No-root，切换到 Root 前可能需要先清理。请备份 Home 偏好设置，使用已保存的 Root 连接选择**卸载 Clean Your TV**，并等待移除验证完成。这也会移除 No-root Home 和 Helper。然后安装 Root；请保留恢复记录。

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

如果无法读取电视输入但应用列表有效，Root 安装将显示警告并继续。Home 中可能缺少输入；应用列表读取失败或为空时，安装仍会停止。如果警告持续出现，请保存诊断报告。

## 5. 检查遥控器

1. 在电视上打开另一个应用，短按一次 **Home**。应打开 Clean Your TV。在向导中填写实际看到的结果；未测试时请跳过。
2. 检查方向键、OK、返回、音量和声音。分别测试待机唤醒及断电后的启动。安装成功本身不会验证这些操作。

如果 Helper 未停止，No-root 设置会在验证软件包后开启 Home。停止后，请在电视上选择启动 Helper。之后可以在设置中关闭 Home。

请使用原来保存的连接和恢复数据。如果已丢失，请重新连接同一台电视并选择卸载 Clean Your TV。设置前先完成经过验证的卸载；不要删除预留文件。如果卸载停止，请保存诊断报告。

<a id="日常使用与恢复"></a>

## 6. 日常使用与恢复

要固定 HDMI 输入源，请在 **+ / 添加应用** 中选择它。按 OK 切换到该输入源。长按 OK 可移动或隐藏磁贴。

如果安装程序显示“Root 设置尚未完成，但电视上缺少部署记录。”： 选择“查看恢复选项”以移除 Clean Your TV，然后单独开始设置。完整移除也会移除 No-root Home 和 Helper；请先备份偏好设置。

No-root 红外遥控支持：短按并松开 Home 后，计划在约 700 毫秒后打开 Clean；LG Home 可能先短暂出现。长按 Home 仍由 webOS 处理，连按三次仍会停止 Helper。普通 Developer Mode 电视上的访问能力尚未验证；请勿更改输入设备权限。

方向键选择磁贴，OK 打开，按住 OK 调整顺序。短按返回保留应用本身的导航和退出确认。启用 Home 控制时，短按 Home 打开 Clean Your TV。按住返回 1.2 秒会临时打开 LG Home 一次，不改变 Home 控制开关和设置。

**两秒内按 Home 三次，每次都松开**，即可返回 LG Home 并停止 Home 控制，偏好设置保留。

No-root: 要重新启动 Home 控制，请打开 Home Helper，选择启动 Helper 并确认。已保存的主屏幕选择会保留。 Root：在 Home 设置中启用 **更改 Home（Change Home）** 恢复。**打开 LG Home（Open LG Home）** 只打开 LG Home 一次，不更改路由。要持续使用 LG Home，请关闭 **更改 Home（Change Home）**。不要同时运行两种控制器。若故障重复出现，请保持 LG Home 启用。

电视上的自动更新不会重新启动已停止的 Helper。如需单独恢复，请使用启动 Helper；不要删除停止文件。

## 需要帮助？

重置或更改 SSH 后若出现 `ssh-identity-changed`，请停止：CYTV 在登录前阻止了已保存密钥的变化。首次信任提示不能替换原密钥；待处理的卸载并不能解释密钥不匹配。请保留原有连接配置、密钥和恢复记录。如果已保存的 Root 配置中有待处理的卸载，可以在控制台记录经独立验证的指纹。原卸载操作仍会被阻止。请参阅[SSH 身份变更恢复](../RECOVERY.md#ssh-identity-changed)。

安装中断后，请使用原先保存的连接，先选择**检查电视状态**。仅通过向导提供的恢复操作继续。如果状态未知，请保存诊断报告并停止；保留恢复数据，不要盲目重复安装。

恢复期间请保持 Home 控制关闭，保留原始诊断报告和已保存的连接。检查与更改须分别确认。请按照适用于已安装版本的详细恢复说明操作；不要强制重新安装或清除恢复状态。

求助时请提供电视型号、固件、No-root 或 Root、安装设备、出错步骤和错误消息。共享报告前移除密码、密钥、地址和个人信息。报告不会自动公开。

[报告问题](../FEEDBACK.md) · [详细恢复说明（英文）](../RECOVERY.md) · [更新或卸载（英文）](../MAINTENANCE.md) · [其他语言](../LANGUAGES.md)

### 简单移除

请使用同一保存的电视连接，在维护中选择**卸载 Clean Your TV**。确认一次后，移除实际存在的已知项目应用和文件，跳过不存在的项目；部分安装后也可使用。

在没有独立 LG Home 应用的旧款电视上，移除 No-root 时可能会切换到直播电视。请保持电视开启，并按提示重新启动；不要删除恢复数据或重置电视。

出现提示时，请断开电视电源后重新连接，等待网络恢复，然后选择**重试**。待机或 Quick Start 不等于完全重启；CYTV 不会自动重启电视。连接中断时，请检查连接并重试同一移除目标，无需另一个恢复向导。访问被拒绝时，请使用要求的 Root 连接；电视忙碌时，请稍候再试。只有验证最终清理后才显示成功。请保留密钥和原始报告。上述紧急控制及分享同意要求仍有效。

如果安装程序无法确认所要求的完全重启，请保存并附上诊断报告。保留已保存的连接和恢复数据。不要反复断电，也不要手动清除未完成的操作。

在安装失败或中断后直接提供恢复入口。如果 No-root 无法继续，请确认一次完整移除。遇到临时断线或 CYTV 进程忙碌时，移除最多自动尝试三次。如果需要 Root 权限，请为同一台电视选择 **通过 Root 连接**；经验证的 Root 清理也会完成该电视被阻止的 No-root 移除。Root 激活失败时，程序尝试恢复并验证 LG Home，不会重复激活。取消未完成的操作会保留诊断报告和恢复操作。紧急停止状态保持不变。

删除过程中连接失败时，可打开连接详情，检查网络或选择现有 Root SSH 私钥后重试。电视地址、版本类型、端口和主机密钥验证保持固定。重新安装 No-root 时，安装向导会尝试自动停止 Helper。仅在提示时按 Home，然后确认重新检查。确认电视控制已恢复、自动启动已关闭、软件包、文件和运行进程均不存在且没有未完成安装后，卸载可无需重启即可完成。如果安装程序要求重启，请完成重启后重试。输入服务故障时仍可继续安全清理软件包，但只有确认输入快捷方式也已清理后才会显示成功。

**重新安装 Root：**使用保存的连接，选择**设置我的电视 → Root**，并确认**重新安装 Root？**。安装程序会恢复 LG Home，并完整删除 Clean Your TV，包括其更新程序、Home Helper 和已保存的偏好设置。确认删除完成后，会安装并激活此安装程序内的软件包和 Root 运行环境。电视上的其他应用和现有 root/SSH 访问权限会保留。如果删除停止或要求完全重启，请先完成删除，再重新开始设置。单独选择**卸载 Clean Your TV**绝不会启动新安装。

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

<a id="未发布候选版本unreleased电视上的旧版-nodejs"></a>
<a id="电视上的旧版-nodejs已随-v1120-发布"></a>
<a id="简单移除v1110"></a>

## 使用设置

用 ↑ ↓ 选择分类，再按 → 或 OK 进入。← 返回分类；返回键先回到分类，再关闭设置。重新进入分类时，焦点返回上次可用的控件。“列数”中的方向键对应三列网格。“语言”会聚焦当前选中的语言。

如果 No-root 无法读取 Home 状态，请选择重试。控件不可用不代表 Home 控制已关闭。在壁纸中可从手机或 CYTV 上传图片；有可用壁纸时才显示画质和调暗选项。删除个人壁纸需要确认；取消会保留壁纸。

## 天气

打开设置中壁纸下方的天气。开启天气后，在城市中手动搜索并确认地区和国家，或选择自动，根据网络连接估算城市。VPN 可能影响结果；如果未找到城市或结果不正确，请手动搜索。已识别或选择的城市会显示在设置中。选择 °C / m/s 或 °F / mph，以及可用的简洁、当前、详细或四天预报格式。预览会采用当前主题；“示例”表示演示数据。Liquid Glass 仅支持简洁格式。Ribbon 和 Atmosphere 不显示天气。关闭天气会停止请求，并隐藏城市、单位和格式选项；仍可选择数据源。连接中断时，近期数据可能暂时保留；数据过旧后，天气会隐藏，直到成功刷新。

选择预报来源：Auto、MET Norway 或 Open-Meteo。Auto 先尝试 MET Norway，失败时尝试一次 Open-Meteo，之后复用上次成功的来源和缓存。手动选择的来源不会自动切换。新设置默认使用 Auto；以前保存且未指定来源的设置保留 Open-Meteo。设置中会显示实际来源。可用性取决于网络。MET 刷新间隔至少三小时，缓存最长保留六小时。缺少的字段会隐藏：MET 不提供体感温度或降水概率。每日范围汇总预报时点的数据，并非实测极值。

预报坐标发送至 api.met.no 或 api.open-meteo.com，城市搜索发送至 geocoding-api.open-meteo.com。可选的自动定位会向 get.geojs.io 发送公网 IP。连接使用 HTTPS，无需 API 密钥。位置、来源和缓存保存在电视上。“数据来源”包含服务条款和署名，包括挪威气象研究所（MET Norway，CC BY 4.0）。

点击天气标题旁的“数据来源”可查看服务和许可信息。

## 从iPhone上传壁纸

打开设置 → 壁纸 → 从手机上传并扫描二维码。选择JPG、PNG或HEIC/HEIF，裁剪、确认画质限制后发送，再在电视上选择应用。Safari使用原生HEIC支持；Chrome、Firefox等现代浏览器会在需要时使用内置的本地解码器。转换在手机上完成，不使用外部服务。取消或选择其他文件会停止转换。输入上限为32 MiB和5000万像素，输出最高为1080p和2 MiB。转换失败时请换一张照片或使用JPG/PNG。此功能适用于手机页面，不适用于Mac应用。

## 设置你的 Clean Your TV

选择主题前，在 **Debloat** 中选择要更改的 LG 广告、推荐、隐私和通知设置，并逐项查看结果。如果安装程序无法读取原始值，就无法保存该值以供自动恢复。选择**跳过 Debloat**可保留当前设置。

安装成功后，选择 Classic、Liquid Glass 或 Ribbon，并开启或关闭主屏幕天气。Ribbon 不支持天气；Liquid Glass 使用简短格式。城市根据网络连接估算，可在 Home 设置中更改。

Developer Mode 的 No-root 提供自动续期（测试版）；请继续检查官方计时器。通过现有 root SSH 新安装 No-root 时，设置中会隐藏 Developer Mode 标签页。Root 可通过 Homebrew Channel 阻止 LG 固件更新，包括安全更新；需要通过 Homebrew Channel 真正重启电视。CYTV 更新单独管理。

选择“保留当前设置”可跳过自定义。开关显示模式功能当前的开启或关闭状态。未更改的设置会保留。重新安装 Root 仍会按上文说明删除 CYTV 设置。请在电视上检查外观；重试前请在 Home 设置中检查未确认的选项。
