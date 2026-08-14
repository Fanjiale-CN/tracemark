# TraceMark 痕跡追溯（粵語）

Artistic decorative seal/postcard synthesis from photo + one-line theme.
Trace every mark. 痕跡追溯。

## 路由表（先睇 AUP.md，再查可用性）

| 軌道 | 觸發 | 模板 |
| --- | --- | --- |
| zh（中式篆刻） | 中文名/齋館/吉語/城市紀念 | render.py 內置（朱文方印/白文方印/圓閒章） |
| jp（日式 craft） | 片假名/日式文具感/駅スタンプ風 | render.py 內置（圓形墨暈戳） |
| wz（西式火漆） | monogram/婚禮/禮品/品牌信封 | render.py 內置（蠟封圓印） |

**類別可用性**：印章軌道唔接受公司、機構、政府名稱（validate_input.py 會拒絕並溫和咁引導你轉去郵票樣式）；郵票同明信片樣式就完全用得。見 AUP.md。

## 使用流程

1. `python3 scripts/validate_input.py "<輸入文字>" "<軌道>"` → 通過咗先繼續
2. 準備輸入相（V1 直接用相就得）
3. `python3 scripts/render.py --config examples/<case>/config.yaml` → 輸出 1200×1600 PNG
4. 目檢質量門：逐隻字核對零翻車、永久微字 "TRACE·ART" 在位、齒孔/藝術邊框在位
5. 新用例照 `examples/<case>/input.jpg + prompt.txt + config.yaml + output.jpg` 配對存入（examples 就係評測集）

## 關鍵約束（違反即返工）

- 成品必須保持藝術化邊框/齒孔/微字，任何配置都繞唔過（法律防線）
- 文字渲染失敗（豆腐塊/缺字）必須報錯，唔可以出殘缺成品
- 鈐印肌理（旋轉/位移/墨暈）必須啟用，唔可以出完美幾何印面
- 唔生成仿真印鑑：成品同真實印章喺尺寸同細節上必須可感知區分

## 迭代紀律

- 每個 release 必須附帶用戶見得到嘅變化（新模板/新肌理/新用例）
- 新模板必須先寫考據（文化原型/尺寸/讀序/用色）先入 render.py；每個模板對應至少一個 examples/ 用例且回歸通過
