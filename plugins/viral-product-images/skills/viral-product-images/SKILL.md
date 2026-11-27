---
name: viral-product-images
description: 欧美市场爆款产品图全自动产线（跨品类独立站 PDP 黄金 7 图 + Meta 高转化投流静图）：给任意独立站商品链接或实拍图（裙子、椅子、床边柜、灯具、化妆镜等），严格按「核验真实商品与实拍排雷 → 拆解欧美热销 Listing 套图与高消耗静图广告 → muse-image 多图锚定生成 100% 无字高清底图并肉眼质检 → 底图与文字分离的欧美极简排版引擎合成（主图/场景/解剖标注/英制尺寸标尺/Before-After/Us vs Them/信任背书）→ 多比例交付并无缝衔接 viral-product-video」闭环产出欧美转化级套图。凡用户要求"复刻爆款产品图"、"做一套欧美商品详情图/主图"、"生成 FB/Meta 静图广告"、"画产品尺寸图/解剖卖点图/对比图"时使用。
---

# 欧美爆款产品图产线（viral-product-images）

与 [viral-product-video](../viral-product-video/SKILL.md) 互为姐妹产线：**先用本产线低成本复刻欧美高转化商品套图与 FB 静态测试图，验证视觉与点击率（CTR）后，直接把表现最好的「无字高清底图（`assets/clean_base/`）」喂给 `viral-product-video` 生视频，实现一鱼两吃、零重复抽卡。**

---

## 核心纪律（欧美高转化四铁律）

1. **底图与文字严格分离**：`muse-image` 只负责产出 **100% 无字、无标尺、无水印的高清实景/棚拍底图**（`no text, no labels, no numbers, no watermark`）；所有英文标题、尺寸标尺、箭头标注、对比表、徽章一律由下游代码排版层精准叠图（AI 直接画字必拼错、必显廉价）。
2. **彻底去除“国内电商味”**：拒绝死白惨亮影棚、过度磨皮网红脸、大红大黄促销爆炸贴。欧美高客单审美标准 = **自然窗光/柔和侧光 + 真实肌理/面料自然褶皱 + 每张图只讲 1 个卖点 + 留白 ≥ 35% + 英文文案 ≤ 8–12 词**。
3. **单位与宣称彻底美标化 & 零编造**：尺寸主标 **英寸（`in` / `"`）**、重量用 **磅（`lbs`）**、货币用 **USD**；每条标注回链官网原文（`claims_basis`），错图剔除，全套锁死同一配色与真实部件数。
4. **平台合规红线**：P1 列表主图必须 **零文字、零角标、零水印**（否则 Google Merchant Center / Amazon 直接拒审）。

---

## 5 步标准流水线

### Stage 0：商品核验与实拍排雷
1. 拉取商品页（JSON-LD + 正文规格 + FAQ + 精确长宽高/材质/价格/运费质保），下载全部商品图至 `投流素材/<campaign>/assets/src/`。
2. **必须用 `read_file` 逐张检查商品图**：
   - 核对真实外形、配色、按键/五金/部件数，**剔除画廊里混入的错图**；
   - 产出「允许宣称清单（含美制换算尺寸）」与「严禁编造红线」。

### Stage 1：拆解欧美爆款套图 & 静图广告（Gate 1 选定风格蓝图）
1. 按当前商品真实品类，收集 1–3 个欧美标杆参考：
   - **站内 PDP 套图**：Amazon US 同类 Top 3–5 Best Sellers（4.5★+、1,000+ 评）的 7–9 张主图序列，或欧美头部独立站 PDP（家居看 West Elm / CB2 / Castlery，服饰看 Reformation / Aritzia，美妆工具看 Simplehuman / Fancii）；
   - **投流静图**：Meta Ads Library 筛 `Image` + `在投 ≥ 60 天` 的常青静图（Before/After、Anatomy 解剖标注、Us vs Them）。
2. 拆解出 `gallery_blueprint.md`（每张图的景别、光线色板、留白方位、唯一核心卖点、版式类型），**停在用户面前拍板确认**（若用户已直接提供参考图，则直接拆解参考图执行）。

### Stage 2：规划「欧美 7+3 黄金套图矩阵」并生成无字底图（Gate 2 视觉质检）

标准产出 **7 张独立站 PDP 套图（原生 `1:1`） + 3 张 Meta 投流静图（`1:1` & `4:5`）**：

| 编号 | 角色 | 版式模板（`render_dtc_cards.py`） | 核心任务与规范 |
|---|---|---|---|
| **P1** | 列表主图（Hero） | `hero_clean` | 纯白/极简浅灰棚拍全貌，**100% 零文字零贴纸**（GMC / Amazon 合规） |
| **P2** | 场景氛围主图 | `hero_clean` 或 `lifestyle_title` | 欧美真实中产家居/自然人货同框，激发占有欲 |
| **P3** | 核心卖点解剖图 | `callout_anatomy` | 无字底图 + 3–4 条细指示线与短英文标签（每条 ≤ 4 词） |
| **P4** | 细节材质微距 | `lifestyle_title` | 五金/缝线/木纹/灯珠/面料特写，打消廉价顾虑 |
| **P5** | 尺寸参照图 | `dimensions` | 正面正交干净图 + 程序绘制精确标尺与 **英寸主标**（如 `12.99" × 11.81"`） |
| **P6** | 痛点/方案对比 | `split_compare` 或 `us_vs_them` | 左普通款/痛点 vs 右我方真品，或简洁 Us vs Them 核验表 |
| **P7** | 配件与信任背书 | `lifestyle_title` | 配件全家福/礼赠氛围 + 免邮/30 天退货/质保徽章 |
| **Ad-1..3** | Meta 投流静图 | `split_compare` / `multi_panel` / `us_vs_them` | 默认输出 `1:1`（`800×800`）测点击率；特别指定时支持 `4:5`（`800×1000`）或更高规格 |

**执行无字底图生成与质检**：
```bash
python3 <skill_dir>/scripts/run_muse_images.py \
  --doc images.json --ids all --workers 2 --retries 2
```
- 无字底图统一保存在 `assets/clean_base/`，脚本自动生成 `assets/clean_base/clean_base_sheet.png`。
- **硬门禁**：必须用 `read_file` 逐张核验每一张底图：
  - 商品外形、配色、部件数量与官网真图 100% 一致；
  - **真实物理比例防失真检查（必查）**：当白底锚点图被放进家居/浴室/桌面/卧室场景时，Prompt 必须显式锚定**商品真实物理尺寸及与周边参照物的比例关系**（如 8 寸镜面直径 ≈ 20 cm ≈ 水龙头高度的 1.3–1.5 倍、占画面宽度 28%–35%，切忌让小件商品在场景里膨胀成“巨无霸”，也不可让大件家具缩水成玩具）；肉眼核验参照物（水龙头/毛巾/枕头/手掌/人物）比例失真时必须立即重写 Prompt 重抽；
  - 人货同框遵守 3/4 空间物理约束（不出现人跑到商品背面、多余断手、手指穿模）；
  - 画面内 **零 AI 乱码文字、零多余水印**，且在预定排版方位留足干净留白区；
  - 坏图立刻改 Prompt 单张重跑（`--ids P3`），绝不带病进排版层。

### Stage 3：高定排版合成（底图 + 欧美极简视觉层）
- **默认分辨率规范（用户明确要求，永久生效）**：所有方形套图与 1:1 广告图**默认输出 `800×800`**（4:5 静图默认 `800×1000`），除非用户特别说明需要更大尺寸（如 2000×2000）；1600×1600 原底图 2× 下采样至 800×800 反而更锐利且加载更快。
- **零锯齿排版铁律**：严禁在 PIL RGBA 底图上直接 `ImageDraw.Draw(im)` 绘制半透明条或空背景矩形（会破坏 Alpha 通道产生黑框与文字锯齿）；`render_dtc_cards.py` 已内置 **独立透明层 `Image.alpha_composite` + 4× 超采样（3200×3200 → Lanczos 缩至 800×800）+ `Helvetica Neue` 字体 + JPEG `subsampling=0`（4:4:4 无色度抽样）**，确保边缘绝对顺滑无锯齿。

编写 `cards.json` 映射每张质检通过的无字底图与核验英文文案，一键输出全套成品：
```bash
python3 <skill_dir>/scripts/render_dtc_cards.py --doc cards.json
```
脚本会自动产出 `final/gallery_qa_sheet.png` 全套总览图（按「版式 + 底图 + 文案」精确去重：完全一样的重复克隆图自动过滤，文案或构图有差异的 Meta 投流图保留并用 `[AD]` 橙黄色标签与 `[PDP]` 绿色标签区分；如需强制包含全部可加 `--all-in-qa`）。

### Stage 4：终审验收、交付与视频产线联动
1. **必须用 `read_file` 审阅 `final/gallery_qa_sheet.png`**（及重点高密度图如 P3/P5/P6）：
   - 标注线是否精准指向对应部件、不压住产品核心区域？
   - 尺寸数字、价格、英文拼写是否 100% 准确无误？
   - 全套 7 张图色温、留白、字体层级是否像同一个欧美 DTC 品牌？
2. 交付完整目录：
   - `final/pdp/`（P1–P7 站内默认 `800×800` 高清图，已按上线顺序编号）；
   - `final/ads/`（Ad-1..3 默认 `800×800` Meta 投流静图）；
   - `assets/clean_base/`（**无字高清底图库 `1600×1600`**——后续测出高 CTR 后直接交接给 `viral-product-video` 生成视频！）；
   - `copy.md`（配套 FB/IG 静图文案）+ `asset-pack.md`（全图清单与使用映射）。

---

## 随包工具脚本（`<skill_dir>/scripts/`）

| 脚本 | 用途 |
|---|---|
| `run_muse_images.py` | 驱动 `muse2api` (`muse-image`) 按多比例（`1:1`/`4:5`/`3:4`/`9:16`）并发生成无字高清底图，内置 HTTP 202 异步兼容、自动重试、自动拼出 `clean_base_sheet.png` 供质检 |
| `render_dtc_cards.py` | 欧美 DTC 极简排版引擎（4× 超采样抗锯齿 + 独立透明层 RGBA 合成 + `Helvetica Neue` + JPEG 4:4:4），支持 `hero_clean`、`lifestyle_title`、`callout_anatomy`、`dimensions`、`split_compare`、`multi_panel`、`us_vs_them` 7 种版式，默认 `800×800` 一键出图并自动拼出精准去重+分色标签的 `gallery_qa_sheet.png` |
