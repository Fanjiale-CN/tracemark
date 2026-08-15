# TraceMark 痕跡追溯（繁體中文）

Artistic decorative seal/postcard synthesis from photo + one-line theme.
Trace every mark. 痕跡追溯。

## 路由表（先讀 AUP.md，再查可用性）

| 軌道 | 觸發 | 模板 |
| --- | --- | --- |
| zh（中式篆刻） | 中文名/齋館/吉語/城市紀念 | render.py 內置（朱文方印/白文方印/圓閒章） |
| jp（日式 craft） | 片假名/日式文具感/駅スタンプ風 | render.py 內置（圓形墨暈戳） |
| wz（西式火漆） | monogram/婚禮/禮品/品牌信封 | render.py 內置（蠟封圓印） |

**用途型可用性**：風控按用途而非關鍵詞——政治表達、公共人物、機構、國家、歷史題材與諷刺作品均可出現；被攔的是認證用途與復刻現存官方印鑑的意圖。見 AUP.md。

## 使用流程

1. 撰寫 `config.yaml`（schema 見 en.md）。AUP 風控校驗由渲染管線自動強制執行——無法跳過，無需單獨運行校驗器
2. 準備輸入照片，放在用例目錄下並在 config 中寫相對路徑（`photo: input.jpg`）
3. `python3 scripts/tracemark.py render --config examples/<case>/config.yaml` — AUP 校验/路径解析/EXIF/缺字检测在管线中强制执行，无法跳过；`--no-photo` 生成纯印章成品
4. 目檢質量門：逐字比對文字零翻車、永久微字 "TRACE·ART" 在位、齒孔/藝術邊框在位
5. 新用例按 `examples/<case>/input.jpg + prompt.txt + config.yaml + output.jpg` 配對存入（examples 即評測集）

## 關鍵約束（違反即返工）

- 成品必須保持藝術化邊框/齒孔/微字，任何配置不得繞過（法律防線）
- 文字渲染失敗（豆腐塊/缺字）必須報錯，不得輸出殘缺成品
- 鈐印肌理（旋轉/位移/墨暈）必須啟用，不得輸出完美幾何印面
- 不生成仿真印鑑：成品與真實印章在尺寸與細節上必須可感知區分

## 迭代紀律

- 每個 release 必須附帶用戶可見的變化（新模板/新肌理/新用例）
- 新模板必須先寫考據（文化原型/尺寸/讀序/用色）再進 render.py；每個模板對應至少一個 examples/ 用例且回歸通過
