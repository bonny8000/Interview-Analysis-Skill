# 逐句編碼與分析矩陣

## 先辨識使用者要的粒度

`participant | sentence_id | sentence | Initial Code | Sub Theme | Theme | Categories` 是逐句編碼表，不是受訪者摘要。交付同名欄位但每人只放一句總結，或將精選引句台帳改名，都不符合此契約。

參考試算表可以決定欄位與分頁順序，但不能把其中的 PU、PEOU、PT、ATU 等框架自動套用到新研究。只有使用者要求沿用理論／碼本才是 Track A；純版型參考仍可走 Track B。也不要照抄範例中缺少主題、拼字分裂或重寫原話的瑕疵。

## 五個層級不是同一件事

| 層級 | 定義 | 虛構示例（不是研究證據） |
|---|---|---|
| sentence | 一位受訪者表達一個完整意思的原話單位，可跨相鄰斷行 | 我還沒看完，它就跳走了。 |
| Initial Code | 緊貼該意思的概念標記，可多碼 | IC01 閱讀未完就轉場 |
| Sub Theme | 聚合有共同机制的數個碼，比 Theme 具體 | S01 閱讀節奏與轉場時機 |
| Theme | 跨子主題的解釋性模式 | T01 控制感取決於能否自行決定繼續 |
| Categories | 分析面向或明確指定的理論構念，與 Theme 並非另一個同義欄 | 控制與自主性 |

同一 Theme 可涉及不同 Categories；同一 Category 可貫穿多個 Themes。不要為湊層級，把同一句話重寫四次充當碼、子主題、主題、類別。研究情境（任務／產品／模式）是 context 欄，不等於上述層級。

## 意義單位與來源

- 一列通常1–3句，範圍由完整意思而非換行、固定字數或標點決定。不能把單獨的「因為」「對」無脈絡當完整觀點。
- 同一人相鄰片段可合成完整回答，保留所有來源回合；不能跨訪談者提問或將不同人的句子拼在一起。跨非相鄰來源應拆成不同單位。
- 同一段有兩個可獨立理解的意思可以拆；同一個不可分的意思涉及兩概念則用多碼。不為增加樣本數而拆成碎片。
- `sentence_id` 在 participant 範圍內穩定且唯一，建議 P01-S001。排序、換主題或新增碼不可重編既有ID。`source_turn` 保存原始回合／段號與行號，兩者不能混稱。
- `sentence` 是保守清理後的原話；`raw_sentence` 保存去識別化的來源字串，非原始個資備份。只改確定的轉錄誤字，改動附理由。可額外提供 `sentence_summary` 作易讀轉述，但不加引號、不用來冒充逐字證據。
- 錄音未核實時，依完整問答能清楚辨識者可標 `context_attributed`；實質話者仍不明者用 `needs_review`，不計入受訪者發現。

## 四張CSV

所有CSV使用 UTF-8 BOM、CSV函式庫、全欄雙引號、無儲存格換行。識別、代碼與文字儲存為字串。

### RawData.csv

前六欄依序：`participant,sentence_id,sentence,Categories,Initial Code,Final Categories`。

再加：`source_turn,source_file,raw_sentence,speaker_status,analysis_status,exclusion_reason,context_note`。可增加 task、evidence_type、sentence_summary 等必要欄位。

- 一個辨識出的受訪者意義單位一列，依來源順序。
- `Initial Code`、Categories 及 Final Categories 是该單位所有對應標籤的去重清單，以 `; ` 分隔；Final Categories 是 Theme 的相容欄位，不是另一套自由命名分類。
- `analysis_status`：`coded`、`needs_review`、`not_relevant`。後兩者填原因、保留列，不混入主題統計。不要用 Z-None 同時代表沒意義、沒看、說話者不明及編碼失敗。
- 來源中不是受訪者意義單位的內容另作 Source Coverage：逐源回合記 `included`、`context_only`、`excluded`、`needs_review` 及原因。不默默丟掉全文後只報精選句數。

### Combine Data.csv

前七欄逐字依序：`participant,sentence_id,sentence,Initial Code,Sub Theme,Theme,Categories`。

追加來源、話者狀態與任務脈絡等欄位，但不要把它們插進前七欄。一列＝一個 coded 單位×一個 Initial Code；不把多碼塞在一格。相同 participant、sentence_id 重複時，sentence 必須一致。依 Theme → Sub Theme → Initial Code → participant → 原句順序排序。

### Codebook.csv

必要欄：`Initial Code,Definition,Include,Exclude,Sub Theme,Theme,Categories,failure_mode`。

每個 Initial Code 有且只有一個 canonical Sub Theme／Theme／Category 組合；同一 Sub Theme 只能屬於一個 Theme。真正跨主題的句子以不同碼多列表示，不讓同碼任意換父層。痛點碼才需 failure_mode，不能為了填滿欄位虛構故障。

### Subtheme Summary.csv

欄位：`Theme,Sub Theme,coding_rows,sentence_count,participant_count,participants`。

- coding_rows＝Combine Data 此子主題的列數，相當於明確範圍的 COUNTA。
- sentence_count＝不重複 `(participant,sentence_id)` 數。
- participant_count＝不重複 participant 數。
- 不同子主題的句子／人數可能重疊，不可相加得到全案總數。全案 distinct 需重新計算。
- 主題統計由已確認歸屬且已編碼的單位計算；未知話者不算。數量反映這批可用資料，不代表族群比例、問題发生率或投票結果。

## 報告與完成檢查

報告先呈現主要發現，再解釋 Theme → Sub Theme → Initial Code 的鏈，附句子ID、逐字引句、涉及人數、反例及條件。清理方法與稽核留在附錄。依立場分群可以重疊，也可以寫不能穩定分群；不要強迫從碼本生成互斥人群。

完成前驗證：全部來源有處理結果、所有 coded 單位進入 Combine Data、每碼存在 Codebook、層級不衝突、RawData與Combine的原話一致、沒有重複的單位×碼、Pivot計數重算一致、引句能回查清理稿、試點／排除名單沒有混入。

仍有未辨識內容時交付明確的 review queue、數量和對結論的影響，稱為附待審內容的分析稿；不能宣稱逐字稿完全校訂或全量受訪者回答都已編碼。
