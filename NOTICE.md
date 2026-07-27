# 來源、修改與致謝

本倉庫是《The Ur-Quan Masters HD Beta 1》的非官方繁體中文本地化版本，與
Toys for Bob、原始著作權人、The Ur-Quan Masters 專案、UQM-HD 專案及
SourceForge 均無從屬、贊助或背書關係。名稱與商標屬各自權利人所有。

## 上游作品與本地化

- 原始遊戲由 Toys for Bob 製作；程式、文字、圖像、音樂、語音及其他素材的
  著作權歸 Toys for Bob 或各自創作者所有。
- 感謝 The Ur-Quan Masters 與 UQM-HD 歷年貢獻者保存、移植及改良本作。
- 繁體中文翻譯由 OpenAI Codex 語言模型重新翻譯，保留在
  `localization/records.llm-zh-TW.json`、最終工作區及稽核紀錄中。它已通過格式、
  資源契約與封裝驗證，但尚未經完整母語人工校訂及全流程人工通關。
- 選單背景與船艦圖片是上游遊戲內容的本地化或擷取版本，依
  CC BY-NC-SA 2.5 提供，不得作商業用途。
- Noto Sans TC 用於產生繁中字形；相關字型軟體依 SIL OFL 1.1 授權。

## 可執行程式的兩項來源修改

相對於官方 UQM-HD Beta 1 原始碼，本倉庫只修改兩個 C 原始檔；兩處均在來源
旁以 `Traditional Chinese distribution change (2026-07-27)` 標示：

1. `game/src/uqm/restart.c`：主選單目前項目採明亮黃色脈衝，使選取狀態明顯。
2. `game/src/uqm/battle.c`：本機 Super Melee 戰鬥中，獨立的
   `KEY_MENU_EDIT_CANCEL`（預設只有 `Esc`）會清除 `IN_BATTLE`，經既有戰後流程
   回到隊伍設定；不設定 `CHECK_ABORT`，也不把玩家一的特殊能力鍵當成退出鍵。

Windows PE 補丁工具只接受已知 SHA-256 與唯一指令特徵；未知版本會被拒絕。
倉庫及發行包不散布獨立的已修改 `uqm.exe`。

此外，`game/build/msvc6/UrQuanMasters.vcproj` 的四個上游開發者絕對資源
路徑已改為等價的 `..\..\src\res` 相對路徑；已不用的個人
`uqmanimationtool.conf` 與其二進位 JAR 未納入倉庫。這些整理不改變遊戲行為。

## 可重現來源雜湊

| 項目 | SHA-256 |
|---|---|
| 官方 UQM-HD Beta 1 原始碼壓縮檔 | `9a94cce18e039a0447a758abed52e72694b279279d7a7eea19a93dfe667f0e73` |
| 官方 Windows Beta 1 安裝程式 | `17ba52347dde55c3103bdaf566c1511e88d509ad7eb50eda60e4f2912f108bde` |
| 官方 `hires4x.zip` | `76af440bd845a63bd42b88913347374eb62c40c149d0bea37045a10bd0bd6618` |
| 官方未修改 `uqm.exe` | `c43c258aa41c4effe5d092c8541560a517cdd7be91e3c576a10a4ad306f776d3` |
| 套用目前兩項補丁後的 `uqm.exe` | `3d2174f5dab4ce9b7a2dcd0eec7c59473f543239953b18664c51fff631f36bc9` |

完整授權文本與上游歸屬見 `LICENSE`、`LICENSES/UPSTREAM-COPYING.txt`、
`LICENSES/OFL-1.1-NotoSansCJK.txt`、`game/COPYING` 及個別來源檔頭。
