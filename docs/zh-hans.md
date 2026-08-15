# TraceMark 痕迹追溯（简体中文）

Artistic decorative seal/postcard synthesis from photo + one-line theme.
Trace every mark. 痕迹追溯。

## 路由表（先读 AUP.md，再查可用性）

| 轨道 | 触发 | 模板 |
| --- | --- | --- |
| zh（中式篆刻） | 中文名/斋馆/吉语/城市纪念 | render.py 内置（朱文方印/白文方印/圆闲章） |
| jp（日式 craft） | 片假名/日式文具感/駅スタンプ风 | render.py 内置（圆形墨晕戳） |
| wz（西式火漆） | monogram/婚礼/礼品/品牌信封 | render.py 内置（蜡封圆印） |

**用途型可用性**：风控按用途而非关键词——政治表达、公共人物、机构、国家、历史题材与讽刺作品均可出现；被拦的是认证用途与复刻现存官方印鉴的意图。见 AUP.md。

## 使用流程

1. 撰写 `config.yaml`（schema 见 en.md）。AUP 风控校验由渲染管线自动强制执行——无法跳过，无需单独运行校验器
2. 准备输入照片，放在用例目录下并在 config 中写相对路径（`photo: input.jpg`）
3. `python3 scripts/tracemark.py render --config examples/<case>/config.yaml` — AUP 校验/路径解析/EXIF/缺字检测在管线中强制执行，无法跳过；`--no-photo` 生成纯印章成品
4. 目检质量门：逐字比对文字零翻车、永久微字 "TRACE·ART" 在位、齿孔/艺术边框在位
5. 新用例按 `examples/<case>/input.jpg + prompt.txt + config.yaml + output.jpg` 配对存入（examples 即评测集）

## 关键约束（违反即返工）

- 成品必须保持艺术化边框/齿孔/微字，任何配置不得绕过（法律防线）
- 文字渲染失败（豆腐块/缺字）必须报错，不得输出残缺成品
- 钤印肌理（旋转/位移/墨晕）必须启用，不得输出完美几何印面
- 不生成仿真印鉴：成品与真实印章在尺寸与细节上必须可感知区分

## 迭代纪律

- 每个 release 必须附带用户可见的变化（新模板/新肌理/新用例）
- 新模板必须先写考据（文化原型/尺寸/读序/用色）再进 render.py；每个模板对应至少一个 examples/ 用例且回归通过
