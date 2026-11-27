#!/usr/bin/env python3
"""US/EU DTC Minimalist Graphic Compositor for viral-product-images.
Separates clean text-free AI base photography from crisp 4x-supersampled typography
and vector graphics using true RGBA alpha-compositing (zero jagged edges, zero halo seams).

Default canvas: 800x800 (unless explicitly overridden in cards.json).
Output JPEG uses 4:4:4 chroma (subsampling=0, quality=96) for razor-sharp typography.

Supported card types in cards.json:
  - hero_clean       : Pure high-res crop/scale, zero text (GMC/Amazon compliant P1)
  - lifestyle_title  : Clean base + minimal luxury headline/subline bar (top or bottom)
  - callout_anatomy  : Clean base + crisp leader lines, dots, and short English callout pills
  - dimensions       : Clean base + precise horizontal & vertical imperial dimension rulers
  - split_compare    : 2-column Before/After or State-A vs State-B + bottom offer bar
  - multi_panel      : 3-column mode/scene comparison + bottom offer bar
  - us_vs_them       : Left hero product photo + right clean Us-vs-Them comparison table

Usage:
  python3 render_dtc_cards.py --doc cards.json
"""
import argparse
import json
import os
from PIL import Image, ImageDraw, ImageFont

FONT_TTC = "/System/Library/Fonts/HelveticaNeue.ttc"
IDX_BOLD = 1     # Helvetica Neue Bold
IDX_MED = 10     # Helvetica Neue Medium
IDX_REG = 0      # Helvetica Neue Regular


def get_font(weight, size):
    idx = {"bold": IDX_BOLD, "medium": IDX_MED, "regular": IDX_REG}.get(weight, IDX_BOLD)
    if os.path.exists(FONT_TTC):
        return ImageFont.truetype(FONT_TTC, size, index=idx)
    fallback = "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if weight == "bold" else "/System/Library/Fonts/Supplemental/Arial.ttf"
    return ImageFont.truetype(fallback, size)


def fit_cover(im, w, h, focus_x=0.5, focus_y=0.5):
    scale = max(w / im.width, h / im.height)
    nw, nh = int(round(im.width * scale)), int(round(im.height * scale))
    rsz = im.resize((nw, nh), Image.LANCZOS)
    x0 = max(0, min(nw - w, int((nw - w) * focus_x)))
    y0 = max(0, min(nh - h, int((nh - h) * focus_y)))
    return rsz.crop((x0, y0, x0 + w, y0 + h))


def composite_rect(base_rgba, box, fill_rgba):
    """True alpha-composited filled rectangle onto base_rgba."""
    if fill_rgba[3] <= 0:
        return base_rgba
    layer = Image.new("RGBA", base_rgba.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rectangle(box, fill=fill_rgba)
    return Image.alpha_composite(base_rgba, layer)


def composite_pill(base_rgba, cx, cy, lines, bg=(18, 18, 18, 220), pad_x=28, pad_y=16, radius=16, max_w=None):
    """True alpha-composited rounded pill + anti-aliased text onto base_rgba.
    lines: list of (text, weight, size, color_rgba)
    """
    meas_d = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    gap = int(lines[0][2] * 0.28) if lines else 10
    measured = []
    tot_h = 0
    for text, weight, sz, col in lines:
        f = get_font(weight, sz)
        bb = meas_d.textbbox((0, 0), text, font=f)
        tw = bb[2] - bb[0]
        if max_w and tw > max_w:
            sz = max(14, int(sz * max_w / tw))
            f = get_font(weight, sz)
            bb = meas_d.textbbox((0, 0), text, font=f)
            tw = bb[2] - bb[0]
        th = bb[3] - bb[1]
        measured.append((text, f, tw, th, bb[1], col))
        tot_h += th
    tot_h += gap * (len(measured) - 1)
    bw = max(m[2] for m in measured) + pad_x * 2
    bh = tot_h + pad_y * 2
    x0, y0 = int(cx - bw // 2), int(cy - bh // 2)

    # 1) Composite pill background on its own transparent layer (skip if alpha == 0!)
    out = base_rgba
    if bg and bg[3] > 0:
        bg_layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
        ImageDraw.Draw(bg_layer).rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=radius, fill=bg)
        out = Image.alpha_composite(out, bg_layer)

    # 2) Composite text on a separate clean transparent layer so anti-aliased edges blend smoothly!
    txt_layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
    td = ImageDraw.Draw(txt_layer)
    y = y0 + pad_y
    for text, f, tw, th, top_off, col in measured:
        td.text((int(cx - tw // 2), int(y - top_off)), text, font=f, fill=col)
        y += th + gap
    return Image.alpha_composite(out, txt_layer)


def supersample_factor(w, h):
    return 4 if max(w, h) <= 1080 else 2


def render_hero_clean(card, cwd):
    W, H = card.get("canvas", [800, 800])
    im = Image.open(os.path.join(cwd, card["src"])).convert("RGB")
    return fit_cover(im, W, H, card.get("focus_x", 0.5), card.get("focus_y", 0.5))


def render_lifestyle_title(card, cwd):
    W, H = card.get("canvas", [800, 800])
    S = supersample_factor(W, H)
    SW, SH = W * S, H * S
    im = fit_cover(Image.open(os.path.join(cwd, card["src"])).convert("RGBA"), SW, SH,
                   card.get("focus_x", 0.5), card.get("focus_y", 0.5))
    pos = card.get("position", "bottom")
    bar_h = int(SH * card.get("bar_ratio", 0.14))
    y_start = 0 if pos == "top" else (SH - bar_h)
    bg = tuple(card.get("bar_bg", [18, 18, 18, 224]))
    im = composite_rect(im, [0, y_start, SW, y_start + bar_h], bg)

    title = card.get("title", "")
    sub = card.get("subtitle", "")
    lines = [(title, "bold", int(SW * 0.040), (255, 255, 255, 255))]
    if sub:
        lines.append((sub, "medium", int(SW * 0.025), (255, 226, 172, 255)))
    im = composite_pill(im, SW // 2, y_start + bar_h // 2, lines, bg=(0, 0, 0, 0), pad_x=0, pad_y=0, max_w=int(SW * 0.90))
    return im.resize((W, H), Image.LANCZOS).convert("RGB")


def render_callout_anatomy(card, cwd):
    W, H = card.get("canvas", [800, 800])
    S = supersample_factor(W, H)
    SW, SH = W * S, H * S
    im = fit_cover(Image.open(os.path.join(cwd, card["src"])).convert("RGBA"), SW, SH,
                   card.get("focus_x", 0.5), card.get("focus_y", 0.5))

    if card.get("title"):
        im = composite_pill(
            im, SW // 2, int(SH * 0.075),
            [(card["title"], "bold", int(SW * 0.034), (255, 255, 255, 255))],
            bg=(18, 18, 18, 220), pad_x=int(SW * 0.035), pad_y=int(SH * 0.014), radius=int(SW * 0.012), max_w=int(SW * 0.88),
        )

    # Draw leader lines & anchor dots on dedicated transparent vector layer
    vec = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vec)
    for c in card.get("callouts", []):
        tx, ty = int(c["target"][0] * SW), int(c["target"][1] * SH)
        lx, ly = int(c["label_pos"][0] * SW), int(c["label_pos"][1] * SH)
        vd.line([(tx, ty), (lx, ly)], fill=(0, 0, 0, 130), width=max(2, int(SW * 0.0045)))
        vd.line([(tx, ty), (lx, ly)], fill=(255, 255, 255, 248), width=max(1, int(SW * 0.0022)))
        r = max(4, int(SW * 0.0075))
        ro = r + max(2, int(SW * 0.0022))
        vd.ellipse([tx - ro, ty - ro, tx + ro, ty + ro], fill=(0, 0, 0, 170))
        vd.ellipse([tx - r, ty - r, tx + r, ty + r], fill=(255, 255, 255, 255))
    im = Image.alpha_composite(im, vec)

    for c in card.get("callouts", []):
        lx, ly = int(c["label_pos"][0] * SW), int(c["label_pos"][1] * SH)
        lines = [(c["label"], "bold", int(SW * 0.025), (255, 255, 255, 255))]
        if c.get("sub"):
            lines.append((c["sub"], "medium", int(SW * 0.018), (226, 232, 242, 255)))
        im = composite_pill(
            im, lx, ly, lines,
            bg=(18, 18, 18, 224), pad_x=int(SW * 0.020), pad_y=int(SH * 0.011), radius=int(SW * 0.011),
        )

    return im.resize((W, H), Image.LANCZOS).convert("RGB")


def render_dimensions(card, cwd):
    W, H = card.get("canvas", [800, 800])
    S = supersample_factor(W, H)
    SW, SH = W * S, H * S
    im = fit_cover(Image.open(os.path.join(cwd, card["src"])).convert("RGBA"), SW, SH,
                   card.get("focus_x", 0.5), card.get("focus_y", 0.5))
    line_col = tuple(card.get("ruler_color", [30, 30, 30, 240]))
    pill_bg = tuple(card.get("pill_bg", [20, 20, 20, 232]))

    if card.get("title"):
        im = composite_pill(
            im, SW // 2, int(SH * 0.065),
            [(card["title"], "bold", int(SW * 0.034), (255, 255, 255, 255))],
            bg=pill_bg, pad_x=int(SW * 0.035), pad_y=int(SH * 0.013), radius=int(SW * 0.011),
        )

    vec = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vec)
    lw = max(2, int(SW * 0.0028))
    tick = int(SW * 0.014)
    for m in card.get("measures", []):
        x1, y1 = int(m["p1"][0] * SW), int(m["p1"][1] * SH)
        x2, y2 = int(m["p2"][0] * SW), int(m["p2"][1] * SH)
        vd.line([(x1, y1), (x2, y2)], fill=line_col, width=lw)
        if abs(x2 - x1) >= abs(y2 - y1):
            vd.line([(x1, y1 - tick), (x1, y1 + tick)], fill=line_col, width=lw)
            vd.line([(x2, y2 - tick), (x2, y2 + tick)], fill=line_col, width=lw)
        else:
            vd.line([(x1 - tick, y1), (x1 + tick, y1)], fill=line_col, width=lw)
            vd.line([(x2 - tick, y2), (x2 + tick, y2)], fill=line_col, width=lw)
    im = Image.alpha_composite(im, vec)

    for m in card.get("measures", []):
        x1, y1 = int(m["p1"][0] * SW), int(m["p1"][1] * SH)
        x2, y2 = int(m["p2"][0] * SW), int(m["p2"][1] * SH)
        mx, my = (x1 + x2) // 2, (y1 + y2) // 2
        lines = [(m["text"], "bold", int(SW * 0.027), (255, 255, 255, 255))]
        if m.get("sub"):
            lines.append((m["sub"], "medium", int(SW * 0.018), (224, 230, 240, 255)))
        im = composite_pill(
            im, mx, my, lines,
            bg=pill_bg, pad_x=int(SW * 0.019), pad_y=int(SH * 0.010), radius=int(SW * 0.010),
        )

    return im.resize((W, H), Image.LANCZOS).convert("RGB")


def render_panels(card, cwd):
    W, H = card.get("canvas", [800, 800])
    S = supersample_factor(W, H)
    SW, SH = W * S, H * S
    panels = card["panels"]
    n = len(panels)
    canvas = Image.new("RGBA", (SW, SH), (0, 0, 0, 255))
    pw = SW // n
    for i, p in enumerate(panels):
        im = Image.open(os.path.join(cwd, p["src"])).convert("RGBA")
        w_this = pw if i < n - 1 else (SW - i * pw)
        crop = fit_cover(im, w_this, SH, p.get("focus_x", 0.5), p.get("focus_y", 0.35))
        canvas.paste(crop, (i * pw, 0))

    # Crisp divider lines on separate layer
    div = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    dd = ImageDraw.Draw(div)
    dw = max(2, int(SW * 0.0022))
    for i in range(1, n):
        x = i * pw
        dd.rectangle([x - dw, 0, x + dw, SH], fill=(255, 255, 255, 235))
    canvas = Image.alpha_composite(canvas, div)

    for i, p in enumerate(panels):
        cx = i * pw + pw // 2
        col = tuple(p.get("title_color", [255, 255, 255, 255]))
        lines = [(p["title"], "bold", int(SW * 0.031), col)]
        if p.get("sub"):
            lines.append((p["sub"], "medium", int(SW * 0.022), (255, 255, 255, 255)))
        canvas = composite_pill(
            canvas, cx, int(SH * 0.085), lines,
            bg=(15, 15, 15, 218), pad_x=int(SW * 0.022), pad_y=int(SH * 0.012), radius=int(SW * 0.012),
            max_w=int(pw * 0.86),
        )

    if card.get("footer_title"):
        bar_h = int(SH * 0.155)
        canvas = composite_rect(canvas, [0, SH - bar_h, SW, SH], (15, 15, 15, 232))
        fl = [(card["footer_title"], "bold", int(SW * 0.039), (255, 255, 255, 255))]
        if card.get("footer_sub"):
            fl.append((card["footer_sub"], "medium", int(SW * 0.024), (255, 226, 172, 255)))
        canvas = composite_pill(
            canvas, SW // 2, SH - bar_h // 2, fl,
            bg=(0, 0, 0, 0), pad_x=0, pad_y=0, max_w=int(SW * 0.92),
        )

    return canvas.resize((W, H), Image.LANCZOS).convert("RGB")


def draw_check_badge(d, cx, cy, r, ok=True):
    if ok:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(22, 148, 82, 255))
        w = max(3, int(r * 0.24))
        p1 = (cx - int(r * 0.44), cy + int(r * 0.02))
        p2 = (cx - int(r * 0.10), cy + int(r * 0.36))
        p3 = (cx + int(r * 0.46), cy - int(r * 0.34))
        d.line([p1, p2, p3], fill=(255, 255, 255, 255), width=w, joint="curve")
    else:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(212, 72, 72, 255))
        w = max(3, int(r * 0.22))
        o = int(r * 0.36)
        d.line([(cx - o, cy - o), (cx + o, cy + o)], fill=(255, 255, 255, 255), width=w)
        d.line([(cx - o, cy + o), (cx + o, cy - o)], fill=(255, 255, 255, 255), width=w)


def render_us_vs_them(card, cwd):
    W, H = card.get("canvas", [800, 800])
    S = supersample_factor(W, H)
    SW, SH = W * S, H * S
    canvas = Image.new("RGBA", (SW, SH), (248, 246, 242, 255))
    left_w = int(SW * 0.42)
    im = fit_cover(Image.open(os.path.join(cwd, card["src"])).convert("RGBA"), left_w, SH,
                   card.get("focus_x", 0.5), card.get("focus_y", 0.5))
    canvas.paste(im, (0, 0))

    layer = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pad = int(SW * 0.034)
    rx0 = left_w + pad
    rx1 = SW - pad
    rw = rx1 - rx0
    brand = card.get("brand", "OURS")
    other = card.get("other", "OTHERS")
    rows = card.get("rows", [])

    t_txt = card.get("title", "WHY CHOOSE US")
    t_sz = int(SW * 0.036)
    f_h = get_font("bold", t_sz)
    tb = d.textbbox((0, 0), t_txt, font=f_h)
    if (tb[2] - tb[0]) > rw:
        t_sz = int(t_sz * rw / (tb[2] - tb[0]))
        f_h = get_font("bold", t_sz)
    d.text((rx0, int(SH * 0.075)), t_txt, font=f_h, fill=(22, 22, 22, 255))

    col_us = rx0 + int(rw * 0.74)
    col_th = rx0 + int(rw * 0.91)
    y_hdr = int(SH * 0.185)
    f_col = get_font("bold", int(SW * 0.0175))
    for cx, lbl, col in [(col_us, brand, (22, 138, 78, 255)), (col_th, other, (120, 120, 120, 255))]:
        bb = d.textbbox((0, 0), lbl, font=f_col)
        d.text((cx - (bb[2] - bb[0]) // 2, y_hdr - bb[1]), lbl, font=f_col, fill=col)

    feat_max_w = int(rw * 0.62)
    row_top = int(SH * 0.255)
    row_bot = int(SH * 0.825)
    step = (row_bot - row_top) // max(1, len(rows))
    badge_r = int(SW * 0.0185)
    lw = max(2, int(SW * 0.0018))
    for idx, row in enumerate(rows):
        ry = row_top + idx * step
        d.line([(rx0, ry), (rx1, ry)], fill=(218, 212, 204, 255), width=lw)
        cy = ry + step // 2
        ftxt = row["feature"]
        fsz = int(SW * 0.0225)
        f_row = get_font("medium", fsz)
        fb = d.textbbox((0, 0), ftxt, font=f_row)
        if (fb[2] - fb[0]) > feat_max_w:
            fsz = int(fsz * feat_max_w / (fb[2] - fb[0]))
            f_row = get_font("medium", fsz)
            fb = d.textbbox((0, 0), ftxt, font=f_row)
        d.text((rx0, cy - (fb[3] - fb[1]) // 2 - fb[1]), ftxt, font=f_row, fill=(32, 32, 32, 255))
        draw_check_badge(d, col_us, cy, badge_r, ok=True)
        draw_check_badge(d, col_th, cy, badge_r, ok=False)
    d.line([(rx0, row_top + len(rows) * step), (rx1, row_top + len(rows) * step)], fill=(218, 212, 204, 255), width=lw)

    canvas = Image.alpha_composite(canvas, layer)
    if card.get("footer"):
        canvas = composite_pill(
            canvas, (rx0 + rx1) // 2, int(SH * 0.905),
            [(card["footer"], "medium", int(SW * 0.021), (255, 255, 255, 255))],
            bg=(22, 22, 22, 238), pad_x=int(SW * 0.025), pad_y=int(SH * 0.013), radius=int(SW * 0.011), max_w=rw,
        )
    return canvas.resize((W, H), Image.LANCZOS).convert("RGB")


DISPATCH = {
    "hero_clean": render_hero_clean,
    "lifestyle_title": render_lifestyle_title,
    "callout_anatomy": render_callout_anatomy,
    "dimensions": render_dimensions,
    "split_compare": render_panels,
    "multi_panel": render_panels,
    "us_vs_them": render_us_vs_them,
}


def card_content_sig(card):
    """Signature of visual + copy content; identical clones (e.g. Ad3 == P7) match, distinct ad hooks stay."""
    ctype = card.get("type", "")
    if "panels" in card:
        panels_sig = tuple(
            (p.get("src", ""), p.get("title", ""), p.get("sub", ""))
            for p in card["panels"]
        )
    else:
        panels_sig = (card.get("src", ""),)
    return (
        ctype,
        panels_sig,
        card.get("position", ""),
        card.get("title", ""),
        card.get("subtitle", ""),
        card.get("footer_title", ""),
        card.get("footer_sub", ""),
        card.get("footer", ""),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", default="cards.json")
    ap.add_argument("--all-in-qa", action="store_true", help="Include exact duplicates in gallery_qa_sheet.png")
    args = ap.parse_args()

    cwd = os.getcwd()
    cfg = json.load(open(os.path.join(cwd, args.doc)))
    rendered = []
    seen_sigs = set()
    qa_items = []
    for card in cfg["cards"]:
        ctype = card["type"]
        if ctype not in DISPATCH:
            raise ValueError(f"Unknown card type: {ctype}")
        img = DISPATCH[ctype](card, cwd)
        out_path = os.path.join(cwd, card["out"])
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        if out_path.lower().endswith((".jpg", ".jpeg")):
            img.save(out_path, quality=96, subsampling=0)
        else:
            img.save(out_path)
        print(f"[{card['id']}] ({ctype}) -> {out_path} ({img.width}x{img.height})")
        rendered.append((card["id"], out_path))

        sig = card_content_sig(card)
        explicit = card.get("in_qa_sheet")
        is_ad = "/ads/" in card["out"].replace("\\", "/")
        if args.all_in_qa:
            include_qa = True
        elif explicit is not None:
            include_qa = bool(explicit)
        else:
            include_qa = sig not in seen_sigs
        seen_sigs.add(sig)
        if include_qa:
            qa_items.append((card["id"], out_path, is_ad))

    if qa_items:
        cols = 4 if len(qa_items) in (4, 7, 8) else min(3, len(qa_items))
        rows = (len(qa_items) + cols - 1) // cols
        cell = 440
        sheet = Image.new("RGB", (cell * cols, cell * rows), (24, 24, 24))
        dr = ImageDraw.Draw(sheet)
        for idx, (cid, fp, is_ad) in enumerate(qa_items):
            im = Image.open(fp).convert("RGB")
            im.thumbnail((cell - 16, cell - 40), Image.LANCZOS)
            r, c = divmod(idx, cols)
            x0 = c * cell + (cell - im.width) // 2
            y0 = r * cell + 34 + ((cell - 40) - im.height) // 2
            sheet.paste(im, (x0, y0))
            tag = f"[AD] {cid}" if is_ad else f"[PDP] {cid}"
            col = (255, 205, 95) if is_ad else (0, 255, 140)
            dr.rectangle([c * cell + 6, r * cell + 6, c * cell + 310, r * cell + 30], fill=(0, 0, 0))
            dr.text((c * cell + 12, r * cell + 11), tag, fill=col)
        qa = os.path.join(cwd, "final", "gallery_qa_sheet.png")
        os.makedirs(os.path.dirname(qa), exist_ok=True)
        sheet.save(qa)
        print(f"GALLERY QA SHEET ({len(qa_items)}/{len(rendered)} unique) -> {qa}")


if __name__ == "__main__":
    main()
