# Changelog — Interview Analysis

## [1.2.0] - 2026-10-12
### Added
- 逐份審閱模式（同一專案多份逐字稿時預設）：每份清理完停下來與使用者確認，確認後寫進訪談彙整表 `interview-table.csv`（每位受訪者 × 每個話題一列；UTF-8 with BOM，Excel 可直接開，也可匯入 Google 試算表或 Notion）。
- `references/review-workflow.md`、`templates/interview-table.template.csv`。
- 清理總覽新增「話題清單」。
### Removed
- 清理不再標注引導性問答（`[引導]`），清理由七步改為六步。

## [1.1.0] - 2026-10-12
### Added
- 逐字稿清理成為第一步：盤點來源、去識別化（直接／間接識別）、說話者錯置四種檢查、專有名詞表與同音字校正、簡轉繁「換字不換詞」、轉錄幻覺移除、回合編號。
- 前置產出 `cleaned/`：每場一份分析用逐字稿（含清理紀錄）＋ `cleaning-overview.md`。
- 檢查點（要先問／標記後繼續）與只清理模式。
- 新範本 `templates/cleaned-transcript.template.md`。
### Changed
- `references/transcript-hygiene.md` → `references/transcript-cleaning.md`（改寫擴充）。
- 引用一律帶回合編號 `P01-T010`；新增「不替說話者講完」「寫進報告前回查」兩條引句規則。
- 走查範例改用真實樣貌的原始轉錄稿（簡體、無標點、同音字、說話者錯置）。

## [1.0.0] - 2026-09-21
### Added
- 初版發布 Initial release。
- 三層主題編碼（開放／主軸／選擇性）、Track A/B 雙軌、碼本、觀點分群、可行動洞察。
- 與 user-story / user-flow / sitemap 共用同一套 `failure_mode` 詞彙。
