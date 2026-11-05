# Clean Your TV — 用户指南

> **1.8.2 — 未发布候选版本:** [1.8.2 / English](../RELEASE-1.8.2.md).

**尚未发布的 C1 Beta（#298）：** 在通用电脑安装程序中选择 Root。符合条件的 C1 电视会自动识别，无需单独的安装程序或标志。此路径需要全新安装，不支持自动更新，且尚未通过实体 C1 验收。打开 LG Home、长按 Back 或安全/电源停止后，Home 控制可能保持关闭；请在电视设置中重新开启更改 Home。常规 Root 路径保持不变。 如果仍有其他 No-root 组件，C1 完全移除会在更改前停止。请先通过常规 No-root 移除流程删除这些组件；状态未明确时请保留恢复数据。 [C1 Beta contract (English)](../development/C1-NATIVE-GATE.md).

尚未发布（#290）：**+ / 添加应用**仅在检测到已安装的调谐器时，以电视提供的名称列出直播电视。其他隐藏的系统应用仍不显示。No-root 需要更新后的 Helper 和安装程序；Root 需要更新后的 Home 软件包。频道启动仍需在电视上验证。

**未发布 — Home 中的 Ribbon：** 两个版本中的 Ribbon 都是唯一的全屏 Home 应用内的主题，使用自己的壁纸。卡片后方不显示其他视频或 HDMI。选择应用时使用电视正常的应用切换方式。应急控制保持不变。最终安装包和电视验收尚未完成。[Ribbon](../THEMES.md#ribbon-over-applications-unreleased)。

Ribbon：长按 OK 编辑；←/→ 移动卡片，↑ 选择 ×（从 Home 隐藏），↓ 返回卡片，OK 确认，Back 取消。编辑时保留当前背景。

**1.7.0 — Root 启动来源：** 在设置 → 您的 Home 屏幕中开启 **更改 Home**，即可设置 **优先打开 Clean Your TV**。**LG Channels / 直播电视**默认开启，**YouTube** 默认关闭。关闭更改 Home 后，两个开关仍可见但不可操作，已保存的值会保留。这些偏好私密保存在本电视上，不包含在可移植配置导出中。这些设置不代表已验证电视开机或唤醒行为。 关闭某个来源后，启动画面由电视固件决定，并不保证恢复到该来源。没有 HDMI 启动开关。[原生启动限制（英文）](../../root-edition/README.md#candidate-native-startup-choices)。

> 本指南介绍 1.7.0。请从 [GitHub Releases 中已发布的版本](https://github.com/Razdva122/clean-your-tv-lg-webos/releases)下载可用软件包。它包含安装程序的五项改进。重新打开 Root 设置时会读取实际状态，检查失败不会启用 Home。System Updater 1.2.0 用于符合条件的新安装，或经过验证的 1.1.0/1.1.1 替换。已安装的 1.1.2 保留原有通道，没有通用迁移方案。请保留恢复数据，不要强行替换。[版本与限制](../RELEASE-1.7.0.md)。

> v1.5.0：主题、展示页和电脑向电视传输。已知 Root 限制：Appearance 可能偏移 110 px；待机唤醒后 Home 可能不会自动打开。设备实机验证范围仍有限。 [1.5.0](../RELEASE-1.5.0.md).

> **1.5.4:** 固定布局主题保留隐藏 Columns 行的空间，以便 Apply 时保持 Appearance 的滚动位置。指针、键盘和无障碍导航会跳过隐藏的 Columns。

[文档导航](../README.md) · [报告问题](../FEEDBACK.md)

**1.5.4 历史测试记录:** C3 验收仅涵盖已记录的电源、Home、焦点、保持关闭状态及手动回滚测试。其他电视、eARC 音频和实体 Android 设备仍未验证；安装成功并不证明兼容。[测试范围（英文）](../history/2026-10-31-release-1.5.3-signed-root-qa.md)。

**1.5.4:**控制台、桌面和 Android 界面会分别显示电视检查状态：未检查、正在检查、通过、未通过或无法验证。出错后仍保留结果。Node.js/Python 检查针对电视的运行环境；`doctor` 不会准备 Python，也不会请求遥控配对。重试前请保存报告。

## 选择版本

No-root 和 Root 是适用于不同电视配置的同等选项。使用 LG 开发者模式请选择 No-root；已有 root SSH 访问请选择 Root。两种版本的兼容性与测试范围分别记录。

- **No-root：**启用 LG Developer Mode 和 Key Server，输入电视显示的口令，并单独接受电视配对请求。开发者模式必须保持有效；过期可能移除侧载应用。即使启用 Beta 自动续期，也要留意官方计时器。Helper 监控需要本地网络。
- **Root：**必须已有 root SSH 访问权限。安装程序不会为电视获取 root。已取得 root 的电视不要启用开发者模式。请保留 root 访问和恢复服务。

Root 需要可用的 Settings Service 和 System Profile Home 接口（`com.webos.service.systemprofile`）；仅有 root 权限并不能证明兼容性。

> **1.6.0:** Root 在准备专用 Python 或安装包之前检查必需的 Home 接口。检查失败会停止安装；通过检查并不能证明固件兼容或实体 Home 键正常。已知连接错误会显示针对性提示。请保留连接配置、信任记录和恢复数据；未完成的操作需要经过验证的恢复，不要盲目重试。保存并检查诊断报告。[详情](../development/INSTALLER-PREFLIGHT-HELP.md)。

## 安装之前

安装期间保持电视开机，将电脑与电视连接到同一个可信本地网络。完成后无需电脑持续开机。兼容性取决于型号、固件和遥控器；Root 仍有待完成的实机检查。

1.5.4 包含支持电视 Node.js **0.10.25+** 的 Home Helper **0.6.21**；Root 仍要求 Node.js **8+**。 [Compatibility](../COMPATIBILITY.md).

**未发布的 webOS 1.x 变更：**下个 No-root 安装程序在精确版本 Helper 测试后接受电视 Node.js **0.10.15+**；已发布的 1.7.1 安装程序仍要求 **0.10.25+**。这不代表旧版 WebKit、原生输入或 Home 兼容性已得到验证。请勿替换电视 runtime 或绕过检查。Root 仍要求 Node.js 8+。[测试与限制](../COMPATIBILITY.md#webos-1x-runtime-floor-unreleased)。

No-root Helper 需要电视 Node.js **0.10.25+**。Root 需要 Node.js **8+** 及可用的 Python **3.9+**。如有需要，安装程序会下载经验证的专用 Python；首次准备需要 **320 MiB** 可用空间。它不会替换系统 Python。请保留恢复功能引用的运行环境。[Python 说明（英文）](../OPTIONAL-PYTHON.md)。Developer Mode 自动续期为 **Beta，默认关闭**；无 root 电视上的实际续期尚未确认，请继续检查官方计时器。

### 设置 Developer Mode（No-root）

Developer Mode 让 CYTV 可以在没有 root 的电视上安装应用。

1. 在电视上打开 LG Apps，搜索并安装 Developer Mode。
2. 打开 Developer Mode 并登录 LG Developer 账号。如需注册，请访问 webostv.developer.lge.com。
3. 开启 Dev Mode Status。电视将重启，然后请重新打开 Developer Mode。
4. 开启 Key Server 并保持 Developer Mode 打开。将其中的 IP Address 填入 CYTV 的电视地址栏。
5. 输入电视上 Developer Mode 显示的六位 Passphrase，注意区分大小写。

请使用电视上的代码，而非 LG 账号密码。如未显示代码，请开启 Key Server。

配对是单独的步骤：电视提示时，请用遥控器允许 CYTV 连接。

请保持 Developer Mode 有效：计时结束前打开它，并在电视联网时按 EXTEND。过期后 LG 可能会删除这些应用。

## 安装与选择语言

- **Windows x64：**下载 `cytv-windows-x64-desktop.zip`，在资源管理器中选择“全部解压缩”，然后打开 `cytv-desktop/cytv-desktop.exe`。保留旁边的 `_internal` 文件夹。尚未配置 Windows 发布者签名。独立控制台为 `cytv-windows-x64.exe`；将其重命名为 `cytv.exe`，在 PowerShell 中用 `.\cytv.exe` 替换下方命令的 `./cytv`。
- **macOS 13+：**解压 `cytv-macos-arm64.zip`（Apple Silicon）或 `cytv-macos-x64.zip`（Intel），将 `cytv.app` 移到“应用程序”后打开。允许本地网络访问。若被阻止，仅对可信项目下载使用“隐私与安全性 → 仍要打开”；不要禁用 Gatekeeper。旧系统尚未验收。
- **Linux x64：**在 Ubuntu 22.04+、Debian 12+ 或 Mint 21+ 中，用图形软件包安装程序打开 `cytv-linux-x64.deb`，安装后从应用菜单启动 Clean Your TV。桌面库可能需要联网下载。不含 Linux ARM。独立 `cytv-linux-x64` 为 CLI；图形界面请使用 `.deb`。

[Android 安装程序（英文）](../../android/README.md)：在右上角选择语言。更新时不要卸载或清除数据。Android 7 / WebView 108 是最低要求，并非已验证的手机配置；验收使用 Android 15 ARM64 / WebView 124 模拟器。实体手机及真实手机到电视的恢复流程仍未验证。

**未发布的 Android 候选版本：**对于原始 Root 操作 `install / coordinator-submitted`，恢复选项审查可在明确确认后使用原始保存的配置和 SSH 主机密钥执行只读检查。请勿卸载应用、清除数据、替换配置或重复安装。仅使用维护者指定的已签名重建 APK；公开 APK 尚不包含此流程。[步骤与限制](../../android/README.md#interrupted-root-installation-inspection-unreleased)。

桌面向导自动选择系统语言，也可手动选择并保存。电视端在**设置 → 语言**中选择，或使用系统/自动选项。安装程序与电视偏好独立。完整代码见[语言索引](../LANGUAGES.md)。

单独下载的 macOS/Linux CLI，请在解压目录打开终端：

```sh
chmod +x cytv
./cytv --language zh-Hans install
```

选择电视（或输入 IP）、版本，然后检查摘要。仅在可信网络上为自己的电视接受首次 SSH 信任；保存的密钥发生改变时将阻止访问。Root 凭据与开发者模式口令不同。Root 会安装恢复功能并立即激活 Home，无试用或 Keep 步骤。请在自己的电视上检查方向键、OK、Home、返回/取消、音量、待机/唤醒和冷启动。

**1.6.0:** 安装程序分别显示软件包验证、启动状态及您对实体 Home 的观察。启动确认或 Helper 进程不能证明 Home 拦截功能。打开其他电视应用，短按一次 Home，然后选择观察到的结果；默认为**未测试／跳过**。`--yes` 不会代答，非交互安装将保留未测试状态。Home 失败或跳过不会撤销已安装的软件包，也不会开始重新安装。如需帮助，请保存本地报告；不会自动发布。其他控制、声音、待机及冷启动仍需分别测试。

## 日常使用与恢复

方向键选择磁贴，OK 打开，按住 OK 调整顺序。短按返回保留应用本身的导航和退出确认。启用 Home 控制时，短按 Home 打开 Clean Your TV。按住返回 1.2 秒会临时打开 LG Home 一次，不改变 Home 控制开关和设置。

**两秒内按 Home 三次，每次都松开**，即可返回 LG Home 并停止 Home 控制，偏好设置保留。No-root Helper 0.6.13 及更早版本改为按住 Home 约两秒；按住 Home 不是 Root 的紧急退出方式。

No-root: 要重新启动 Home 控制，请打开 Home Helper，选择启动 Helper 并确认。已保存的主屏幕选择会保留。 Root：在 Home 设置中启用 **Change Home** 恢复。**Open LG Home** 只打开 LG Home 一次，不更改路由。要持续使用 LG Home，请关闭 **Change Home** 或运行 `cytv restore`。不要同时运行两种控制器。若故障重复出现，请保持 LG Home 启用。

尚未发布的 Root 修复：关闭 Home 控制或选择 Open LG Home 后，LG Home 确认启动时会关闭 Root 窗口。Home 控制关闭时，仍可手动打开 Home Root 进入设置。

> **1.5.4 — Root:** Root 状态正常时，明确开启 **更改 Home** 会创建 CYTV 自有的原生 **Clean** 输入项，并将记忆输入设为 Clean。关闭 Home 控制、紧急停止、故障、为更新暂停或卸载时，会删除 CYTV 自有项；仅当当前记忆值仍是 CYTV 设置的值时，才恢复原先的输入。其他输入和前台应用保持不变。不受支持的电视或非 CYTV 所有的输入项会继续使用现有的受保护 Home 控制。不保证 Clean 立即成为开机第一画面。记录中的 C3 首屏、待机和断电冷启动检查已通过，但不保证所有设备兼容。更新/回滚后 Home 可能保持关闭（#202），设置可能显示旧状态（#206）：关闭并重新打开设置，明确开启“更改 Home”并等待 Clean 状态。 [1.5.4 QA (English)](../history/2026-10-31-release-1.5.3-signed-root-qa.md) · [Native input (English)](../development/ROOT-NATIVE-INPUT.md).

```sh
./cytv --language zh-Hans status
./cytv --language zh-Hans doctor --report
./cytv --language zh-Hans restore
./cytv --language zh-Hans uninstall
```

> **1.6.0 (#152):** 如果 Helper 停用请求被拒绝，No-root 恢复/卸载流程可使用经过验证的 SSH 停止方式。停止状态会保留；结果不确定时保留操作日志。请勿删除状态文件。仍需在 EF950V 实机上确认。 [#152](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/152)

> **1.6.0 (#201):** No-root 状态检查会保留中断的安装或卸载记录。文件匹配或应用缺失不能证明操作已完成。如果验证被拒绝，请停止并保留诊断；没有仅凭文件绕过验证的方法。 [#201](../RECOVERY.md#unreleased-uncertain-no-root-package-operations-201)

中断后重试前先运行 `status`，保留日志和恢复文件。`restore` 返回 LG Home 而不移除应用；`uninstall` 先恢复再移除。Root 恢复状态会特意保留，切勿删除它来强行重新安装。分享报告前请检查内容，不要公开密钥或配置文件夹。

打开 **Home 设置 → 外观 → 列数**，选择 1–8 列，或选择 **跟随主题** 使用主题的值（Classic 默认为 5 列）。手动选择的列数优先于主题。 固定布局的主题会隐藏列数选项并使用作者设定的值。切换到支持此设置的主题后，将恢复您保存的选择。 下载的 Alpine 主题中的应用位于一条循环横向列表中：左/右循环滚动，上键进入快捷按钮，下键返回同一应用。 在 Alpine 中，也可用鼠标滚轮或触控板滚动列表；对话框打开时不会滚动后面的 Home。

1.5.4: **Home 设置 → 外观**，关闭 **显示“添加应用”按钮** 即可隐藏 +。默认开启。隐藏 + 后，仍可通过同一页面的 **添加应用** 添加或恢复应用。排序和隐藏功能保持可用，选择在重启后保留。即使隐藏所有应用，顶部按钮和设置仍可使用。

1.7.0: 所选主题决定使用顶部的 **输入源** 菜单还是 HDMI 磁贴栏；没有全局位置设置或 **在 Home 上显示输入源** 开关。磁贴栏目前仅支持 `dock-grid`。Liquid Glass 选择磁贴栏；Classic 和没有此选项的主题保留顶部菜单。从程序坞按上键进入磁贴栏，再按上键进入顶部按钮；下键或返回键回到程序坞，OK 打开输入源。存在输入源磁贴时，磁贴栏会替代顶部输入源菜单。设备名称仅来自固件提供的 输入元数据；否则，已连接的输入源显示 **已连接**。Home 不会编造 PlayStation 名称，也不保证 CEC 识别。空端口仍可选择。预览**默认开启**；之前明确保存的关闭设置会保留。关闭 **Home 设置 → 外观 → 预览所选输入源** 即可停用。仅在预览开启且所选主题使用磁贴栏时，已连接的 HDMI 在停留约 0.8 秒后可显示预览。在部分电视上，HDMI 预览可能播放声音或开启 HDR，无法保证静音。Home 不会自动更改电视的全局静音或 HDR 设置。电视直播和空端口保持静态磁贴。 Root 通过自身服务读取输入状态。No-root 在允许时保留直接 EIM；权限被拒绝后，通过已配对的 Helper 发出只读请求。读取失败时状态保持未知；没有新增控制项或配对提示。

在1.5.4主题预览中，若使用可选的侧边栏布局，上/下键选择菜单项，右键进入应用区域，在应用第一列按左键返回菜单。

No-root 1.5.0：从待机唤醒后，Helper 可尝试恢复临时 watchdog 超时，十分钟内最多五次。Stop 和连按三次 Home 后仍需手动启动 Helper；反复失败会保持停止状态。尚待电视实机验收。[行为与限制（英语）](../HELPER-DIAGNOSTICS.md#watchdog-recovery-unpublished-candidate-155)。

## 更新与移除

保留已知可用的安装包和私有设置备份。电脑辅助替换 No-root 安装包时，先停止 Helper，然后直接更新；卸载可能清除设置。移除桌面应用不会移除电视应用。不要用独立 IPK 替换正在运行的 Root 环境；请使用 cytv 的明确恢复/重新安装流程。

打开 Home 设置 → 软件更新，确认前检查提供的版本。即使使用 No-root 版本，在电视上更新和回滚也需要 **root、Homebrew Channel** 以及事先准备好的配套更新基础设施。无 root 电视请用电脑安装程序。完整系统更新的准备是单独明确执行的操作，参阅[更新（英文）](../UPDATES.md)。恢复界面显示保存的回滚版本；回滚可能丢失之后的设置更改。

**现有 1.3.0 安装：**原有 System Updater 可能拒绝基础设施变更。请保留中断操作，遵循 1.5.0+ 文档中的已验证恢复与替换准备流程；不要清除日志或盲目重试。仅更新应用不会替换固定的 Root 基础设施。[迁移与恢复（英文）](../UPDATES.md#one-time-computer-preparation)。

Home 设置通信修复已在 1.5.0 发布。请使用配套的已发布安装程序同时更新 Home 和 Helper；仅更新 Home 不会更改 Helper。验证范围仍限于已记录的机型。 [#146](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/146).

Root HDMI 声音恢复是实验功能，**默认关闭**，仅在需要时自行启用。它可能中断正常音频，并不证明 eARC 兼容性。[声音恢复（英文）](../development/ROOT-AUDIO-RECOVERY.md)。独立的 **Homebrew CYTV Installer 尚未发布**；请使用已发布的电脑或 Android 安装程序。

Homebrew Channel 拒绝此安装程序访问。在 webOS 11 上，Homebrew 0.7.3 需要开发者提供兼容性更新。在受支持的 Homebrew 版本包含此修复前，请使用已发布的电脑或 Android 安装程序。 [#116](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/116).

1.5.0+: 如果旧 Root 目录的可写权限导致固件 API 访问被拒绝，可显式运行 `cytv enable-firmware-access --edition root --repair-package-permissions`。该命令先用可信的私有软件包记录验证当前文件，再仅移除 Root 自有路径的组及其他用户写权限。遇到未知或已修改文件就停止；保留个人配置、Home 选择和固件屏蔽设置。[修复详情（英文）](../LG-FIRMWARE-UPDATES.md#explicit-package-permission-repair-candidate)。

1.5.0+: `cytv recover-system-rollback --edition root` 仅用于已验证的 Root 回滚：所有软件包安装程序均已完成，但启动器就绪等待超时。必须由真实启动器发送就绪信号；安装结果不明时拒绝恢复。保留软件包、固定代码和密钥、失败证据及明确关闭的 Home 控制状态，并以私有记录保存有时限的尝试。 普通重试不会延长时限。仅在之前的 120 秒到期、没有已接受的就绪信号且不存在不明安装结果后，才可用 `--new-recovery-attempt` 按 UUID/哈希归档完整旧记录，并明确开始新尝试。已完成的恢复不会重新开始，也不会自动连续重试。 [流程与限制（英文）](../RECOVERY.md#root-system-rollback-readiness-candidate)。

1.6.0：System Updater 1.2.0 用于符合条件的新安装，或通过 `cytv replace-system-updater --edition root` 对 1.1.0/1.1.1 进行经过验证的替换。只替换 System Updater，保留 Root/Root Updater 应用、完整配置和 Home 选择，并归档旧状态。未知或未完成的操作会阻止替换。已安装的 1.1.2 保持固定并使用旧通道；没有通用迁移方案，请勿强行替换。这不会限制 No-root 更新源。 [替换流程（英文）](../RECOVERY.md#replace-the-root-system-updater-candidate)

## 帮助与详细说明

**1.6.0:** 为同一台已保存的电视选择**检查恢复选项**，或运行 `cytv recover`。检查和更改需要分别确认，默认为“否”；`--yes` 不会批准。Root 仅在现有验证通过后继续。No-root 仅在现有软件包服务检查允许时提供删除选项；删除可能重置 Home 偏好设置。不会自动开始新的安装。状态未知或访问被拒绝时，请保存报告并停止；保留日志，不要重复删除。#201 的完成证据以及 #216 的实际电视恢复仍未确认。 [Recovery](../RECOVERY.md). 求助时请提供型号、固件、版本类别、安装程序版本、失败步骤及预期/实际表现；分享前检查报告并删除秘密信息。

1.7.0: 如果原始日志能证明 No-root 删除在首次软件包请求前停止，恢复可在没有全局软件包状态权限的情况下继续。请单独确认删除，验证删除完成后再单独开始安装。结果未知或已发送的操作仍会阻止继续；保留已保存的连接和日志。1.6.0 不含此更改。[详情](../RECOVERY.md#no-root-removal-stopped-before-package-submission-unreleased)。

[文档导航](../README.md) · [报告问题](../FEEDBACK.md)

开发中：如果尚未发送软件包移除请求，移除失败后可为同一已保存的电视选择“查看恢复选项”。检查与移除仍需分别确认。如果电视拒绝软件包状态检查，恢复会停止并提供报告。`recovery` 摘要区分尚未开始的移除、继承的操作和中断的软件包操作，不公开完整日志，也不能作为恢复授权。

<!-- Anchors retained for links to earlier guide headings. -->
<a id="v110-起的可选-root-python"></a>
<a id="120-的-lg-固件更新阻止功能"></a>
<a id="130-新增功能"></a>
<a id="130-新增功能--12"></a>
<a id="未发布候选版通过-homebrew-设置-root"></a>
<a id="未发布候选版本hdmi-声音恢复root"></a>

<a id="主题-154"></a>

## 主题

在下一版本预览中，**Home 设置 → 壁纸**显示当前主题壁纸、检测到的电视能力和当前模式。自动模式选择兼容画质；仅当主题包含相应资源时才可选择 4K、1080p 或图片。视频播放失败时会回退到图片。调暗程度每次调整 5%，也可恢复主题默认设置。Classic 和无壁纸主题会明确显示无壁纸状态。

下一版本预览的个人壁纸：在桌面 CYTV 中打开“壁纸”，选择 JPG/PNG、调整裁剪，并输入 Home 设置显示的电视局域网地址及接收 PIN。CYTV 在本地生成无声视频；只有裁剪后的原图分辨率足够时才提供 4K。在电视选择从 CYTV 接收或手机上传，并用同一 Wi-Fi 的手机扫描二维码。手机发送的是最高 1920×1080 的普通图片，不使用原生 4K 视频层；清晰度受电视界面分辨率限制。发送前确认提示，然后在电视预览并应用。个人上传会保留，可在壁纸设置中重新选择或删除。取消或文件被拒绝时会保留原背景。需要匹配的下一版本 Home/服务与 CYTV 构建。

自选动态视频（下一版本预览）：在桌面 CYTV → 壁纸中选择 MP4/MOV/MKV/WebM，时长 1–60 秒，最大 512 MiB、3840×2160。声音会被移除，画面居中裁剪为 16:9。较小视频转换为兼容的 1080p 输出；只有原始裁剪尺寸足够时才生成 UHD。使用电视地址/PIN 发送，然后在电视上预览并应用。手机上传仍仅支持 JPG/PNG。最终软件包验证和实体电视测试尚未完成。

下一版本的内置壁纸：**Home 设置 → 壁纸 → 内置壁纸 → Black Hole**。视频作者为 **Xecutioner**，获准在注明作者的前提下非商业使用。确认其他主题时会启用该主题自己的壁纸；Black Hole 和个人上传仍可重新选择。连续 4K 流避免每次循环回到文件开头，并提供兼容视频或图片作为后备。

Android CYTV: **设置电视** · **壁纸** · **维护**. 在电视上打开 Home 设置 → 壁纸 → 从手机上传。用手机相机扫描二维码，选择 JPG/PNG，然后在电视上应用。 手机上传：最高 1920×1080 的图片，不支持原生 4K 视频。真正的 4K 请使用电脑版 CYTV。

1.7.0: **设置 → 主题**。**Classic**, **Liquid Glass**, **Ribbon** 为内置主题，无需下载；默认仍为 Classic。**Channel** 是 showcase 中的外部主题。在主题展示试用时：选择后请在 **20 秒**内按 **保留主题**。选择 **还原**、按 Back 或等待超时会恢复之前的主题。未确认的试用被中断时，下次启动 Home 将恢复 Classic。 在已安装列表中选择内置或已下载主题会立即应用并保存，没有确认计时器。从电脑接收或通过 URL 安装的主题也如此。只有主题展示中的试用主题会启动 20 秒试用，已下载版本也一样。

1.7.0：**Classic**、**Liquid Glass** 和 **Ribbon** 为内置主题。**Alpine 1.4.4** 移至 **主题展示**，需要下载。已保存的 `builtin:alpine` 选择会回退到 Classic，并显示现有的恢复提示；Home 不会自动下载 Alpine，也不会将其替换为 Liquid Glass。 版本 1.6.0 包含 Classic、Alpine 和 Ribbon。

已安装的主题显示在可横向滚动的单行列表中。当前主题始终排在第一位，其卡片会突出显示。使用左/右方向键浏览。

展示页仅显示此电视尚未安装的主题。Classic、Liquid Glass, Ribbon 和已下载主题均会隐藏，即使目录中已有新版本。删除后主题会重新出现。更新请使用链接安装或从电脑接收。

主题卡片直接嵌入主题设置，与设置分类并排显示。展示目录、链接安装和电脑传输都在同一面板打开；只有展示目录中的试用会暂时显示 Home。

打开主题展示或选择刷新时，会从主项目仓库检查已审核的目录更新，无需更新 Home 或重新加载页面。正常合并后即可获取新条目；尚未合并的候选版本可能仍显示内置目录。离线或请求失败时使用内置条目和预览。内置主题与已安装的 Home 版本一致。打开 Channel 预览，选择**下载主题**（需要互联网）。下载后试用，并在 **20 秒**内选择保留主题。已安装主题可离线使用。仍可通过 URL 添加固定版本链接。

测试未发布主题时，先在电视打开**设置 → 主题 → 从电脑接收**。将电视显示的地址和六位 PIN 输入电脑预览中的 **Send to TV**，发送后在电视选择**应用主题**。主要方式由电脑主动连接电视 TCP **8879**，无需修改电脑防火墙。两台设备须在同一可信家庭网络。接收器在一次上传、取消、离开页面或 **10 分钟**后关闭。PIN 不会保存，安装后的主题可离线使用。无需发布到 GitHub。

安装已发布主题时，打开**通过 ID 添加**，输入 ID（例如 `102300a209`）、`da.gd/102300a209` 或完整 GitHub 链接。Home 会在加载前显示补全的 da.gd 地址，然后验证 GitHub 目标和主题包。作者可从版本说明或电脑预览的 **TV link → Copy ID** 复制 ID。

**1.6.0:** Home Helper 面板中的**显示诊断信息**会显示其自身状态请求的简短过滤结果。查看不会启动 Helper，也不会更改 Home 控制。仅在被要求时分享已检查的 JSON；[详情](../HELPER-DIAGNOSTICS.md#candidate-panel-caller-diagnostics-207)。

[Themes (English)](../THEMES.md) · [1.5.4 QA (English)](../history/2026-10-31-release-1.5.3-signed-root-qa.md).

1.5.4 中的可配置应用栏主题可将输入、Wi-Fi 和设置放在左下角。启用此导航时，在第一个可见应用上按左键依次选择设置、Wi-Fi 和输入；在设置上按右键返回同一可见应用。需要新 Home 功能的主题在不支持的版本上安装会被拒绝，当前外观和选择保持不变。请先更新 Home。之后降级可能在启动时恢复 Classic。

主题页面显示内置主题和您自行安装的所有主题预览，离线也可查看。单独的展示按钮打开已发布目录；个人安装不会发布主题。

外观包含显示当前数量的列数和应用设置。独立的主题分类包含已安装主题、主题展示、从电脑接收及右侧的通过 ID 添加（例如 102300a209）。选择 Classic 卡片可恢复；下载的主题可逐个删除。语言分类可直接选择语言。

浏览器预览中的“从电脑接收”说明电视上的操作，不会在电脑上启动电视接收器。请使用预览上方的 Send to TV。删除已下载主题需要确认；删除当前主题前会先恢复 Classic。取消会保留主题。

<a id="设置分类未发布候选版本"></a>

## 设置分类（1.5.0）

两个版本均在左侧显示分类，右侧显示所选设置：主屏幕、外观、主题、语言、软件更新及高级。No-root 还提供 Developer Mode；Root 的 LG 固件更新位于更新分类，HDMI 声音位于高级分类。上下键在当前列内移动，右键进入设置，左键返回分类。返回键先返回分类，再关闭设置。也可用 Tab 选择返回 Home 按钮。

软件更新分类及内部按钮上的黄色圆点表示有可用更新。成功检查确认没有更新后，两处圆点同时消失；检查失败时保留上次确认的状态。

<a id="自动图形分辨率候选版本"></a>

## 自动图形分辨率(1.6.0)

1.6.0 的电脑/Android 安装程序和已迁移的 OTA 客户端会根据电视报告的能力选择 720p 或 1080p。无法验证时，操作会停止。独立安装的旧更新程序需要按文档通过电脑迁移；恢复过程保留原始软件包。

[HD/FHD details (English)](../development/HOME-GRAPHICS-RESOLUTION.md#automatic-selection-and-ota).

> **1.6.0:** 请保留最初失败尝试的报告。新报告将已记录的首次错误与后续检查区分开，并提供经过筛选的 Doctor/状态摘要。安装、状态检查或恢复成功后也可导出报告。缺失的历史证据仍标为未知；报告不授予恢复操作权限。 [↗](../development/INSTALLER-DIAGNOSTICS.md).
