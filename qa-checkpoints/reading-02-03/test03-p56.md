# Test 03 Parts 5–6 editorial QA (Q101–146)
Read all 46 stems, answer choices, Traditional Chinese glosses and rationales, and all four English/Chinese source passages. Keys unchanged. No audio, browser or full-exam acceptance claimed. For a changed English stem/option, make -r2 active ID and preserve the baseline original in legacyQuestions. For translation/rationale-only corrections keep the ID; where correct whyZh and explanationZh duplicate, update both.

## Before acceptance

- Q105 B although → so that; zh: 以便; whyZh: so that 表示目的；拒絕退款不會讓取消申請提早送達，這裡是在說明退款資格的必要條件。 Original although is grammatical if an on-time cancellation is denied for another reason. D remains unless; existing evidence. Improve correct explanation: unless 等於 if … not。未達提前 48 小時的要求就不予退款；達到時間要求則不等於保證退款。
- Q109: use existing Test 03 hunk of qa-checkpoints/reading-revisions.patch (t03-q109-r2 + original archived; A unchanged). Policy context and C familiar remove grammatically possible “available to enter” reading.
- Q121: generic direct-booking benefit could plausibly be a comprehensive breakfast; nonpayment explicit context secures keyed B. Prompt: Guests who book directly with the hotel do not have to pay the usual breakfast charge. They receive a ____ breakfast. promptZh: 直接向飯店訂房的旅客無須支付一般早餐費，可享用____早餐。 Evidence: Guests who book directly with the hotel do not have to pay the usual breakfast charge. They receive a complimentary breakfast. Correct explanation: 前一句說這些旅客不必付早餐費，complimentary breakfast 表示飯店免費招待的早餐。 C whyZh: comprehensive 表示內容完整或涵蓋廣泛，並未說明是否免費。
- Q130: original clause “while wearing protective gloves” has no clearly expressed wearer. Prompt: With the redesigned handle, users wearing protective gloves find the device easier ____. promptZh: 有了重新設計的握把，戴著防護手套的使用者會覺得裝置更容易____。 Evidence: With the redesigned handle, users wearing protective gloves find the device easier to operate. A remains to operate; current rationale applies.
- Q139 D launching → launches. “The site is launching to the public next month” is possible with intransitive launch (a website can launch), contrary to the rationale, and has almost same meaning as B. Keep English group passage. D zh: 上線（第三人稱單數）; whyZh: launches 是限定動詞；題幹已有 is，不能直接再接 launches。 B whyZh/explanationZh: is launched 是被動結構，指網站下個月正式向大眾推出。 Evidence unchanged.
- Q138 A explanation currently says the opposite of “unless visiting”. A whyZh: unless visiting 意思是「除非去服務台，否則可以詢問館員」，把到服務台變成例外；此處反而把到服務台當作詢問的時機。
- Q128 promptZh loses neither/nor. Replace: 專案經理與兩位設計師今天早上都沒空開會。（英文空格測試 be 動詞。） D rationale: was 是單數形式，與較接近的複數主詞 the two designers 不一致；this morning 本身不一定排除過去式。
- Q140 A zh adds an unsupported attachment. Replace: 另有一組虛構的付款卡資料供測試。 Correct rationale: 提供虛構的付款卡資料，讓測試者不必輸入個人財務資訊也能操作付款畫面，正好承接後句。

## Additional accurate glosses/rationales

- Q101 A zh: 而；相較之下。 Whereas introduces a contrasting clause, not necessarily standalone 然而.
- Q102 promptZh: 應徵者須提供兩位推薦人，____曾督導其工作。 D whyZh: 正式書面英文中，either of whom 在此表示兩位中的任一位，通常搭配單數 has；both of whom 搭配 have 並表示兩位皆符合。
- Q103 C zh: 報銷；核銷後退還。 Correct rationale: reimburse your expenses 指退還您先行支付的費用，收據正本是會計核銷的憑證。
- Q110 C zh: 屆時已完成。
- Q116 promptZh: 飯店地點便利，位於從火車站步行可達的範圍內。（英文空格測試表示範圍的介系詞。） Original blank appeared after 範圍內.
- Q117 C zh: 取決於（dependent on）。
- Q118 B whyZh: have 是複數形式，與 Each of ... 的單數主詞不一致；本句也指下個月才會展示。
- Q119 C whyZh: through 作介系詞可表示「穿過」；在這裡要用 thorough 修飾 inspection，表示檢查仔細而完整。 Avoid generalizing that through can only be a preposition.
- Q120 A zh: 關係代名詞，指三位候選人。 B zh: 他們（人稱代名詞受格）。
- Q122 B rationale: no later than Friday afternoon 指最遲須在星期五下午提交，也可以更早；星期五下午本身不被排除。
- Q127 promptZh: 設備必須仍裝在____包裝內，才能退貨。
- Q129 promptZh: 市政府將____合格承包商提交的投標文件，收件截至五月十二日。 Contractors submit bids, not a government 標案. B whyZh: access 指取得存取權或查看，不表示受理投標。 D rationale: accept bids 指收受投標文件，符合政府公告的收件截止語境。
- G055 passageZh receipt sentence: 請在貨車離開前，將這張收據與您自己的紀錄核對。 Old only said check your records, loses comparing receipt to records.
- G055 passageZh heaters sentence: 為避免這類損壞，請將所有運輸箱放在室內，並 [133] ____ 暖氣設備與陽光直射處。 Q133 B zh: 遠離（away from）。
- G056 passageZh Q135 sentence: 地圖館藏已移至二樓參考資料區，在正常開館時間仍 [135] ____。 Q135 D zh: 可供查閱的。 Avoid preceding 可 in passage repeating gloss.
- G056 passageZh Q138 sentence: 在開放日前有需要的人，可以在 [138] ____ 服務台時向館員詢問。 Q138 D zh: 前往（while visiting 合譯為「前往……時」）。
- G057 passageZh Wednesday sentence: 週三將寄送非公開的預覽連結，以及一份待完成的任務清單。 Remove unsupported “short”; “private” = access restricted, not literally personal.
- Q141 A zh: 多麼；到什麼程度。 Focus on degree, not method. Optional improve G057 sentence: 我們特別想了解，比較不同的出遊日期有 [141] ____ 容易。
- Q142 A rationale: implement improvements 表示將改進措施付諸實行，不只是同意或採納建議。
- G058 first shipment passageZh: 首批預定十月出貨。最遲在九月二十日收到的訂單將優先寄出，[145] ____ 較晚收到的訂單可能要到十一月才會送達。 “by” includes September 20, and arrival is not dispatch. Q145 A rationale: while 表示對比：在期限內收到的訂單優先出貨，較晚收到的訂單則可能要到十一月才送達。

Other scoped items have no identified ambiguity that changes the key. Q131 “reserve empty crates by size” is significantly weaker than sorting in collection context and follow-on instruction; Q137 “repaired to other members” cannot communicate reallocation; all sentence insertions (Q132/136/140/144) connect to adjacent reference words and paragraph goals.

Verified key fingerprint: BACCDCDAACBDDADACCDABBADCABADA / BDBADCADBAAACCAA
