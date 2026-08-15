---
name: tracemark
description: Generate artistic commemorative seal/postcard imagery from a photo and a one-line theme, in three cultural tracks (Chinese zhuan seal 中式篆刻, Japanese craft stamp 日本のはがき印, Western wax seal 西式火漆). Trigger when the user wants to add a decorative seal or stamp to a photo or postcard 给照片盖章; turn a photo into a postcard with an artistic seal; generate a seal-style graphic for a journal, gift, or social post; create monogram or wax-seal-style ornament 制作装饰性印章或火漆印. Do NOT use for real/official seals 真实公章, authentication stamps 认证印章, documents needing legal validity, or copying existing trademarks. Always render through the unified entry scripts/tracemark.py (AUP gate is enforced inside the pipeline). Read AUP.md first. Follow research/*.md for cultural design rules.
---

# TraceMark 痕迹追溯

Artistic decorative seal/postcard synthesis from photo + one-line theme.
Trace every mark. 痕迹追溯。

> Languages / 語言切換：[简体中文](docs/zh-hans.md) · [繁體中文](docs/zh-hant.md) · [粵語](docs/yue.md) · [English](docs/en.md) · [日本語](docs/ja.md) · [Français](docs/fr.md)
> 六语完整版文档存于 `docs/` 目录；AUP.md 六语版见 AUP.md。

## 路由表（先读 AUP.md，再查可用性）

| 轨道 | 触发 | 模板 |
| --- | --- | --- |
| zh（中式篆刻） | 中文名/斋馆/吉语/城市纪念 | 模板：zh-square-zhu 朱文方印 / zh-square-bai 白文方印 / zh-circle-leisure 圆闲章 |
| jp（日式 craft） | 片假名/日式文具感/駅スタンプ风 | 模板：jp-circle-stamp 圆形墨晕戳 |
| wz（西式火漆） | monogram/婚礼/礼品/品牌信封 | 模板：wz-wax-monogram 蜡封圆印 |

模板由 config.yaml 的 `template:` 字段路由（可选，缺省走轨道默认模板）。

**用途型可用性**（v1.0）：风控按用途而非关键词——政治表达、公共人物、机构、国家、历史题材与讽刺作品均可出现；被拦的是任何认证用途与复刻现存官方印鉴的意图。政治/机构/讽刺题材被拒时，管线会说明被拦的是哪个用途并给出改法，温和引导而非报错。见 AUP.md。

## 使用流程

1. 撰写 `config.yaml` 放入用例目录；照片放同目录，`photo: input.jpg`（相对 config 目录解析，永不用 cwd）
2. `python3 scripts/tracemark.py render --config <用例目录>/config.yaml` → 输出 1200×1600 JPEG (q88)；`--no-photo` 生成纯印章成品（齿孔+TRACE·ART 强制在位）
3. 单跑风控：`python3 scripts/tracemark.py validate "<文字>" "zh"`（track zh|jp|wz 或 mode seal|stamp|postcard 均可，自动推导）；风控被拒会温和引导而非报错
4. 成品合规扫描：`python3 scripts/tracemark.py audit <output.jpg>`（非空白+齿孔/边框+TRACE·ART+画幅指纹+sidecar 元数据一致性）；每次 render 完成后管线强制自动审计一次，结果写 `output.tracemark.json`
5. 环境健康检查：`python3 scripts/tracemark.py doctor`（依赖/字体/写目录）；freetype-py 缺失会硬报错，禁止静默降级
6. 边界用例在 config 中写 `_expect: fail`（缺字）或 `_expect: reject`（风控）供 run_examples.py 断言；新用例按 `input.jpg + prompt.txt + config.yaml + output.jpg` 配对存入（examples 即回归评测集）
7. 依赖：`pip install -r requirements.txt`（Pillow>=10 / PyYAML / numpy / freetype-py；缺字检测读字体真实 cmap——豆腐块一律 FAIL，渲染管线全程无法跳过风控）

概念分层：`track`（文化轨道 zh/jp/wz）→ `format`（印章/邮票/明信片，由轨道推导）→ `template`（布局：zh-square-zhu / zh-square-bai / zh-circle-leisure / jp-circle-stamp / wz-wax-monogram，覆盖 format 与风格）→ `purpose`（用途，风控唯一维度）。模板有容量上限（方印 8 字、圆闲章 4 字、monogram 3 字母）：超限硬报错，严禁截断用户原文。

## 关键约束（违反即返工）

- 成品必须保持艺术化边框/齿孔/微字，任何配置不得绕过（法律防线）
- 文字渲染失败（豆腐块/缺字）必须报错，不得输出残缺成品
- 严禁静默截断、重写或忽略用户原文：超限/缺字/模板不匹配一律硬报错并给出改法
- 钤印肌理（旋转/位移/墨晕）必须启用，不得输出完美几何印面
- 不生成仿真印鉴：成品与真实印章在尺寸与细节上必须可感知区分

## 迭代纪律

- 每个 release 必须附带用户可见的变化（新模板/新肌理/新用例）
- 新模板必须先写考据（文化原型/尺寸/读序/用色）再进 render.py；每个模板对应至少一个 examples/ 用例且回归通过
