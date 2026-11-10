---
lang: zh-Hant
topic: root-vs-no-root
title: "LG webOS 啟動器：Root 與 No-root 如何選擇"
description: "為 LG webOS 電視選擇合適的 Clean Your TV 版本，安裝前先比較存取權限、開發者模式維護、Home 鍵控制及復原方式。"
updated: '2026-11-09'
---

如果 LG 電視使用開發者模式，請選擇 No-root。只有電視已具備可用的 root 權限和相容服務時，才選擇 Root。兩個 Clean Your TV 版本提供相同的主畫面介面，安裝後都在電視上執行。安裝程式不會取得 root 權限，也不會刷寫韌體。

## No-root 有哪些要求？

No-root 在設定時使用 LG 開發者模式、Key Server 與本機配對。Home Helper 在電視上執行，並在裝置和韌體支援時處理 Home 鍵。日常使用不需要一直開著電腦或手機。

需要持續維護的是開發者模式：請在工作階段到期前延長有效時間。LG 提醒，透過開發者模式安裝的應用程式，可能在模式停用或工作階段到期後遭到移除。專案的自動續期選項是選用的測試功能，預設關閉，不應將它視為保證。使用此版本前，請閱讀[開發者模式指南](/clean-your-tv-lg-webos/zh-Hant/articles/lg-developer-mode/)。

## Root 有哪些要求？

Root 使用現有的 root SSH 存取權限、相容的電視服務，以及支援的輸入和執行環境功能。僅有 root 權限並不能證明相容。安裝程式會檢查環境；不要略過未通過的前置條件，也不要藉由替換系統執行環境強行通過檢查。

Root 使用獨立的套件與 Home 鍵導向方式。不要在現有的 root 環境上啟用開發者模式；使用 Root 導向前，應停止 No-root Home Helper。選擇版本是依據已具備的存取權限，而不是選一個能替電視取得 root 權限的按鈕。

## 維護與復原有何不同？

- **日常使用：** 兩個版本都在電視上執行，可在啟動器中使用應用程式與佈景主題。
- **No-root 維護：** 保持開發者模式有效，並保留 Helper 所需的配對與連線條件。
- **Root 維護：** 保持獨立復原服務及其所需執行環境可用。能否更新取決於已安裝版本與支援的更新途徑；僅有 root 權限不會啟用 OTA。
- **緊急退出：** 目前支援的版本使用兩秒內短按 Home 鍵三次。Home Helper 0.6.13 及更早版本則使用長按兩秒。

緊急停止後，必須主動操作才能重新啟動持續導向。No-root 需開啟 Home Helper 並選擇 Start Helper；Root 需在 Home 設定中使用 Change Home。請參閱[版本比較](/clean-your-tv-lg-webos/zh-Hant/editions/)與[復原說明](/clean-your-tv-lg-webos/zh-Hant/help/#home-button)。

## 安裝前檢查電視

備妥確切的型號、韌體、webOS 和遙控器資訊，再閱讀[相容性頁面](/clean-your-tv-lg-webos/zh-Hant/compatibility/)。實測結果對應的是特定配置。設定後請分別測試 Home 鍵、應用程式啟動、聲音、待機和冷開機。套件能安裝，不代表所有功能都能正常運作。

使用[正式發布的安裝程式與安裝指南](/clean-your-tv-lg-webos/zh-Hant/install/)。如果已有可用設定並打算切換版本，請依文件中的轉換和移除步驟操作，不要將一個版本直接覆蓋安裝在另一個版本上。

## 資料來源與延伸閱讀

- [專案版本比較](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [專案需求與已知限制](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/COMPATIBILITY.md)
- [更換主畫面帶來的變化](/clean-your-tv-lg-webos/zh-Hant/articles/change-lg-webos-home-screen/)
