---
name: viral-product-video
description: 跨品类商品真实推广视频全自动产线（爆款复刻商拍产线）：给任意独立站商品链接或实拍图（裙子、椅子、床边柜、灯具、化妆镜等），严格按「核验真实商品与实拍 → 检索同款高播爆款并验图选片 → yt-dlp 下载逐秒抽帧拆解 → 1:1 复刻爆款骨架并注入我方真实卖点 → muse2api 关键帧+分镜双重视觉质检 → 精剪成片+音效+安全区字幕+三比例静图交付」闭环产出可投流成品。凡用户给一个商品链接/SKU 要求"分析生成推广视频"、"找同款爆款复刻拍一条广告"、"用 muse2api 出商品带货视频"、"人货同框推广视频"时使用。
---

# 爆款复刻商拍产线（viral-product-video）

面向任意独立站商品（服饰、家具、家居、美妆工具、灯具等）的**端到端真实商品推广视频流水线**。核心原则：

1. **严格按实际商品走，绝不套固定品类模板**：先查清当前商品的真实外形、卖点、价格与“没有的功能”，再找该形态的真实爆款原片拆解。
2. **先看真片再复刻，绝不凭标题脑补**：爆款视频必须下载后逐秒抽帧看画面，再 1:1 复刻其运镜、节奏与情绪曲线。
3. **人货同框先在图片阶段锁死商品**：绝不让生视频模型同时自由发挥“画准商品 + 空间物理 + 动作”，全部在 `muse-image` 关键帧阶段肉眼过关后，才进 `muse-video`。
4. **实证优先、零虚假宣称**：每一条字幕与文案必须有商品页原文支撑（`claims_basis`），错图剔除，禁用未核验参数。

---

## 6 步标准流水线（每步带硬门禁）

### Stage 0：商品核验与实拍排雷
1. 拉取目标商品页（JSON-LD + 正文规格 + FAQ + 价格 + 运费/质保政策），下载商品画廊全部图片至 `投流素材/<campaign>/assets/src/`。
2. **必须用 `read_file` 逐张查看下载的商品图**：
   - 核对真实外观细节（配色、部件数量、材质、按键/接口位置）；
   - **剔除混入画廊的错图/不同规格图**（实战教训：`LW-80` 官网画廊混入了 12 灯泡带 10X 错图，真实商品是 9 灯泡 1X）；
   - 建立两张表：**允许宣称清单**（带原文依据）+ **严禁编造红线**（如插电款禁写无线/电池、1X 镜禁写 10X、无蓝牙禁写蓝牙）；
   - **单一配色锁定**：单条视频从头到尾只用 1 个配色，严禁跨镜换色。

### Stage 1：同款高播爆款检索与验图选片（Gate 1 停在用户面前）
1. 用 `scripts/find_viral_yt.py` 按当前商品的**具体形态关键词**检索 YouTube / Shorts 高播放短视频（`< 90s` 优先），脚本会自动拉取真实播放量、时长、作者、描述，并拼出 2×3 缩略图质检图 `candidates_sheet.png`：
   ```bash
   python3 <skill_dir>/scripts/find_viral_yt.py \
     --queries "wood nightstand bedside table #shorts" "modern nightstand #shorts" \
     --out 投流素材/<campaign>/viral_candidates
   ```
2. **必须用 `read_file` 查看 `candidates_sheet.png` 过滤形态不符的错款**（例如搜好莱坞镜会混入平板灯镜，搜床边柜会混入 DIY 教程）。
3. 列出 3–5 条已核验同款高播视频（含真实播放量、时长、链接、实看特点与推荐理由），**停下让用户拍板选 1 条**（或由用户提供自己刷到的 TikTok/IG/YouTube 链接）。
4. **双轨兜底规则**：若某个冷门细分形态全网没有大爆款（如 8 寸桌面圆镜最高仅 35K），如实告知用户，采用「同款实证结构 + 跨形态借 0–3s 情绪钩子」双轨法，但画面严守我方商品真实使用场景。

### Stage 2：下载原片与逐秒实证拆解
1. 用 `scripts/analyze_viral.py`（内置 `yt-dlp` 自动寻址 + `ffmpeg` 1fps 抽帧）下载选中的原片并生成逐秒时间轴拼图 `viral_timeline_sheet.png`：
   ```bash
   python3 <skill_dir>/scripts/analyze_viral.py \
     --input "<用户选中的链接或本地mp4>" \
     --sku "<listing.md路径>" \
     --out 投流素材/<campaign>/ref --skip-llm
   ```
2. **必须用 `read_file` 逐帧查看时间轴拼图**，输出 `viral_breakdown.md`，严格拆清 6 维：
   - 呈现形式（人货同框 UGC / 纯商品美学扫镜 / 痛点对比 / 对镜自拍）；
   - 0–3s 视觉+文案双钩子；
   - 情绪痛点与爽点落点；
   - **逐拍真实时间轴**（每拍起止秒数、精确机位/运镜方向、商品占比、转场方式）；
   - 爆火底层归因；
   - 1:1 复刻到我方商品的映射表（剔除我方没有的功能，注入我方差异化优势与价格锚点）。

### Stage 3：写 `shots.json`（多图参考关键帧 + 单动作分镜）
- 呈现形式跟随所选爆款：
  - **人货同框型**（如服饰穿搭、家具试坐、美妆试用）：先用 `muse-image` 固定 1 张人设母版 `K0_character_ref.png`，再用 `images: [K0/K1, 真实商品图]` 生成每镜首帧；
  - **纯商品美学型**（如 12s 高完播梦想梳妆台/家具展示）：直接用 `images: [真实商品图]` 生成 `K1` 主场景，后续不同机位/色温关键帧均锚定 `[K1, 真实商品图]` 保持房间与摆件像素级锁定。
- **Prompt 铁律**：
  - 每镜 **只做 1 个单一连续动作**，尾缀 `Single continuous motion, no text, no watermark`；
  - **锚定主场景防漂移**：尽量让 `K2..Kn` 都直接锚定 `K1 + 真品图`（并行提速且零色偏累积），而非串行滚雪球；
  - **人货空间物理约束（踩坑总结）**：涉及镜子/屏幕/朝向性家具时，Prompt 必须显式写清 3/4 空间位置（例如“人物坐左侧 3/4 面向右侧商品，商品在右侧斜向朝她，**绝不把人放到商品背面，画面前景不出现多余断手**”）；
  - **时段/背景锁定**：多镜同场景切换灯光或动作时，显式写 `KEEP THE EXACT SAME window lighting and room background from image 1`，防窗外天色突然从黄昏跳成白天。

### Stage 4：`muse2api` 关键帧生成 → 视觉质检 → 视频生成 → 密集抽帧质检
1. **前置配置**：工作目录放 `.muse.env`（`MUSE_BASE=...` / `MUSE_KEY=m2a_...`），**确保 `*.env` 与 `.muse.env` 在 `.gitignore` 中，绝不入库**。
2. **Stage 4A · 生成关键帧并逐张肉眼质检**：
   ```bash
   python3 <skill_dir>/scripts/run_muse.py --stage keyframes --ids K1 --retries 2
   python3 <skill_dir>/scripts/run_muse.py --stage keyframes --ids K2,K3,K4 --workers 2 --retries 2
   ```
   - **硬门禁**：必须 `read_file` 看每一张关键帧！检查：① 商品外形/颜色/部件数（如灯泡数、抽屉数、衣领版型）零畸变；② 空间物理与手部自然；③ 背景时段与服装一致。坏图立刻微调 Prompt 重跑单张，**不合格的关键帧绝不喂给视频模型**。
3. **Stage 4B · 生成 5 秒分镜视频并 6×5 密集抽帧**：
   ```bash
   python3 <skill_dir>/scripts/run_muse.py --stage videos --ids all --workers 2 --retries 2 --tag v1
   python3 <skill_dir>/scripts/render_qa_sheet.py --dir renders/v1
   ```
   - **硬门禁**：必须 `read_file` 查看 `renders/v1/qa_sheet_all.png`（每镜抽 `0.2 / 1.2 / 2.2 / 3.2 / 4.4s` 五帧）：检查运动中商品是否融化、手部是否畸形、产品是否出画，并**逐镜标定最佳截点 `[ss, end]`**（避开末段易漂移帧）。

### Stage 5：精剪成片、零版权音效与完整投放素材包交付
- **画质与时长**：`ffmpeg` Lanczos 统一升至 `1080×1920 30fps` + 轻度锐化（`unsharp=5:5:0.45`）+ 分段轻调色；时长严格贴合原爆款高完播节奏（通常 12–15.5 秒）。
- **克制转场（全片最多 3 种）**：
  1. `0.20s` 切黑硬切（仅用于痛点→爆亮/变身主反转）；
  2. 无渐变硬切（用于色温/款式/多角度快切，对比才利落）；
  3. `0.22–0.25s` 闪白过渡（模拟反光或节奏衔接，克制使用）。
- **音频与商用合规（永久红线）**：
  - **BGM 仅限免署名可商用曲**（Pixabay Content License / Mixkit 等，禁用 CC-BY）；音量约 `0.28–0.34`，开头淡入 `0.35s`、结尾淡出 `1.0s`；
  - **交互音效本地代码合成**（开关脆哒声、亮灯柔和起音、闪白微风声，100% 零版权），用 `adelay` 精确对齐每段切点前 `20ms`，最后 `alimiter=limit=0.95` 防爆音。
- **字幕规范（PIL 预渲染 PNG + overlay，不依赖 ffmpeg drawtext）**：
  - 大号纯白粗体（`Arial Black` / `Arial Bold`）+ 半透明纯黑圆角底条（`rgba(0,0,0,215)`），**零花字**；
  - 严格落在 Meta Reels 9:16 安全区（顶部留空 ≥220px，底部留空 ≥420px，即底边 `y_bottom ≤ 1500px`，且不遮挡商品主体）；
  - 结尾定帧 2.5–3s：价格字最大（`84px`），免邮/退货/质保小一号（`28–33px`）放下方。
- **标准交付包（缺一不可）**：
  1. `final/ad_<SKU>_<angle>_916.mp4`（终版成片，`ffprobe` 核验码率/时长/音画流）；
  2. `final/qa_final_sheet.png`（12 帧终审验收拼图，**交付前必须 `read_file` 终审确认无遮挡、无错字**）；
  3. `covers/`（4 张 1080×1920 Reels/Shorts 封面）；
  4. `images/`（`static-11.png` 1:1、`static-45.png` 4:5、`static-916.png` 9:16 同角度对照静态测试图）；
  5. `copy.md`（Meta Primary Text ×3 + Headline ×3 + Description ×2，全有官网依据）；
  6. `asset-pack.md`（全文件映射表 + BGM 商用授权记录 + Meta AI 媒体申报提醒）。

---

## `muse2api` 网关实战排坑表（已全部封装进 `scripts/run_muse.py`）

1. **HTTP `202 Accepted`**：`/v1/images/generations` 开 `async: true` 与 `/v1/videos` 均可能返回 `202`，客户端必须接受 `code in (200, 201, 202)`。
2. **完成状态字段是 `"completed"`**：轮询必须同时兼容 `{"completed", "succeeded", "done"}`（旧脚本只判 `done` 会死等超时）。
3. **媒体 URL 是相对路径**：回包 `result.url` / `video.url` 形如 `/v1/media/xxx.mp4`，需拼接 `MUSE_BASE`，且 `/v1/media/*` 无需鉴权。
4. **偶发上游异常必须自动重试**：账号池可能出现某账号地区受限、503 过载仅回纯文本、或下载时 `RemoteDisconnected`——`run_muse.py` 已内置提交/生成重试（`--retries 2`）+ 下载 3 次重试 + 并发控流（建议 `--workers 2`，不超过健康账号数的一半）。
5. **输出分辨率归一化**：`muse-video` 实际可能吐出 `720×1280` 或 `704×1248`（24fps），合成阶段统一 `scale=1080:1920:flags=lanczos:force_original_aspect_ratio=increase,crop=1080:1920,fps=30`。
6. **`yt-dlp` 路径**：macOS 上 `pip install --user yt-dlp` 装在 `~/Library/Python/3.12/bin/yt-dlp`（不在默认 PATH），`analyze_viral.py` 已自动探测 `site.getuserbase()/bin/yt-dlp`。

---

## 随包工具脚本（`<skill_dir>/scripts/`）

| 脚本 | 用途 |
|---|---|
| `find_viral_yt.py` | 按关键词检索 YouTube / Shorts 高播短视频、拉真实播放量与描述，并生成 2×3 缩略图拼图供肉眼筛错款 |
| `analyze_viral.py` | `yt-dlp` 下载选中爆款原片 + 1fps 时间轴抽帧拼图 + 音频提取 + 可选调用 `muse-spark` 拆解 |
| `run_muse.py` | 驱动 `muse2api` 批量生成多图参考关键帧（`--stage keyframes`）与 5s 分镜视频（`--stage videos`），带并发控流与自动重试 |
| `render_qa_sheet.py` | 对 `renders/<tag>/` 下所有分镜 MP4 批量抽 5 帧（`0.2/1.2/2.2/3.2/4.4s`）生成密集质检拼图，方便精准选截点 |
