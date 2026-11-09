# Clean Your TV — 使用者指南

安裝程式詢問電視名稱，預設為 **Home**；CLI可用 `--tv-name "Aashiyaan"`。舊版本升級後，**設定 → Home → 電視名稱**會自動出現，可隨時儲存新名稱或重設為Home。重新啟動和受支援的更新會保留名稱及其他設定。最多48個字元。適用於啟動器及其本身的載入畫面，不變更網路名稱。LG較早的載入名稱可能需要透過安裝程式套用。

尚未發布的安裝程式變更：新安裝前，電腦安裝程式會檢查 GitHub 上是否有更新的穩定版本。選擇「開啟 GitHub 並下載最新版本」會停止目前安裝並開啟下載頁面；選擇「不，安裝此版本」才會明確繼續。檢查失敗時仍可繼續。未完成的操作和復原流程會跳過檢查。

Clean Your TV 為 LG webOS 提供個人主畫面：依自己的順序排列應用程式，此選單沒有贊助內容列。使用電腦或 Android 手機安裝，設定完成後即可關閉電腦。

## 1. 下載安裝程式

點選適合裝置的圖片。按鈕下載最新已發布版本。Mac 請選 Apple Silicon（M1 或更新）或 Intel，可在 Apple 選單 → 關於這台 Mac 中查看。

[![下載 — Windows x64](../../assets/brand/downloads/windows.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-windows-x64-desktop.zip)
[![下載 — macOS Apple Silicon](../../assets/brand/downloads/macos-arm64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-arm64.zip)
[![下載 — macOS Intel](../../assets/brand/downloads/macos-x64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-x64.zip)
[![下載 — Linux x64](../../assets/brand/downloads/linux.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-linux-x64.deb)
[![下載 — Android ARM64](../../assets/brand/downloads/android.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-android-arm64.apk)

<a id="選擇版本"></a>

<a id="安裝之前"></a>

## 2. 選擇版本

開啟電視，將電視與電腦或手機連接到同一家庭網路。出現提示時，允許 CYTV 存取本地網路。

- **No-root** — 電視沒有 root 權限時選擇。依下方步驟設定 Developer Mode。
- **Root** — 已有 SSH root 存取權限時選擇。安裝程式不會為電視取得 root。請勿在此電視上開啟 Developer Mode；保留 SSH 存取和復原資料。

對於 Root，安裝程式會檢查並選擇可用的 Home 控制方式。如果無法確認相容性，安裝將停止；請勿略過失敗的檢查。

**No-root → Root:** 如果在完整移除後重新安裝了 No-root，切換至 Root 前可能需要先清理。請備份 Home 偏好設定，使用已儲存的 Root 連線選擇**解除安裝 Clean Your TV**，並等待移除驗證完成。這也會移除 No-root Home 和 Helper。接著安裝 Root；請保留復原記錄。

### 設定 Developer Mode（No-root）

Developer Mode 讓 CYTV 可以在沒有 root 的電視上安裝應用程式。

1. 在電視上開啟 LG Apps，搜尋並安裝 Developer Mode。
2. 開啟 Developer Mode 並登入 LG Developer 帳號。如需註冊，請前往 [LG Developer](https://webostv.developer.lge.com)。
3. 開啟 Dev Mode Status。電視將重新啟動，之後請再次開啟 Developer Mode。
4. 開啟 Key Server 並保持 Developer Mode 開啟。將其中的 IP Address 填入 CYTV 的電視位址欄。
5. 輸入電視上 Developer Mode 顯示的六位 Passphrase，注意區分大小寫。

請使用電視上的代碼，而非 LG 帳號密碼。如未顯示代碼，請開啟 Key Server。

配對是獨立步驟：電視提示時，請用遙控器允許 CYTV 連線。

請保持 Developer Mode 有效：計時結束前開啟它，並在電視連網時按 EXTEND。過期後 LG 可能會刪除這些應用程式。

<a id="安裝與選擇語言"></a>

## 3. 開啟安裝程式

- **Windows x64：**下載 `cytv-windows-x64-desktop.zip`，在資源管理器中選擇“全部解壓縮”，然後打開 `cytv-desktop/cytv-desktop.exe`。保留旁邊的 `_internal` 資料夾。
- **macOS 13+：**解壓 `cytv-macos-arm64.zip`（Apple Silicon）或 `cytv-macos-x64.zip`（Intel），將 `cytv.app` 移到“應用程式”後打開。允許本地網路訪問。若被阻止，僅對可信項目下載使用“隱私與安全性 → 仍要打開”；不要禁用 Gatekeeper。
- **Linux x64：**在 Ubuntu 22.04+、Debian 12+ 或 Mint 21+ 中，用圖形軟體包安裝程式打開 `cytv-linux-x64.deb`，安裝後從應用菜單啟動 Clean Your TV。桌面庫可能需要聯網下載。不含 Linux ARM。

**Android ARM64：**需要 Android 7+、WebView/Chrome 108+ 的 64 位元 ARM 手機。開啟下載的 APK，依 Android 提示允許從該來源安裝。開啟 CYTV，在右上角選擇語言。更新時不要解除安裝或清除資料。

桌面精靈會自動選擇系統語言，也可手動選擇並儲存。電視端在**設定 → 語言**中選擇，或使用系統/自動選項。安裝程式與電視偏好各自獨立。完整代碼見[語言索引](../LANGUAGES.md)。

## 4. 安裝到電視

1. 在 CYTV 中選擇**設定我的電視**。電腦端選擇搜尋到的電視；Android 端輸入電視 IP 位址。搜尋未找到電視時，請手動輸入位址。
2. 選擇 **No-root** 或 **Root**，繼續前確認電視是否正確。
3. No-root：輸入 Developer Mode 的代碼並在電視上允許連線。Root：使用現有 SSH 憑證。僅在可信任網路中為自己的電視確認新 SSH 身分。如果已儲存的金鑰變更，請停止並檢查原因。
4. 依精靈提示操作。完成前保持電視開啟，不要切換網路或關閉 CYTV。不要強制停止 Android 應用程式。Root 在準備好復原後立即啟用 Home 控制。

如果無法讀取電視輸入但應用程式清單有效，Root 安裝將顯示警告並繼續。Home 中可能缺少輸入；應用程式清單讀取失敗或為空時，安裝仍會停止。如果警告持續出現，請儲存診斷報告。

## 5. 檢查遙控器

1. 在電視上開啟另一個應用程式，短按一次 **Home**。應開啟 Clean Your TV。在精靈中填寫實際看到的結果；未測試時請略過。
2. 檢查方向鍵、OK、返回、音量和聲音。分別測試待機喚醒及斷電後的啟動。安裝成功本身不會驗證這些操作。

<a id="日常使用與恢復"></a>

## 6. 日常使用與恢復

No-root 紅外線遙控支援：短按並放開 Home 後，預定約 700 毫秒後開啟 Clean；LG Home 可能先短暫出現。長按 Home 仍由 webOS 處理，連按三次仍會停止 Helper。一般 Developer Mode 電視上的存取能力尚未驗證；請勿變更輸入裝置權限。

方向鍵選擇圖塊，OK 打開，按住 OK 調整順序。短按返回保留應用本身的導航和退出確認。啟用 Home 控制時，短按 Home 打開 Clean Your TV。按住返回 1.2 秒會臨時打開 LG Home 一次，不改變 Home 控制開關和設定。

**兩秒內按 Home 三次，每次都鬆開**，即可返回 LG Home 並停止 Home 控制，偏好設定保留。

No-root: 要重新啟動 Home 控制，請開啟 Home Helper，選擇啟動 Helper 並確認。已儲存的主畫面選擇會保留。 Root：在 Home 設定中啟用 **更改 Home（Change Home）** 恢復。**開啟 LG Home（Open LG Home）** 只打開 LG Home 一次，不更改路由。要持續使用 LG Home，請關閉 **更改 Home（Change Home）**。不要同時執行兩種控制器。若故障重復出現，請保持 LG Home 啟用。

更新不會重新啟動已停止的 No-root Helper。請按上述步驟手動恢復；不要手動刪除停止標記。

## 需要協助？

重設或變更 SSH 後若出現 `ssh-identity-changed`，請停止：CYTV 在登入前阻止了已儲存金鑰的變化。首次信任提示不能取代原金鑰；待處理的解除安裝無法解釋金鑰不符。請保留原有連線設定、金鑰和復原記錄。目前沒有受支援的自動重新信任指令。需要獨立驗證電視身分和指紋，並採用經過審查、保留原設定的復原程序：[SSH 身分變更復原](../RECOVERY.md#ssh-identity-changed)。

安裝中斷後，請使用原先儲存的連線，先選擇**檢查電視狀態**。僅透過精靈提供的復原操作繼續。如果狀態不明，請儲存診斷報告並停止；保留復原資料，不要盲目重複安裝。

復原期間請保持 Home 控制關閉，保留原始診斷報告和已儲存的連線。檢查與變更須分別確認。請依照適用於已安裝版本的詳細復原說明操作；不要強制重新安裝或清除復原狀態。

求助時請提供電視型號、韌體、No-root 或 Root、安裝裝置、出錯步驟和錯誤訊息。分享報告前移除密碼、金鑰、位址和個人資料。報告不會自動公開。

[回報問題](../FEEDBACK.md) · [詳細復原說明（英文）](../RECOVERY.md) · [更新或移除（英文）](../MAINTENANCE.md) · [其他語言](../LANGUAGES.md)

### 簡單移除

請使用同一儲存的電視連線，在維護中選擇**解除安裝 Clean Your TV**。確認一次後，移除實際存在的已知專案應用程式和檔案，略過不存在的項目；部分安裝後也可使用。

在沒有獨立 LG Home 應用程式的舊款電視上，移除 No-root 時可能會切換到直播電視。請保持電視開啟，並依提示重新啟動；不要刪除復原資料或重設電視。

出現提示時，請斷開電視電源後重新連接，等待網路恢復，然後選擇**重試**。待機或 Quick Start 不等於完全重新啟動；CYTV 不會自動重新啟動電視。連線中斷時，請檢查連線並重試同一移除目標，無需另一個復原精靈。存取被拒絕時，請使用要求的 Root 連線；電視忙碌時，請稍候再試。只有驗證最終清理後才顯示成功。請保留金鑰和原始報告。上述緊急控制及分享同意要求仍有效。

在安裝失敗或中斷後直接提供復原入口。如果 No-root 無法繼續，請確認一次完整移除。遇到暫時斷線或 CYTV 程序忙碌時，移除最多自動嘗試三次。如果需要 Root 權限，請為同一台電視選擇 **透過 Root 連線**；經驗證的 Root 清理也會完成該電視受阻的 No-root 移除。Root 啟用失敗時，程式嘗試還原並驗證 LG Home，不會重複啟用。取消未完成的操作會保留診斷報告和復原操作。緊急停止狀態保持不變。

刪除過程中連線失敗時，可開啟連線詳細資訊，檢查網路或選擇現有 Root SSH 私鑰後重試。電視位址、版本類型、連接埠和主機金鑰驗證保持固定。No-root 會在配對前檢查 Helper：請停止它，並在目前安裝流程中確認重新檢查。只有確認元件和處理程序均不存在且沒有未完成安裝的空電視才可略過重新啟動；實際刪除後仍須執行要求的完整重新啟動。輸入服務故障時仍可繼續安全清理套件，但只有確認輸入捷徑也已清理後才會顯示成功。

**重新安裝 Root：**使用儲存的連線，選擇**設定我的電視 → Root**，並確認**重新安裝 Root？**。安裝程式會還原 LG Home，並完整刪除 Clean Your TV，包括其更新程式、Home Helper 和已儲存的偏好設定。確認刪除完成後，會安裝並啟用此安裝程式內的套件和 Root 執行環境。電視上的其他應用程式和現有 root/SSH 存取權限會保留。如果刪除停止或要求完整重新啟動，請先完成刪除，再重新開始設定。單獨選擇**解除安裝 Clean Your TV**絕不會啟動新安裝。

<!-- Legacy anchors retained for existing links. Detailed references: -->
<a id="v110-起的可選-root-python"></a>
<a id="120-的-lg-固件更新阻止功能"></a>
<a id="130-新增功能"></a>
<a id="130-新增功能--12"></a>
<a id="未發佈候選版透過-homebrew-設定-root"></a>
<a id="未發佈候選版本hdmi-聲音恢復root"></a>
<a id="主題-154"></a>
<a id="設定分類未發布候選版本"></a>
<a id="自動圖形解析度候選版本"></a>
<a id="更新與移除"></a>
<a id="說明與詳細指引"></a>
<a id="主題"></a>
<a id="設定分類150"></a>
<a id="自動圖形解析度160"></a>
<a id="儲存空間"></a>

詳細英文參考：[需求](../COMPATIBILITY.md) · [遙控器](../CONTROLS.md) · [主題](../THEMES.md) · [更新](../UPDATES.md)。

<a id="未發布候選版本unreleased電視上的舊版-nodejs"></a>
<a id="電視上的舊版-nodejs已隨-v1120-發布"></a>
<a id="簡單移除v1110"></a>

## 天氣

開啟設定中桌布下方的天氣。開啟天氣後，在城市中手動搜尋並確認地區和國家，或選擇自動，依網路連線估算城市。VPN 可能影響結果；如果找不到城市或結果不正確，請手動搜尋。已識別或選擇的城市會顯示在設定中。選擇 °C / m/s 或 °F / mph，以及可用的簡潔、目前、詳細或四天天氣預報格式。預覽會採用目前主題；「範例」表示示範資料。Liquid Glass 僅支援簡潔格式。Ribbon 和 Atmosphere 不顯示天氣。關閉天氣會停止請求，並隱藏城市、單位和格式選項；仍可選擇資料來源。連線中斷時，近期資料可能暫時保留；資料過舊後，天氣會隱藏，直到成功重新整理。

選擇預報來源：Auto、MET Norway 或 Open-Meteo。Auto 先嘗試 MET Norway，失敗時嘗試一次 Open-Meteo，之後重用上次成功的來源與快取。手動選擇的來源不會自動切換。新設定預設使用 Auto；以前儲存且未指定來源的設定保留 Open-Meteo。設定中會顯示實際來源。可用性取決於網路。MET 更新間隔至少三小時，快取最多保留六小時。缺少的欄位會隱藏：MET 不提供體感溫度或降水機率。每日範圍彙整預報時間點的資料，並非實測極值。

預報座標傳送至 api.met.no 或 api.open-meteo.com，城市搜尋傳送至 geocoding-api.open-meteo.com。選用的自動定位會向 get.geojs.io 傳送公用 IP。連線使用 HTTPS，無需 API 金鑰。位置、來源與快取儲存在電視上。「資料來源」包含服務條款與署名，包括挪威氣象研究所（MET Norway，CC BY 4.0）。

點選天氣標題旁的「資料來源」可查看服務和授權資訊。
