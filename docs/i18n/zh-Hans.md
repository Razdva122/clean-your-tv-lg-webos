# Clean Your TV — 用户指南

> v1.5.0：主题、展示页和电脑向电视传输。已知 Root 限制：Appearance 可能偏移 110 px；待机唤醒后 Home 可能不会自动打开。设备实机验证范围仍有限。 [1.5.0](../RELEASE-1.5.0.md).

> 下一候选版本（尚未发布）：固定布局主题保留隐藏 Columns 行的空间，以便 Apply 时保持 Appearance 的滚动位置。指针、键盘和无障碍导航会跳过隐藏的 Columns。实机电视验证尚待完成。

[文档导航](../README.md) · [报告问题](../FEEDBACK.md)

本指南适用于已发布的 **[1.5.2](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/tag/v1.5.2)**。C3 验收仅涵盖已记录的电源、Home、焦点、保持关闭状态及手动回滚测试。其他电视、eARC 音频和实体 Android 设备仍未验证；安装成功并不证明兼容。[测试范围（英文）](../RELEASE-1.4.0-ACCEPTANCE.md)。

**未发布的安装程序：**控制台、桌面和 Android 界面会分别显示电视检查状态：未检查、正在检查、通过、未通过或无法验证。出错后仍保留结果。Node.js/Python 检查针对电视的运行环境；`doctor` 不会准备 Python，也不会请求遥控配对。重试前请保存报告。

## 选择版本

No-root 和 Root 是适用于不同电视配置的同等选项。使用 LG 开发者模式请选择 No-root；已有 root SSH 访问请选择 Root。两种版本的兼容性与测试范围分别记录。

- **No-root：**启用 LG Developer Mode 和 Key Server，输入电视显示的口令，并单独接受电视配对请求。开发者模式必须保持有效；过期可能移除侧载应用。即使启用 Beta 自动续期，也要留意官方计时器。Helper 监控需要本地网络。
- **Root：**必须已有 root SSH 访问权限。安装程序不会为电视获取 root。已取得 root 的电视不要启用开发者模式。请保留 root 访问和恢复服务。

Root 需要可用的 Settings Service 和 System Profile Home 接口（`com.webos.service.systemprofile`）；仅有 root 权限并不能证明兼容性。

## 安装之前

安装期间保持电视开机，将电脑与电视连接到同一个可信本地网络。完成后无需电脑持续开机。兼容性取决于型号、固件和遥控器；Root 仍有待完成的实机检查。

Node 0.10.25 支持仅适用于尚未发布的源码/测试构建；已发布的安装程序仍要求 0.12.2+。参见[兼容性](../COMPATIBILITY.md)。

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

桌面向导自动选择系统语言，也可手动选择并保存。电视端在**设置 → 语言**中选择，或使用系统/自动选项。安装程序与电视偏好独立。完整代码见[语言索引](../LANGUAGES.md)。

单独下载的 macOS/Linux CLI，请在解压目录打开终端：

```sh
chmod +x cytv
./cytv --language zh-Hans install
```

选择电视（或输入 IP）、版本，然后检查摘要。仅在可信网络上为自己的电视接受首次 SSH 信任；保存的密钥发生改变时将阻止访问。Root 凭据与开发者模式口令不同。Root 会安装恢复功能并立即激活 Home，无试用或 Keep 步骤。请在自己的电视上检查方向键、OK、Home、返回/取消、音量、待机/唤醒和冷启动。

## 日常使用与恢复

方向键选择磁贴，OK 打开，按住 OK 调整顺序。短按返回保留应用本身的导航和退出确认。启用 Home 控制时，短按 Home 打开 Clean Your TV。按住返回 1.2 秒会临时打开 LG Home 一次，不改变 Home 控制开关和设置。

**两秒内按 Home 三次，每次都松开**，即可返回 LG Home 并停止 Home 控制，偏好设置保留。No-root Helper 0.6.13 及更早版本改为按住 Home 约两秒；按住 Home 不是 Root 的紧急退出方式。

No-root: 要重新启动 Home 控制，请打开 Home Helper，选择启动 Helper 并确认。已保存的主屏幕选择会保留。 Root：在 Home 设置中启用 **Change Home** 恢复。**Open LG Home** 只打开 LG Home 一次，不更改路由。要持续使用 LG Home，请关闭 **Change Home** 或运行 `cytv restore`。不要同时运行两种控制器。若故障重复出现，请保持 LG Home 启用。

> **仅限尚未发布的 1.5.3 候选版 — Root：**Root 状态正常时，明确开启 **更改 Home** 会创建 CYTV 自有的原生 **Clean** 输入项，并将记忆输入设为 Clean。关闭 Home 控制、紧急停止、故障、为更新暂停或卸载时，会删除 CYTV 自有项；仅当当前记忆值仍是 CYTV 设置的值时，才恢复原先的输入。其他输入和前台应用保持不变。不受支持的电视或非 CYTV 所有的输入项会继续使用现有的受保护 Home 控制。不保证 Clean 立即成为开机第一画面。一台 C3 的首屏实验已通过；待机、断电冷启动、关闭 Home 控制、更新和回滚的最终验证仍待完成。[候选版详情（英语）](../development/ROOT-NATIVE-INPUT.md)。

```sh
./cytv --language zh-Hans status
./cytv --language zh-Hans doctor --report
./cytv --language zh-Hans restore
./cytv --language zh-Hans uninstall
```

中断后重试前先运行 `status`，保留日志和恢复文件。`restore` 返回 LG Home 而不移除应用；`uninstall` 先恢复再移除。Root 恢复状态会特意保留，切勿删除它来强行重新安装。分享报告前请检查内容，不要公开密钥或配置文件夹。

仅适用于尚未发布的候选版本，两个版本均支持：打开 **Home 设置 → 外观 → 列数**，选择 1–8 列，或选择 **跟随主题** 使用主题的值（Classic 默认为 5 列）。手动选择的列数优先于主题。 固定布局的主题会隐藏列数选项并使用作者设定的值。切换到支持此设置的主题后，将恢复您保存的选择。 Alpine 候选预览中的应用位于一条循环横向列表中：左/右循环滚动，上键进入快捷按钮，下键返回同一应用。 在 Alpine 预览中，也可用鼠标滚轮或触控板滚动列表；对话框打开时不会滚动后面的 Home。

在两种版本的未发布候选版中，打开 **Home 设置 → 外观**，关闭 **显示“添加应用”按钮** 即可隐藏 +。默认开启。隐藏 + 后，仍可通过同一页面的 **添加应用** 添加或恢复应用。排序和隐藏功能保持可用，选择在重启后保留。即使隐藏所有应用，顶部按钮和设置仍可使用。

在尚未发布的候选版本主题预览中，若使用可选的侧边栏布局，上/下键选择菜单项，右键进入应用区域，在应用第一列按左键返回菜单。

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

1.5.0：替换包包含 System Updater 1.1.2。电视 OTA 前，请明确运行 `cytv replace-system-updater --edition root` 替换 1.1.0 或 1.1.1。只替换 System Updater，保留 Root/Root Updater 应用、完整配置和 Home 选择，并归档旧状态。结果不明或尚未完成的操作会阻止替换。此要求不限制 No-root 更新源。[替换流程（英文）](../RECOVERY.md#replace-the-root-system-updater-candidate)。

## 帮助与详细说明

操作失败或中断后，先检查状态并保存该次尝试的诊断报告。引导恢复会分别确认移除和重新安装。结果不确定时请停止，保留私有日志及恢复文件；切勿删除它们来强制重试。参阅[恢复（英文）](../RECOVERY.md)。求助时请提供型号、固件、版本类别、安装程序版本、失败步骤及预期/实际表现；分享前检查报告并删除秘密信息。

[文档导航](../README.md) · [报告问题](../FEEDBACK.md)

<!-- Anchors retained for links to earlier guide headings. -->
<a id="v110-起的可选-root-python"></a>
<a id="120-的-lg-固件更新阻止功能"></a>
<a id="130-新增功能"></a>
<a id="130-新增功能--12"></a>
<a id="未发布候选版通过-homebrew-设置-root"></a>
<a id="未发布候选版本hdmi-声音恢复root"></a>


## 主题：开发候选版本

在支持主题的候选版本中打开 **设置 → 主题**。**Classic** 和 **Alpine** 为内置主题，无需下载；默认仍为 Classic。**Channel** 是 showcase 中的外部主题。在主题展示试用时：选择后请在 **20 秒**内按 **保留主题**。选择 **还原**、按 Back 或等待超时会恢复之前的主题。未确认的试用被中断时，下次启动 Home 将恢复 Classic。 在已安装列表中选择内置或已下载主题会立即应用并保存，没有确认计时器。从电脑接收或通过 URL 安装的主题也如此。只有主题展示中的试用主题会启动 20 秒试用，已下载版本也一样。

已安装的主题显示在可横向滚动的单行列表中。当前主题始终排在第一位，其卡片会突出显示。使用左/右方向键浏览。

展示页仅显示此电视尚未安装的主题。Classic、Alpine 和已下载主题均会隐藏，即使目录中已有新版本。删除后主题会重新出现。更新请使用链接安装或从电脑接收。

主题卡片直接嵌入主题设置，与设置分类并排显示。展示目录、链接安装和电脑传输都在同一面板打开；只有展示目录中的试用会暂时显示 Home。

打开主题展示或选择刷新时，会从主项目仓库检查已审核的目录更新，无需更新 Home 或重新加载页面。正常合并后即可获取新条目；尚未合并的候选版本可能仍显示内置目录。离线或请求失败时使用内置条目和预览。内置主题与已安装的 Home 版本一致。打开 Channel 预览，选择**下载主题**（需要互联网）。下载后试用，并在 **20 秒**内选择保留主题。已安装主题可离线使用。仍可通过 URL 添加固定版本链接。

测试未发布主题时，先在电视打开**设置 → 主题 → 从电脑接收**。将电视显示的地址和六位 PIN 输入电脑预览中的 **Send to TV**，发送后在电视选择**应用主题**。主要方式由电脑主动连接电视 TCP **8879**，无需修改电脑防火墙。两台设备须在同一可信家庭网络。接收器在一次上传、取消、离开页面或 **10 分钟**后关闭。PIN 不会保存，安装后的主题可离线使用。无需发布到 GitHub。

安装已发布主题时，打开**通过 ID 添加**，输入 ID（例如 `102300a209`）、`da.gd/102300a209` 或完整 GitHub 链接。Home 会在加载前显示补全的 da.gd 地址，然后验证 GitHub 目标和主题包。作者可从版本说明或电脑预览的 **TV link → Copy ID** 复制 ID。

公开发布的软件包可能尚无这些选项。浏览器测试不等于实体电视兼容性验证。[完整指南](../THEMES.md)。

此未发布候选版在 Classic 和 Alpine 之外内置 **Ribbon**，无需下载主题。默认仍为 Classic。更新 Home 后，在设置 → 外观中选择 Ribbon。

尚未发布的可配置应用栏主题可将输入、Wi-Fi 和设置放在左下角。启用此导航时，在第一个可见应用上按左键依次选择设置、Wi-Fi 和输入；在设置上按右键返回同一可见应用。需要新 Home 功能的主题在不支持的版本上安装会被拒绝，当前外观和选择保持不变。请先更新 Home。之后降级可能在启动时恢复 Classic。

主题页面显示内置主题和您自行安装的所有主题预览，离线也可查看。单独的展示按钮打开已发布目录；个人安装不会发布主题。

外观包含显示当前数量的列数和应用设置。独立的主题分类包含已安装主题、主题展示、从电脑接收及右侧的通过 ID 添加（例如 102300a209）。选择 Classic 卡片可恢复；下载的主题可逐个删除。语言分类可直接选择语言。

浏览器预览中的“从电脑接收”说明电视上的操作，不会在电脑上启动电视接收器。请使用预览上方的 Send to TV。删除已下载主题需要确认；删除当前主题前会先恢复 Classic。取消会保留主题。

<a id="设置分类未发布候选版本"></a>

## 设置分类（1.5.0）

两个版本均在左侧显示分类，右侧显示所选设置：主屏幕、外观、主题、语言、软件更新及高级。No-root 还提供 Developer Mode；Root 的 LG 固件更新位于更新分类，HDMI 声音位于高级分类。上下键在当前列内移动，右键进入设置，左键返回分类。返回键先返回分类，再关闭设置。也可用 Tab 选择返回 Home 按钮。

软件更新分类及内部按钮上的黄色圆点表示有可用更新。成功检查确认没有更新后，两处圆点同时消失；检查失败时保留上次确认的状态。
