#!/usr/bin/env python3
"""Render Kokani Connect branded slides (1080x1350 JPEG) from a JSON spec.

Usage: python3 scripts/design.py spec.json

Spec: {"id": "2026-10-19-ghar-se-door", "slides": [ {slide}, ... ]}
Each slide may contain:
  kicker   small red label at the top (e.g. "GHAR SE DOOR")
  lines    list of headline lines; wrap a line in *stars* to make it red
  body     list of body lines (grey)
  bullets  list of short items shown with red markers
  cta      text for the red pill button
  big      very large single word/number (e.g. "26")
  big_label caption under `big`
  footer   "logo" (default) or "swipe" (adds 'Swipe →' hint)
Output: media/<id>-1.jpg, media/<id>-2.jpg, ...
"""
import json
import re
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BRAND = json.loads((ROOT / "brand" / "brand.json").read_text())
C = BRAND["colors"]
BG, WH, RED, MUT = C["background"], C["primary_text"], C["accent_red"], "#BDBDBD"
W, H, M = 1080, 1350, 80
FONT_DIR = "/usr/share/fonts/truetype/google-fonts/Poppins-"


def font(weight, size):
    return ImageFont.truetype(f"{FONT_DIR}{weight}.ttf", size)


LOGO = Image.open(ROOT / "brand" / "logo-wide.png").convert("RGB")


def paste_logo(img, width, x, y):
    lg = LOGO.resize((width, int(LOGO.height * width / LOGO.width)), Image.LANCZOS)
    img.paste(lg, (x, y))
    return lg.height


def wrap(draw, text, fnt, max_w):
    words, out, cur = text.split(), [], ""
    for w in words:
        t = f"{cur} {w}".strip()
        if draw.textlength(t, font=fnt) <= max_w:
            cur = t
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out


def rich_words(text):
    """Split 'a *b c* d' into [(word, is_red), ...]."""
    out, red = [], False
    for part in re.split(r"(\*)", text):
        if part == "*":
            red = not red
            continue
        out += [(w, red) for w in part.split()]
    return out


def wrap_rich(draw, text, fnt, max_w):
    lines, cur = [], []
    for w, r in rich_words(text):
        trial = " ".join(x for x, _ in cur + [(w, r)])
        if cur and draw.textlength(trial, font=fnt) > max_w:
            lines.append(cur)
            cur = []
        cur.append((w, r))
    if cur:
        lines.append(cur)
    return lines


def draw_rich(draw, x, y, words, fnt):
    for w, r in words:
        draw.text((x, y), w, font=fnt, fill=RED if r else WH)
        x += draw.textlength(w + " ", font=fnt)


def render_slide(s, idx, total):
    """Draw once off-screen to measure height, then again vertically centred."""
    probe = _render(s, idx, total, 0)
    top = max(110, (H - 230 - probe) // 2)
    img = Image.new("RGB", (W, H), BG)
    _render(s, idx, total, top, img)
    return img


def _render(s, idx, total, y0, img=None):
    draw_on = img is not None
    if img is None:
        img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    y = y0
    if s.get("kicker"):
        d.text((M, y), s["kicker"].upper(), font=font("Medium", 32), fill=RED)
        y += 60
        d.line([M, y, M + 110, y], fill=RED, width=6)
        y += 70
    if s.get("big"):
        d.text((M, y - 20), s["big"], font=font("Bold", 260), fill=RED)
        y += 300
        if s.get("big_label"):
            for ln in wrap(d, s["big_label"], font("Bold", 64), W - 2 * M):
                d.text((M, y), ln, font=font("Bold", 64), fill=WH)
                y += 82
        y += 30
    hsize = s.get("headline_size", 84)
    for line in s.get("lines", []):
        for words in wrap_rich(d, line, font("Bold", hsize), W - 2 * M):
            draw_rich(d, M, y, words, font("Bold", hsize))
            y += int(hsize * 1.25)
    if s.get("lines"):
        y += 40
    for para in s.get("body", []):
        for ln in wrap(d, para, font("Regular", 42), W - 2 * M):
            d.text((M, y), ln, font=font("Regular", 42), fill=MUT)
            y += 60
        y += 22
    for b in s.get("bullets", []):
        d.rounded_rectangle([M, y + 14, M + 22, y + 36], radius=5, fill=RED)
        for i, ln in enumerate(wrap(d, b, font("Medium", 44), W - 2 * M - 50)):
            d.text((M + 50, y), ln, font=font("Medium", 44), fill=WH)
            y += 62
        y += 18
    if s.get("cta"):
        f = font("Medium", 40)
        tw = d.textlength(s["cta"], font=f)
        y += 30
        d.rounded_rectangle([M, y, M + tw + 100, y + 96], radius=48, fill=RED)
        d.text((M + 50 + tw / 2, y + 48), s["cta"], font=f, fill=WH, anchor="mm")
        y += 96
    if not draw_on:
        return y - y0
    # footer: logo bottom-left, slide counter / swipe bottom-right
    paste_logo(img, 300, M, H - 190)
    if total > 1:
        hint = "Swipe" if idx < total else f"{idx}/{total}"
        d.text((W - M - (44 if idx < total else 0), H - 120), hint, font=font("Medium", 34), fill=MUT, anchor="rm")
        if idx < total:  # drawn chevron (font has no arrow glyph)
            cx, cy = W - M - 18, H - 120
            d.line([(cx - 12, cy - 14), (cx + 4, cy), (cx - 12, cy + 14)], fill=RED, width=5, joint="curve")
    d.rectangle([0, H - 14, W, H], fill=RED)
    return y - y0


def main(spec_path):
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    total = len(spec["slides"])
    paths = []
    for i, s in enumerate(spec["slides"], 1):
        p = ROOT / "media" / (f"{spec['id']}-{i}.jpg" if total > 1 else f"{spec['id']}.jpg")
        render_slide(s, i, total).save(p, "JPEG", quality=92)
        paths.append(str(p.relative_to(ROOT)))
    print("\n".join(paths))


if __name__ == "__main__":
    main(sys.argv[1])
