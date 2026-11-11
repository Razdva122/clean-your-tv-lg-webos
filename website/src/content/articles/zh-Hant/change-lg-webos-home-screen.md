---
lang: zh-Hant
topic: change-lg-webos-home-screen
title: "如何更換 LG webOS 電視的主畫面"
description: "使用 Clean Your TV 自訂 LG webOS 主畫面，了解啟動器能改變什麼、如何選擇版本，以及安裝前需要確認的事項。"
updated: '2026-11-09'
---

Clean Your TV 是 LG webOS 電視的替代主畫面。你可以按照自己的習慣排列應用程式、選擇佈景主題，並自訂 Dock。完成設定後，它直接在電視上執行，因此可以關閉電腦。能否接管 Home 鍵，取決於電視、韌體、遙控器及安裝方式。

## 可以自訂哪些內容？

啟動器改變的是尋找並開啟電視應用程式的介面。你可以整理常用項目，並選擇 Classic、Liquid Glass 或 Ribbon 等版面配置。安裝前可透過[瀏覽器示範](/clean-your-tv-lg-webos/demo/)比較各種配置。示範中的電視操作是模擬的，無法測試與你家電視的相容性。

替代啟動器不會更換 webOS 韌體、解鎖付費串流服務，也不會移除其他應用程式內的廣告。影像設定、輸入來源與串流服務仍是電視的獨立部分。若主要目標是讓主畫面更清爽，請閱讀[廣告方面有哪些變化](/clean-your-tv-lg-webos/zh-Hant/articles/lg-tv-home-screen-ads/)。

## 應該選擇哪種安裝方式？

已啟用 LG 開發者模式的電視應使用 No-root。電視端的 Home Helper 會在支援的環境中處理 Home 鍵。開發者模式必須維持啟用；工作階段到期可能導致側載的應用程式遭到移除。

只有電視已具備可用的 root 權限，且符合執行環境與服務需求時，才應使用 Root。Clean Your TV 安裝程式不會替電視取得 root 權限。不要在現有的 root 環境上啟用開發者模式，也不要同時執行兩種 Home 鍵導向方式。[版本指南](/clean-your-tv-lg-webos/zh-Hant/articles/root-vs-no-root/)說明了兩者的取捨。

## 更改現有設定前

1. 記錄確切型號、韌體、webOS 版本及遙控器類型，並對照[需求與電視實測紀錄](/clean-your-tv-lg-webos/zh-Hant/compatibility/)。每份報告只適用於其記錄的配置。
2. 按照[安裝指南](/clean-your-tv-lg-webos/zh-Hant/install/)操作，使用其中連結的正式發布安裝程式。設定期間，電視與安裝裝置必須位於可互相通訊的網路中。
3. 設定完成後，先檢查應用程式啟動與 Home 鍵，再分別檢查聲音、待機與喚醒，以及完全關機後的冷開機。套件安裝成功，不代表這些行為都已通過驗證。

## 如何返回 LG Home？

目前支援的版本使用兩秒內短按 Home 鍵三次來觸發緊急退出。Home Helper 0.6.13 及更早版本則需長按 Home 鍵兩秒。暫時開啟一次 LG Home 與停用持續的 Home 鍵導向是兩件事，請按照已安裝版本對應的[復原說明](/clean-your-tv-lg-webos/zh-Hant/help/#home-button)操作。更改啟動行為前，先確保有可用的復原途徑。

## 資料來源與延伸閱讀

- [專案版本與按鍵操作參考](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [專案安裝說明與前置條件](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/INSTALL.md)
- [開發者模式：讓 No-root 設定保持可用](/clean-your-tv-lg-webos/zh-Hant/articles/lg-developer-mode/)
