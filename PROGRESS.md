# TraceMark V1 — 完成状态（2026-08-15）

## 仓库：/home/ubuntu/tracemark（尚未 git init / 未推送）

V1 引擎全部通过：三轨道渲染（zh 中式朱文方印篆体田字格 / jp 日式圆形墨晕戳 / wz 西式火漆浮雕）+ 风控校验（seal 禁机构名三语引导，postcard 放行）+ 三个 examples 用例回归全部 ok。

## 最终文件清单
SKILL.md / README.md / AUP.md（中英日三语）/ FONTS.md / LICENSE（MIT）
scripts/{render.py, texture.py, validate_input.py, run_examples.py}
examples/{shanghai-sunrise, kyoto-lantern, wax-monogram}/（input+prompt+config+output 配对）
fonts/{yishanbeizhuanti.ttf(峄山碑篆体，字传自定义许可可再分发须署名), noto-serif-jp.ttf(OFL), playfair-display.ttf(OFL)}
research/{chinese,japanese,western}_seal_culture.md

## 推送前待办
1. 删除 scripts/__pycache__（再删一次，run 后又生成了）
2. git init + add + commit "feat: TraceMark V1 — 三文化盖章明信片合成引擎"
3. 推送：gh repo create Fanjiale-CN/tracemark --public 2>/dev/null 或用用户确认的名字
   - 注意：用户账号 Fanjiale-CN，开源 skill 必须 public
4. 交付三张成品图给用户测试

## 关键决策记录（历史）
- 英文名 TraceMark（tracemark 在 GitHub 仅 3 个 0-3 星小仓，无占用）；域名 tracemark.ink 备选（~3美元，未注册）
- 风控：seal 禁公司/机构/政府名；stamp/postcard 全放开（类别可用性，非关键词狩猎）
- 演示站 V1 不做（gh-pages 画廊是后续），V1 纯 skill
- 中式首发：但三轨道全部实现（jp/wz 为最小模板，符合"仓库结构三文化并立"决策）
- 输入照片：zh 用例用了 galok 上海 hero 图（外滩1886黑白照）

## 目检结论
三轨道全部合格（analysis 记录在沙盒 /home/ubuntu/tracemark 外部备份）


# 多语言文档任务（2026-08-15，进行中）

用户要求：SKILL 说明增加六语言版本——简体中文、繁體中文、粵語、English、日本語、Français，让人们在底部选择语言，做完推送 main。

## 架构决定
- README.md：重写为单一入口 + 顶部语言切换锚点表 + 六个语言区块（已完成）
- AUP.md：重写为六语言区块 + 顶部切换（已完成）
- SKILL.md：description 增加中英日触发词混合；加语言切换导航块（已完成）
- docs/ 目录存放六语完整版：zh-hans.md ✅、zh-hant.md ✅，待写：yue.md / en.md / ja.md / fr.md
- 完成后 git add -A && commit "docs: six-language README/AUP/SKILL" && git push origin main

## 关键事实
- 仓库：Fanjiale-CN/tracemark（public），本地 /home/ubuntu/tracemark，main 分支
- 粤语文案要点：口语书面混合（"係""俾""嘅""喺""呢個"），与繁中区分开
- 法语版 AUP 标题：Politique d'utilisation acceptable
