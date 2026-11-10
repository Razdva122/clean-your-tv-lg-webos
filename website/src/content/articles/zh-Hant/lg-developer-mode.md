---
lang: zh-Hant
topic: lg-developer-mode
title: "No-root webOS 啟動器與 LG 開發者模式"
description: "了解 Clean Your TV No-root 為何需要 LG 開發者模式、工作階段到期如何影響側載應用程式，以及啟動器消失後該檢查什麼。"
updated: '2026-11-09'
---

LG 開發者模式讓你不必取得電視的 root 權限，就能安裝及測試 webOS TV 應用程式。Clean Your TV No-root 使用這種存取方式，並搭配電視端的 Home Helper。開發者模式的工作階段有時間限制：請在 LG 的 Developer Mode 應用程式中查看剩餘時間，並在到期前延長，讓側載的應用程式持續可用。

## 開發者模式提供什麼？

開發者模式提供開發用途的存取權限，不會提供 root 權限，也不保證 Home 鍵輔助工具在所有型號上都能運作。Clean Your TV 仍會檢查執行環境與輸入方面的需求。一般商店應用程式、側載應用程式與已取得 root 權限的系統，使用的存取途徑各不相同。

No-root 只能用於合適的開發者模式環境。如果電視已取得 root 權限，不要再在其上啟用開發者模式。請先閱讀 [Root 與 No-root 比較](/clean-your-tv-lg-webos/zh-Hant/articles/root-vs-no-root/)及[相容性需求](/clean-your-tv-lg-webos/zh-Hant/compatibility/)。

## 準備電視與安裝裝置

確切步驟請遵循[目前的安裝指南](/clean-your-tv-lg-webos/zh-Hant/install/)。你需要 LG 的 Developer Mode 應用程式、必要的 LG 開發者帳號登入，以及配對用的 Key Server。電視與電腦或支援的 Android 裝置必須連上可互相通訊的網路。即使兩台裝置都能上網，訪客網路或用戶端隔離仍可能阻止設定。

請妥善保管配對金鑰與連線資訊，不要公開。使用指南中連結的正式發布安裝程式，不要把任意下載的 IPK 檔案當成完整的 Home 鍵設定方案。安裝完成後，啟動器與 Helper 都在電視上執行，電腦可以關機。

## 維持工作階段有效

開啟 LG 的 Developer Mode 應用程式，查看工作階段剩餘時間，並在具備所需連線的情況下延長。應遵循 LG 目前的說明，不要依賴舊文章中固定不變的時數。嘗試續期不代表成功：操作後，請再次檢查顯示的剩餘時間。

Clean Your TV 提供選用的自動續期測試功能，預設關閉。即使啟用，仍應持續檢查實際的開發者模式狀態。這項功能不會取消 LG 的工作階段要求，也不能讓已停用的模式永久有效。

## 啟動器消失，或 Home 鍵開啟 LG Home，怎麼辦？

重複安裝前，先檢查開發者模式。LG 文件說明，停用開發者模式或讓工作階段到期，可能會解除安裝開發用應用程式。工作階段到期與 Home Helper 緊急停止、配對問題或安裝中斷是不同情況。

如果開發用應用程式已被移除，請依文件恢復開發者模式，再根據實際狀態使用安裝程式的引導設定或復原功能。如果應用程式仍在，但 Home 鍵導向已停止，請查看 [Home 鍵說明](/clean-your-tv-lg-webos/zh-Hant/help/#home-button)。如果先前的操作中斷，請使用[復原指南](/clean-your-tv-lg-webos/zh-Hant/help/#interrupted)，不要刪除系統檔案。復原後，應另外驗證 Home 鍵行為。

## 資料來源與延伸閱讀

- [LG：使用 Developer Mode 應用程式](https://webostv.developer.lge.com/develop/getting-started/developer-mode-app)
- [專案 No-root 安裝指南](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/INSTALL.md)
- [專案復原參考](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/RECOVERY.md)
