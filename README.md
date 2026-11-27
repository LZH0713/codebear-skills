# codebear-skills

Personal plugin marketplace & collection of custom Agent Skills.

## Plugins & Skills

| Plugin | Version | Description |
| --- | --- | --- |
| [`viral-product-images`](plugins/viral-product-images/skills/viral-product-images/SKILL.md) | `1.0.0` | 欧美市场爆款产品图全自动产线：跨品类独立站 PDP 黄金 7 图 + Meta 高转化投流静图，底图与极简排版分离，无缝衔接视频产线。 |
| [`viral-product-video`](plugins/viral-product-video/skills/viral-product-video/SKILL.md) | `1.0.0` | 跨品类商品真实推广视频全自动产线：同款爆款检索、逐秒抽帧拆解、多图锚定关键帧与分镜视频质检、精剪成片与三比例静图交付。 |

## Directory Structure

```text
.
├── .claude-plugin/
│   └── marketplace.json
├── README.md
└── plugins/
    ├── viral-product-images/
    │   ├── plugin.json
    │   ├── .claude-plugin/plugin.json
    │   ├── assets/logo.svg
    │   └── skills/viral-product-images/
    │       ├── SKILL.md
    │       └── scripts/
    └── viral-product-video/
        ├── plugin.json
        ├── .claude-plugin/plugin.json
        ├── assets/logo.svg
        └── skills/viral-product-video/
            ├── SKILL.md
            └── scripts/
```

## Usage

### Add as a Plugin Marketplace

Add `https://github.com/LZH0713/codebear-skills.git` (or `LZH0713/codebear-skills`) as a custom plugin marketplace, then install individual plugins:

```bash
/plugin marketplace add LZH0713/codebear-skills
/plugin install viral-product-images@codebear-skills
/plugin install viral-product-video@codebear-skills
```

### Manual Installation

Copy any skill folder under `plugins/<name>/skills/<name>/` into your agent's skills directory (for example, `.agents/skills/` in a workspace or your global skills folder).
