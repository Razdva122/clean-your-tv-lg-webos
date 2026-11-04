# Clean Your TV — 使用者指南

**1.7.0 — Root 啟動來源：** 在設定 → 您的 Home 畫面中開啟 **變更 Home**，即可設定 **優先開啟 Clean Your TV**。**LG Channels / 直播電視**預設開啟，**YouTube** 預設關閉。關閉變更 Home 後，兩個開關仍可見但無法操作，已儲存的值會保留。這些偏好私密儲存在本電視上，不包含在可攜設定檔匯出中。這些設定不代表已驗證電視開機或喚醒行為。 關閉某個來源後，啟動畫面由電視韌體決定，並不保證恢復到該來源。沒有 HDMI 啟動開關。[原生啟動限制（英文）](../../root-edition/README.md#candidate-native-startup-choices)。

> 本指南介紹 1.7.0。請從 [GitHub Releases 中已發布的版本](https://github.com/Razdva122/clean-your-tv-lg-webos/releases)下載可用套件。它包含安裝程式的五項改進。重新開啟 Root 設定時會讀取實際狀態，檢查失敗不會啟用 Home。System Updater 1.2.0 用於符合條件的新安裝，或經過驗證的 1.1.0/1.1.1 替換。已安裝的 1.1.2 保留原有通道，沒有通用遷移方案。請保留復原資料，勿強制替換。[版本與限制](../RELEASE-1.7.0.md)。

> v1.5.0：主題、展示頁與電腦向電視傳輸。已知 Root 限制：Appearance 可能偏移 110 px；待機喚醒後 Home 可能不會自動開啟。裝置實機驗證範圍仍有限。 [1.5.0](../RELEASE-1.5.0.md).

> **1.5.4:** 固定版面主題保留隱藏 Columns 列的空間，以便 Apply 時維持 Appearance 的捲動位置。指標、鍵盤和無障礙導覽會略過隱藏的 Columns。

[文件導覽](../README.md) · [回報問題](../FEEDBACK.md)

**1.5.4 歷史測試紀錄:** C3 驗收僅涵蓋已記錄的電源、Home、焦點、保持關閉狀態及手動回復版本測試。其他電視、eARC 音訊和實體 Android 裝置仍未驗證；安裝成功不代表相容。[測試範圍（英文）](../history/2026-10-31-release-1.5.3-signed-root-qa.md)。

**1.5.4:**主控台、桌面與 Android 介面會分別顯示電視檢查狀態：未檢查、正在檢查、通過、未通過或無法驗證。出錯後仍保留結果。Node.js/Python 檢查針對電視的執行環境；`doctor` 不會準備 Python，也不會要求遙控配對。重試前請儲存報告。

## 選擇版本

No-root 和 Root 是適用於不同電視組態的同等選項。使用 LG 開發者模式請選擇 No-root；已有 root SSH 訪問請選擇 Root。兩種版本的兼容性與測試範圍分別記錄。

- **No-root：**啟用 LG Developer Mode 和 Key Server，輸入電視顯示的口令，並單獨接受電視配對請求。開發者模式必須保持有效；過期可能移除側載應用。即使啟用 Beta 自動續期，也要留意官方計時器。Helper 監控需要本地網路。
- **Root：**必須已有 root SSH 訪問權限。安裝程式不會為電視獲取 root。已取得 root 的電視不要啟用開發者模式。請保留 root 訪問和恢復服務。

Root 需要可用的 Settings Service 和 System Profile Home 介面（`com.webos.service.systemprofile`）；僅有 root 權限並不能證明相容性。

> **1.6.0:** Root 在準備專用 Python 或安裝套件之前檢查必要的 Home 介面。檢查失敗會停止安裝；通過檢查並不能證明韌體相容或實體 Home 鍵正常。已知連線錯誤會顯示專屬提示。請保留連線設定、信任記錄和復原資料；未完成的操作需要經過驗證的復原，請勿盲目重試。儲存並檢查診斷報告。[詳情](../development/INSTALLER-PREFLIGHT-HELP.md)。

## 安裝之前

安裝期間保持電視開機，將電腦與電視連線到同一個可信本地網路。完成後無需電腦持續開機。兼容性取決於型號、固件和遙控器；Root 仍有待完成的實機檢查。

1.5.4 包含支援電視 Node.js **0.10.25+** 的 Home Helper **0.6.21**；Root 仍要求 Node.js **8+**。 [Compatibility](../COMPATIBILITY.md).

**未發布的 webOS 1.x 變更：**下個 No-root 安裝程式在精確版本 Helper 測試後接受電視 Node.js **0.10.15+**；已發布的 1.7.1 安裝程式仍要求 **0.10.25+**。這不代表舊版 WebKit、原生輸入或 Home 相容性已獲驗證。請勿替換電視 runtime 或略過檢查。Root 仍要求 Node.js 8+。[測試與限制](../COMPATIBILITY.md#webos-1x-runtime-floor-unreleased)。

No-root Helper 需要電視 Node.js **0.10.25+**。Root 需要 Node.js **8+** 及可用的 Python **3.9+**。如有需要，安裝程式會下載經驗證的專用 Python；首次準備需要 **320 MiB** 可用空間。它不會取代系統 Python。請保留復原功能引用的執行環境。[Python 說明（英文）](../OPTIONAL-PYTHON.md)。Developer Mode 自動續期為 **Beta，預設關閉**；無 root 電視上的實際續期尚未確認，請繼續檢查官方計時器。

### 設定 Developer Mode（No-root）

Developer Mode 讓 CYTV 可以在沒有 root 的電視上安裝應用程式。

1. 在電視上開啟 LG Apps，搜尋並安裝 Developer Mode。
2. 開啟 Developer Mode 並登入 LG Developer 帳號。如需註冊，請前往 webostv.developer.lge.com。
3. 開啟 Dev Mode Status。電視將重新啟動，之後請再次開啟 Developer Mode。
4. 開啟 Key Server 並保持 Developer Mode 開啟。將其中的 IP Address 填入 CYTV 的電視位址欄。
5. 輸入電視上 Developer Mode 顯示的六位 Passphrase，注意區分大小寫。

請使用電視上的代碼，而非 LG 帳號密碼。如未顯示代碼，請開啟 Key Server。

配對是獨立步驟：電視提示時，請用遙控器允許 CYTV 連線。

請保持 Developer Mode 有效：計時結束前開啟它，並在電視連網時按 EXTEND。過期後 LG 可能會刪除這些應用程式。

## 安裝與選擇語言

- **Windows x64：**下載 `cytv-windows-x64-desktop.zip`，在資源管理器中選擇“全部解壓縮”，然後打開 `cytv-desktop/cytv-desktop.exe`。保留旁邊的 `_internal` 資料夾。尚未組態 Windows 發佈者簽名。獨立主控台為 `cytv-windows-x64.exe`；將其重命名為 `cytv.exe`，在 PowerShell 中用 `.\cytv.exe` 替換下方指令的 `./cytv`。
- **macOS 13+：**解壓 `cytv-macos-arm64.zip`（Apple Silicon）或 `cytv-macos-x64.zip`（Intel），將 `cytv.app` 移到“應用程式”後打開。允許本地網路訪問。若被阻止，僅對可信項目下載使用“隱私與安全性 → 仍要打開”；不要禁用 Gatekeeper。舊系統尚未驗收。
- **Linux x64：**在 Ubuntu 22.04+、Debian 12+ 或 Mint 21+ 中，用圖形軟體包安裝程式打開 `cytv-linux-x64.deb`，安裝後從應用菜單啟動 Clean Your TV。桌面庫可能需要聯網下載。不含 Linux ARM。獨立 `cytv-linux-x64` 為 CLI；圖形界面請使用 `.deb`。

[Android 安裝程式（英文）](../../android/README.md)：在右上角選擇語言。更新時不要解除安裝或清除資料。Android 7 / WebView 108 是最低需求，並非已驗證的手機設定；驗收使用 Android 15 ARM64 / WebView 124 模擬器。實體手機及真實手機到電視的復原流程仍未驗證。

**未發布的 Android 候選版本：**對於原始 Root 操作 `install / coordinator-submitted`，復原選項檢視可在明確確認後使用原始儲存的設定檔和 SSH 主機金鑰執行唯讀檢查。請勿解除安裝應用程式、清除資料、替換設定檔或重複安裝。僅使用維護者指定的已簽署重建 APK；公開 APK 尚未包含此流程。[步驟與限制](../../android/README.md#interrupted-root-installation-inspection-unreleased)。

桌面精靈會自動選擇系統語言，也可手動選擇並儲存。電視端在**設定 → 語言**中選擇，或使用系統/自動選項。安裝程式與電視偏好各自獨立。完整代碼見[語言索引](../LANGUAGES.md)。

單獨下載的 macOS/Linux CLI，請在解壓目錄打開終端：

```sh
chmod +x cytv
./cytv --language zh-Hant install
```

選擇電視（或輸入 IP）、版本，然後檢查摘要。僅在可信網路上為自己的電視接受首次 SSH 信任；儲存的密鑰發生改變時將阻止訪問。Root 憑據與開發者模式口令不同。Root 會安裝恢復功能並立即啟用 Home，無試用或 Keep 步驟。請在自己的電視上檢查方向鍵、OK、Home、返回/取消、音量、待機/喚醒和冷啟動。

**1.6.0:** 安裝程式分別顯示套件驗證、啟動狀態及您對實體 Home 的觀察。啟動確認或 Helper 程序不能證明 Home 攔截功能。開啟其他電視應用程式，短按一次 Home，然後選擇觀察到的結果；預設為**未測試／略過**。`--yes` 不會代答，非互動安裝將保留未測試狀態。Home 失敗或略過不會撤銷已安裝的套件，也不會開始重新安裝。如需協助，請儲存本機報告；不會自動發布。其他控制、聲音、待機及冷啟動仍需分別測試。

## 日常使用與恢復

方向鍵選擇圖塊，OK 打開，按住 OK 調整順序。短按返回保留應用本身的導航和退出確認。啟用 Home 控制時，短按 Home 打開 Clean Your TV。按住返回 1.2 秒會臨時打開 LG Home 一次，不改變 Home 控制開關和設定。

**兩秒內按 Home 三次，每次都鬆開**，即可返回 LG Home 並停止 Home 控制，偏好設定保留。No-root Helper 0.6.13 及更早版本改為按住 Home 約兩秒；按住 Home 不是 Root 的緊急退出方式。

No-root: 要重新啟動 Home 控制，請開啟 Home Helper，選擇啟動 Helper 並確認。已儲存的主畫面選擇會保留。 Root：在 Home 設定中啟用 **Change Home** 恢復。**Open LG Home** 只打開 LG Home 一次，不更改路由。要持續使用 LG Home，請關閉 **Change Home** 或執行 `cytv restore`。不要同時執行兩種控制器。若故障重復出現，請保持 LG Home 啟用。

> **1.5.4 — Root:** Root 狀態正常時，明確開啟 **變更 Home** 會建立 CYTV 自有的原生 **Clean** 輸入項目，並將記憶輸入設為 Clean。關閉 Home 控制、緊急停止、故障、為更新暫停或解除安裝時，會刪除 CYTV 自有項目；僅當目前記憶值仍是 CYTV 設定的值時，才還原先前的輸入。其他輸入與前景應用程式維持不變。不支援的電視或非 CYTV 所有的輸入項目會繼續使用既有的受保護 Home 控制。不保證 Clean 立即成為開機第一個畫面。紀錄中的 C3 首畫面、待機與斷電冷啟動檢查已通過，但不保證所有裝置相容。更新/回復版本後 Home 可能維持關閉（#202），設定可能顯示舊狀態（#206）：關閉並重新開啟設定，明確開啟「變更 Home」並等待 Clean 狀態。 [1.5.4 QA (English)](../history/2026-10-31-release-1.5.3-signed-root-qa.md) · [Native input (English)](../development/ROOT-NATIVE-INPUT.md).

```sh
./cytv --language zh-Hant status
./cytv --language zh-Hant doctor --report
./cytv --language zh-Hant restore
./cytv --language zh-Hant uninstall
```

> **1.6.0 (#152):** 如果 Helper 停用請求遭拒，No-root 復原/解除安裝流程可使用經過驗證的 SSH 停止方式。停止狀態會保留；結果不確定時保留操作記錄。請勿刪除狀態檔案。仍需在 EF950V 實機上確認。 [#152](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/152)

> **1.6.0 (#201):** No-root 狀態檢查會保留中斷的安裝或解除安裝記錄。檔案相符或應用程式不存在，不能證明操作已完成。如果驗證遭拒，請停止並保留診斷；沒有僅憑檔案繞過驗證的方法。 [#201](../RECOVERY.md#unreleased-uncertain-no-root-package-operations-201)

中斷後重試前先執行 `status`，保留日誌和恢復檔案。`restore` 返回 LG Home 而不移除應用；`uninstall` 先恢復再移除。Root 恢復狀態會特意保留，切勿刪除它來強行重新安裝。分享報告前請檢查內容，不要公開密鑰或組態資料夾。

開啟 **Home 設定 → 外觀 → 欄數**，選擇 1–8 欄，或選擇 **跟隨主題** 使用主題的值（Classic 預設為 5 欄）。手動選擇的欄數優先於主題。 固定版面的主題會隱藏欄數選項並使用作者設定的值。切換到支援此設定的主題後，將恢復您儲存的選擇。 下載的 Alpine 主題中的應用程式位於一條循環橫向清單中：左/右循環捲動，上鍵進入快捷按鈕，下鍵返回同一應用程式。 在 Alpine 中，也可用滑鼠滾輪或觸控板捲動清單；對話框開啟時不會捲動後方的 Home。

1.5.4: **Home 設定 → 外觀**，關閉 **顯示「新增應用程式」按鈕** 即可隱藏 +。預設開啟。隱藏 + 後，仍可透過同一頁面的 **新增應用程式** 新增或恢復應用程式。排序和隱藏功能保持可用，選擇會在重新啟動後保留。即使隱藏所有應用程式，頂部按鈕和設定仍可使用。

1.7.0: 所選主題決定使用頂部的 **輸入源** 選單或 HDMI 磚塊列；沒有全域位置設定或 **在 Home 上顯示輸入源** 開關。磚塊列目前僅支援 `dock-grid`。Liquid Glass 選擇磚塊列；Classic 和沒有此選項的主題保留頂部選單。從 Dock 按上鍵進入磚塊列，再按上鍵進入頂部按鈕；下鍵或返回鍵回到 Dock，OK 開啟輸入源。有輸入源磚塊時，磚塊列會取代頂部輸入源選單。裝置名稱僅來自韌體提供的 輸入中繼資料；否則，已連接的輸入源顯示 **已連接**。Home 不會編造 PlayStation 名稱，也不保證 CEC 識別。空連接埠仍可選擇。預覽**預設開啟**；先前明確儲存的關閉設定會保留。關閉 **Home 設定 → 外觀 → 預覽所選輸入來源** 即可停用。僅在預覽開啟且所選主題使用磚塊列時，已連接的 HDMI 在停留約 0.8 秒後可顯示預覽。在部分電視上，HDMI 預覽可能播放聲音或開啟 HDR，無法保證靜音。Home 不會自動變更電視的全域靜音或 HDR 設定。電視直播和空連接埠保持靜態磚塊。 Root 透過自身服務讀取輸入狀態。No-root 在允許時保留直接 EIM；權限被拒絕後，透過已配對的 Helper 發出唯讀請求。讀取失敗時狀態保持未知；沒有新增控制項或配對提示。

在1.5.4主題預覽中，若使用可選的側邊欄配置，上／下鍵選擇選單項目，右鍵進入應用程式區域，在應用程式第一欄按左鍵返回選單。

No-root 1.5.0：從待機喚醒後，Helper 可嘗試恢復暫時的 watchdog 逾時，十分鐘內最多五次。Stop 和連按三次 Home 後仍需手動啟動 Helper；反覆失敗會保持停止狀態。尚待電視實機驗收。[行為與限制（英語）](../HELPER-DIAGNOSTICS.md#watchdog-recovery-unpublished-candidate-155)。

## 更新與移除

保留已知可用的安裝套件和私有設定備份。電腦輔助替換 No-root 安裝套件時，先停止 Helper，然後直接更新；解除安裝可能清除設定。移除桌面應用不會移除電視應用。不要用獨立 IPK 替換正在執行的 Root 環境；請使用 cytv 的明確恢復/重新安裝流程。

開啟 Home 設定 → 軟體更新，確認前檢查提供的版本。即使使用 No-root 版本，在電視上更新和回復版本也需要 **root、Homebrew Channel** 以及事先準備好的配套更新基礎設施。無 root 電視請用電腦安裝程式。完整系統更新的準備是單獨明確執行的操作，請參閱[更新（英文）](../UPDATES.md)。復原介面顯示儲存的回復版本；回復可能遺失之後的設定變更。

**現有 1.3.0 安裝：**原有 System Updater 可能拒絕基礎設施變更。請保留中斷操作，遵循 1.5.0+ 文件中的已驗證復原與替換準備流程；不要清除記錄或盲目重試。僅更新應用程式不會取代固定的 Root 基礎設施。[遷移與復原（英文）](../UPDATES.md#one-time-computer-preparation)。

Home 設定通訊修正已在 1.5.0 發布。請使用配套的已發布安裝程式同時更新 Home 和 Helper；僅更新 Home 不會變更 Helper。驗證範圍仍限於已記錄的機型。 [#146](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/146).

Root HDMI 聲音復原是實驗功能，**預設關閉**，僅在需要時自行啟用。它可能中斷正常音訊，並不證明 eARC 相容性。[聲音復原（英文）](../development/ROOT-AUDIO-RECOVERY.md)。獨立的 **Homebrew CYTV Installer 尚未發佈**；請使用已發佈的電腦或 Android 安裝程式。

Homebrew Channel 拒絕此安裝程式存取。在 webOS 11 上，Homebrew 0.7.3 需要開發者提供相容性更新。在受支援的 Homebrew 版本包含此修正前，請使用已發布的電腦或 Android 安裝程式。 [#116](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/116).

1.5.0+: 若舊 Root 目錄的可寫入權限導致韌體 API 存取遭拒，可明確執行 `cytv enable-firmware-access --edition root --repair-package-permissions`。指令會先以可信的私人套件記錄驗證目前檔案，再僅移除 Root 自有路徑的群組及其他使用者寫入權限。遇到未知或已修改檔案便停止；保留個人設定、Home 選擇和韌體封鎖設定。[修復詳情（英文）](../LG-FIRMWARE-UPDATES.md#explicit-package-permission-repair-candidate)。

1.5.0+: `cytv recover-system-rollback --edition root` 僅用於已驗證的 Root 回復版本：所有套件安裝程式均已完成，但啟動器就緒等待逾時。必須由真正的啟動器傳送就緒訊號；安裝結果不明時拒絕恢復。保留套件、固定程式碼和金鑰、失敗證據及明確關閉的 Home 控制狀態，並以私人記錄保存有時限的嘗試。 一般重試不會延長時限。僅在先前的 120 秒到期、沒有已接受的就緒訊號且不存在不明安裝結果後，才可用 `--new-recovery-attempt` 按 UUID/雜湊封存完整舊記錄，並明確開始新嘗試。已完成的恢復不會重新開始，也不會自動連續重試。 [流程與限制（英文）](../RECOVERY.md#root-system-rollback-readiness-candidate)。

1.6.0：System Updater 1.2.0 用於符合條件的新安裝，或透過 `cytv replace-system-updater --edition root` 對 1.1.0/1.1.1 進行經過驗證的替換。只替換 System Updater，保留 Root/Root Updater 應用程式、完整設定和 Home 選擇，並封存舊狀態。未知或未完成的操作會阻止替換。已安裝的 1.1.2 保持固定並使用舊通道；沒有通用遷移方案，請勿強制替換。這不會限制 No-root 更新來源。 [替換流程（英文）](../RECOVERY.md#replace-the-root-system-updater-candidate)

## 說明與詳細指引

**1.6.0:** 為同一台已儲存的電視選擇**檢查復原選項**，或執行 `cytv recover`。檢查和變更需要分別確認，預設為「否」；`--yes` 不會批准。Root 僅在現有驗證通過後繼續。No-root 僅在現有套件服務檢查允許時提供移除選項；移除可能重設 Home 偏好設定。不會自動開始新的安裝。狀態不明或存取遭拒時，請儲存報告並停止；保留日誌，不要重複移除。#201 的完成證據以及 #216 的實際電視復原仍未確認。 [Recovery](../RECOVERY.md). 求助時請提供型號、韌體、版本類別、安裝程式版本、失敗步驟及預期/實際表現；分享前檢查報告並刪除機密資訊。

1.7.0: 如果原始日誌能證明 No-root 移除在首次套件請求前停止，復原可在沒有全域套件狀態權限的情況下繼續。請單獨確認移除，驗證移除完成後再單獨開始安裝。結果不明或已傳送的操作仍會阻止繼續；保留已儲存的連線和日誌。1.6.0 不含此變更。[詳情](../RECOVERY.md#no-root-removal-stopped-before-package-submission-unreleased)。

[文件導覽](../README.md) · [回報問題](../FEEDBACK.md)

開發中：如果尚未傳送套件移除請求，移除失敗後可為同一已儲存的電視選擇「檢視復原選項」。檢查與移除仍需分別確認。如果電視拒絕套件狀態檢查，復原會停止並提供報告。`recovery` 摘要區分尚未開始的移除、繼承的操作和中斷的套件操作，不公開完整日誌，也不能作為復原授權。

<!-- Anchors retained for links to earlier guide headings. -->
<a id="v110-起的可選-root-python"></a>
<a id="120-的-lg-固件更新阻止功能"></a>
<a id="130-新增功能"></a>
<a id="130-新增功能--12"></a>
<a id="未發佈候選版透過-homebrew-設定-root"></a>
<a id="未發佈候選版本hdmi-聲音恢復root"></a>

<a id="主題-154"></a>

## 主題

在下一版本預覽中，**Home 設定 → 桌布**顯示目前主題桌布、偵測到的電視能力和目前模式。自動模式選擇相容畫質；只有主題包含對應資源時才能選擇 4K、1080p 或圖片。影片播放失敗時會改用圖片。調暗程度每次調整 5%，也可恢復主題預設設定。Classic 和無桌布主題會明確顯示無桌布狀態。

下一版本預覽的個人桌布：在桌面 CYTV 開啟「桌布」，選擇 JPG/PNG、調整裁切，並輸入 Home 設定顯示的電視區域網路位址及接收 PIN。CYTV 在本機產生無聲影片；只有裁切後原圖的解析度足夠時才提供 4K。在電視選擇從 CYTV 接收或手機上傳，並以同一 Wi-Fi 的手機掃描 QR 碼。手機傳送的是最高 1920×1080 的一般圖片，不使用原生 4K 影片層；清晰度受電視介面解析度限制。傳送前確認提示，再於電視預覽並套用。個人上傳會保留，可在桌布設定重新選擇或刪除。取消或檔案遭拒時會保留原背景。需要相符的下一版本 Home/服務與 CYTV 組建。

下一版本的內建桌布：**Home 設定 → 桌布 → 內建桌布 → Black Hole**。影片作者為 **Xecutioner**，獲准在標示作者的前提下非商業使用。確認其他主題時會套用該主題自己的桌布；Black Hole 和個人上傳仍可重新選擇。連續 4K 串流避免每次循環回到檔案開頭，並提供相容影片或圖片作為備援。

Android CYTV: **設定電視** · **桌布** · **維護**. 在電視上開啟 Home 設定 → 桌布 → 從手機上傳。用手機相機掃描 QR 碼，選擇 JPG/PNG，然後在電視上套用。 手機上傳：最高 1920×1080 的圖片，不支援原生 4K 影片。真正的 4K 請使用電腦版 CYTV。

1.7.0: **設定 → 主題**。**Classic**, **Liquid Glass**, **Ribbon** 為內建主題，無須下載；預設仍是 Classic。**Channel** 是 showcase 的外部主題。在主題展示試用時：選擇後請於 **20 秒**內按 **保留主題**。選擇 **還原**、按 Back 或等候逾時會恢復先前的主題。尚未確認的試用遭中斷時，下次啟動 Home 會還原 Classic。 在已安裝清單中選擇內建或已下載主題會立即套用並儲存，沒有確認計時器。從電腦接收或透過 URL 安裝的主題也一樣。只有主題展示中的試用主題會啟動 20 秒試用。

1.7.0：**Classic**、**Liquid Glass** 和 **Ribbon** 為內建主題。**Alpine 1.4.4** 移至 **主題展示**，需要下載。已儲存的 `builtin:alpine` 選擇會退回 Classic，並顯示現有的復原提示；Home 不會自動下載 Alpine，也不會將其替換成 Liquid Glass。 版本 1.6.0 包含 Classic、Alpine 和 Ribbon。

已安裝的主題顯示在可水平捲動的單行清單中。目前主題一律排在第一位，並以醒目的卡片顯示。使用左／右方向鍵瀏覽。

展示頁僅顯示此電視尚未安裝的主題。Classic、Liquid Glass, Ribbon 和已下載主題均會隱藏，即使目錄中已有新版本。刪除後主題會重新出現。更新請使用連結安裝或從電腦接收。

主題卡片直接嵌入主題設定，與設定分類並排顯示。展示目錄、連結安裝和電腦傳輸都在同一面板開啟；只有展示目錄中的試用會暫時顯示 Home。

開啟主題展示或選擇重新整理時，會從主專案儲存庫檢查已審核的目錄更新，無需更新 Home 或重新載入頁面。正常合併後即可取得新項目；尚未合併的候選版本可能仍顯示內建目錄。離線或請求失敗時使用內建項目與預覽。內建主題與已安裝的 Home 版本一致。開啟 Channel 預覽，選擇**下載主題**（需要網際網路）。下載後試用，並在 **20 秒**內選擇保留主題。已安裝主題可離線使用。仍可透過 URL 新增固定版本連結。

測試未發布主題時，先在電視開啟**設定 → 主題 → 從電腦接收**。將電視顯示的位址和六位 PIN 輸入電腦預覽中的 **Send to TV**，傳送後在電視選擇**套用主題**。主要方式由電腦主動連線至電視 TCP **8879**，無需修改電腦防火牆。兩台裝置須在同一可信家庭網路。接收器在一次上傳、取消、離開頁面或 **10 分鐘**後關閉。PIN 不會儲存，安裝後的主題可離線使用。無需發布至 GitHub。

安裝已發佈主題時，開啟**透過 ID 新增**，輸入 ID（例如 `102300a209`）、`da.gd/102300a209` 或完整 GitHub 連結。Home 會在載入前顯示補全的 da.gd 位址，然後驗證 GitHub 目標與主題套件。作者可從版本說明或電腦預覽的 **TV link → Copy ID** 複製 ID。

**1.6.0:** Home Helper 面板中的**顯示診斷資訊**會顯示其本身狀態要求的簡短過濾結果。檢視不會啟動 Helper，也不會變更 Home 控制。僅在被要求時分享已檢查的 JSON；[詳情](../HELPER-DIAGNOSTICS.md#candidate-panel-caller-diagnostics-207)。

[Themes (English)](../THEMES.md) · [1.5.4 QA (English)](../history/2026-10-31-release-1.5.3-signed-root-qa.md).

1.5.4 中的可設定應用程式列主題可將輸入、Wi-Fi 和設定放在左下角。啟用此導覽時，在第一個可見應用程式上按左鍵依序選取設定、Wi-Fi 和輸入；在設定上按右鍵返回同一可見應用程式。需要新 Home 功能的主題在不支援的版本上安裝會遭拒，現有外觀和選擇保持不變。請先更新 Home。之後降級可能在啟動時還原 Classic。

主題頁面顯示內建主題和您自行安裝的所有主題預覽，離線也可查看。獨立的展示按鈕開啟已發佈目錄；個人安裝不會發佈主題。

外觀包含顯示目前數量的欄數和應用程式設定。獨立的主題分類包含已安裝主題、主題展示、從電腦接收及右側的透過 ID 新增（例如 102300a209）。選擇 Classic 卡片可還原；下載的主題可逐一刪除。語言分類可直接選擇語言。

瀏覽器預覽中的「從電腦接收」說明電視上的操作，不會在電腦上啟動電視接收器。請使用預覽上方的 Send to TV。刪除已下載主題需要確認；刪除目前主題前會先還原 Classic。取消會保留主題。

<a id="設定分類未發布候選版本"></a>

## 設定分類（1.5.0）

兩個版本均在左側顯示分類，右側顯示所選設定：主畫面、外觀、主題、語言、軟體更新及進階。No-root 另有 Developer Mode；Root 的 LG 韌體更新位於更新分類，HDMI 聲音位於進階分類。上下鍵在目前欄內移動，右鍵進入設定，左鍵返回分類。返回鍵先返回分類，再關閉設定。也可用 Tab 選擇返回 Home 按鈕。

軟體更新分類及內部按鈕上的黃色圓點表示有可用更新。成功檢查確認沒有更新後，兩處圓點同時消失；檢查失敗時保留上次確認的狀態。

<a id="自動圖形解析度候選版本"></a>

## 自動圖形解析度(1.6.0)

1.6.0 的電腦/Android 安裝程式和已遷移的 OTA 用戶端會根據電視回報的能力選擇 720p 或 1080p。無法驗證時，操作會停止。獨立安裝的舊更新程式需要依文件透過電腦遷移；復原程序保留原始套件。

[HD/FHD details (English)](../development/HOME-GRAPHICS-RESOLUTION.md#automatic-selection-and-ota).

> **1.6.0:** 請保留最初失敗嘗試的報告。新報告會區分已記錄的首次錯誤與後續檢查，並提供經過篩選的 Doctor/狀態摘要。安裝、狀態檢查或還原成功後也可匯出報告。缺少的歷史證據仍標為未知；報告不授予復原操作權限。 [↗](../development/INSTALLER-DIAGNOSTICS.md).
