# SHIFT 題庫擴充指南

這個網站將程式與題庫分開。你可以新增題庫 JSON，再使用隨附工具產生 JS 題庫與更新目錄；**不用修改 `index.html` 或 `assets/app.js`**。新的題庫會自動顯示在首頁，也會加入分類練習。

所有新增內容沿用網站的作答流程：**完成一批題目後交卷，再顯示 100 分制成績、錯題與解析**。作答期間不顯示正誤、翻譯、逐字稿或解析；未答題列入總題數並計錯。這個成績是練習正確率，沒有換算成多益官方分數。

## 兩種加入方式

| 方式 | 適合情況 | 保存位置 |
|---|---|---|
| 網站「資料管理」→「匯入 JSON 題庫」 | 自己在目前瀏覽器加入練習 | 題目隨本機學習資料保存；媒體檔仍須放進網站資料夾 |
| 執行 `tools/add_pack.py` | 製作能整包分享、直接開啟的網站版本 | 產生 `data/題庫ID.js`，並更新 `data/catalog.js` |

網頁內匯入的題目不會自動變成資料夾裡的發布檔案。若要讓別人解壓縮後直接看到新題庫，請使用第二種方式。

## 快速開始

發布者需要 **Python 3.9 以上**，不需安裝任何額外套件。練習者只需要瀏覽器。

1. 複製 `data/example-pack.json`，另存為自己的 JSON，例如 `data/custom-003.json`。
2. 將根物件、所有題目與題組的 `testId` 改成相同的新 ID，例如 `custom-003`。
3. 將題目 ID 改成不重複的值，例如 `custom-003-q001`；若有題組，使用 `custom-003-g001` 等獨立 ID。
4. 填入題目、中譯、選項理由、答案、解析、證據與詞彙。若含聽力或圖片，先放好對應檔案。
5. 在含有 `index.html` 的網站資料夾開啟命令列，執行工具。

Windows：

```powershell
py -3 tools/add_pack.py data/custom-003.json --title "我的科技英語練習" --subtitle "規格確認・供應商合作"
```

macOS 或 Linux：

```bash
python3 tools/add_pack.py data/custom-003.json --title "我的科技英語練習" --subtitle "規格確認・供應商合作"
```

完成後，關閉再開啟網頁，或重新整理目前頁面；首頁會出現新題庫。不需手動加入 `<script>` 標籤。

`--title`、`--subtitle` 可省略，工具會讀取 JSON 根物件的 `title`、`subtitle`。若也未提供，首頁標題使用 `testId`，副標題使用「自訂擴充題庫」。

### 只檢查，不寫入

```bash
python3 tools/add_pack.py data/custom-003.json --check
```

Windows 可將上述 `python3` 換成 `py -3`。只檢查模式同樣會核對現有題庫的 ID 與媒體檔案是否存在。

### 指定另一個網站資料夾

預設目的地是工具所屬的網站資料夾，與命令列目前所在位置無關。需要指定其他目的地時：

```bash
python3 tools/add_pack.py /path/to/custom-003.json --site-dir /path/to/SHIFT-English-Lab-v1
```

輸入 JSON 的路徑依命令列所在位置解析；`--site-dir` 則須指向包含 `index.html`、`data/catalog.js` 的網站根目錄。

## JSON 格式

請使用 UTF-8 編碼。JSON 不接受註解、尾隨逗號、重複欄位名稱或 `NaN` 等特殊數值。

### 根物件

| 欄位 | 說明 |
|---|---|
| `schemaVersion` | 固定為數字 `1` |
| `testId` | 題庫的永久識別碼；工具接受 1～64 個英數字、連字號、底線，且以英數字開頭 |
| `title` | 可選；首頁顯示的題庫名稱 |
| `subtitle` | 可選；首頁顯示的簡短說明 |
| `groups` | 題組陣列；只有獨立 Part 5 題目時可填 `[]` |
| `questions` | 題目陣列；每包 1～5,000 題，JSON 檔不超過 20 MiB |

擴充包不必固定 200 題。可以建立 20 題文法、數組聽力，或完整的一回題目。若要仿照本版完整回次，Part 1～7 題數依序為 6、25、39、30、30、16、54，合計 200 題。工具不會把簡短題庫自動補成完整測驗。

### 題目物件

完整可用的單題範例已附在 `data/example-pack.json`。每題欄位如下：

| 欄位 | 說明 |
|---|---|
| `id` | 全網站不重複且長期固定的題目 ID |
| `testId` | 與根物件相同 |
| `number` | 本題庫內不重複的正整數；可保留正式 Part 編號，不強制從 1 連續排列 |
| `part` | 1～7 的整數 |
| `groupId` | 所屬題組 ID；只有 Part 5 可填 `null`，其他題型必須對應存在的題組 |
| `topic` | `technology`、`manufacturing`、`business`、`daily` 其中之一 |
| `difficulty` | `foundation`、`intermediate`、`advanced` 其中之一 |
| `tags` | 文字陣列，例如 `["delivery", "prepositions"]`；可填 `[]` |
| `prompt` / `promptZh` | 英文題幹／完整繁中題幹 |
| `options` | 選項陣列；Part 2 依序為 A、B、C，其餘依序為 A、B、C、D |
| `answer` | 唯一正解的選項 ID，例如 `"B"` |
| `explanationZh` | 完整繁體中文解析 |
| `evidence` | 支持答案的原文片段；文法題可寫出文法結構或搭配依據 |
| `vocabulary` | 至少一個詞彙物件，每個包含非空白的 `term`、`zh`、`note` |

每個選項都必須包含 `id`、英文 `text`、繁中 `zh`、具體理由 `whyZh`。正確選項說明為何成立；錯誤選項說明不符之處。選項內容不能完全重複。

題目與題組 ID 可使用 1～96 個英數字、句點、底線、冒號、連字號，第一個字元須為英數字。建議固定使用題庫前綴，例如 `custom-003-q001`，避免不同作者的題庫互相撞號。

### 題組物件

同一篇文章或同一段音訊只需存一個題組，再由多個題目的 `groupId` 引用。這樣抽題時才能保留共用素材與題組關係。

| 欄位 | 說明 |
|---|---|
| `id` / `testId` / `part` | 題組 ID、所屬題庫 ID、題型；Part 必須與引用它的題目相同 |
| `title` / `titleZh` | 題組英文標題／繁中標題 |
| `topic` | 四個主題分類之一 |
| `passage` / `passageZh` | 完整英文文章或逐字稿／完整繁體中文翻譯 |
| `audio` | Part 1～4 必填；例如 `audio/custom-003-g001.mp3` |
| `image` | Part 1 必填；例如 `assets/custom-003/scene-01.svg`；其他題型可依需要提供 |
| `duration` | 可選；音檔長度，單位秒，須為非負數 |
| `audioScript` | 可選；實際朗讀的英文文字，勿混入繁中翻譯或宣布正解 |
| `turns` | 可選；語音製作資料，每項包含 `voice`（`female` 或 `male`）與英文 `text` |

`groups` 不應保留未被任何題目引用的空題組。工具會檢查引用關係，但無法自動判斷語意是否只有一個正解；發布前仍需逐題確認答案、翻譯、音檔及圖片一致。

## 聽力與圖片檔案

題庫工具負責驗證及轉檔，**不會產生語音、繪製圖片或複製外部媒體**。即使填入 `audioScript`、`turns` 或 `imageScene`，仍必須提供實際的 `audio`／`image` 路徑與檔案。

| 資料 | 位置與支援格式 |
|---|---|
| 音檔 | `audio/` 以下；`.mp3`、`.wav`、`.ogg`、`.m4a` |
| 圖片 | `assets/` 以下；`.svg`、`.png`、`.jpg`、`.jpeg`、`.webp` |

為配合網頁與跨平台檔案路徑，請使用英數字、底線、連字號及句點命名，並使用小寫副檔名。目錄分隔符號固定為 `/`。檔名不得包含空白、中文、`..`、反斜線、網址、查詢參數或絕對路徑，也不能透過符號連結指向網站資料夾外部。工具會檢查媒體檔確實存在。

正確範例：`audio/custom-003/conversation-01.mp3`。

音訊內容應與題型一致：

- Part 1：朗讀 A～D 四個敘述，圖片須與唯一正解相符。
- Part 2：先朗讀問題或陳述，再朗讀 A～C 三個回應。
- Part 3／4：提供完整對話或短文，多題共用同一段音檔。

Part 1／2 作答時網頁只顯示選項字母；不要漏掉音檔內的選項。所有題型都在交卷後查看正解、逐字稿與解析。

## 更新既有擴充題庫

工具預設拒絕覆蓋任何已存在的題庫。確定要更新自己先前加入的題庫時，使用相同 `testId` 並加入 `--replace`：

```bash
python3 tools/add_pack.py data/custom-003.json --replace --check
python3 tools/add_pack.py data/custom-003.json --replace
```

內建 `test-01`、`test-02` 由工具保留，使用 `--replace` 也不能覆蓋。若要改編內建內容，請另用新的題庫、題目與題組 ID。

更新前請保留網站前一版，也在網站「資料管理」匯出學習紀錄。修正同一題的錯字可保留 ID；若更換題意、選項意義或正解，建議建立新 ID，避免原有作答紀錄套用到不同題目。工具不會刪除或修改瀏覽器內的學習紀錄。

工具會檢查所有登錄在 `data/catalog.js` 的發布題庫，拒絕跨題庫重複的題目或題組 ID。它不會讀取各使用者瀏覽器自行匯入的私有題庫，因此作者仍應採用獨立的 ID 前綴。

## 產生的檔案與發布方式

成功後，工具會完成兩件事：

1. 將輸入 JSON 包裝為 `window.SHIFT_PACKS.push(...)` 的 classic JavaScript，寫入 `data/題庫ID.js`。
2. 更新 `data/catalog.js` 的 `window.SHIFT_CATALOG.tests`，加入標題、讀聽題數、主題與題庫路徑。

目錄與題庫皆維持目前網站使用的包裝格式。工具只解析資料，不執行目錄或題庫中的 JavaScript；自訂加入函式、運算式或其他程式碼的目錄會被拒絕。不要手動把 JavaScript 程式寫進題庫 JSON。

輸入 JSON 是作者原始檔，可保留方便日後編輯。網站實際載入產生的 JS 檔；發布時請將更新後的完整資料夾與媒體一起分享或上傳。新增檔案後須重新整理網頁，已開啟的頁面不會自行掃描資料夾。

本機版可在桌面直接開啟 `index.html`。手機使用建議上傳完整資料夾至一般靜態網站主機。兩者都不需要網站後端，但學習紀錄仍屬於各自瀏覽器。
