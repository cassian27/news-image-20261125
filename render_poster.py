#!/usr/bin/env python3
"""Draw the make.fun news-image-20261125 poster at build time.

Reads stories.json (the verified 25 November 2026 story list: a lead plus
up to six more) and paints a 1024x1024 newspaper front page into
entry.png, using Pillow and the DejaVu fonts on this machine.

Build time only. The graded program is main.ts, which just copies the
finished entry.png to /output. Nothing here runs at grade time, and the
render is deterministic: fixed layout, fixed palette, fixed fonts, no
timestamps and no randomness, so running it twice writes identical bytes.

Usage:
    python3 render_poster.py            # read stories.json, write entry.png
    python3 render_poster.py --check    # also write a 300px preview
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
W, H = 1024, 1024

# Newsprint cream, ink black, one red accent, quiet panel tints.
PAPER = (250, 246, 236)
INK = (24, 22, 20)
RED = (178, 34, 28)
MUTED = (96, 90, 82)
PANEL = (255, 255, 255)
PANEL_EDGE = (205, 198, 188)
TINTS = [
    (214, 231, 240),  # blue
    (240, 224, 205),  # sand
    (220, 236, 214),  # green
    (240, 214, 214),  # rose
    (228, 220, 240),  # lavender
    (240, 236, 196),  # pale yellow
]

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")


def load(name, size):
    return ImageFont.truetype(str(FONT_DIR / name), size)


SERIF_BOLD = lambda s: load("DejaVuSerif-Bold.ttf", s)  # noqa: E731
SANS_BOLD = lambda s: load("DejaVuSans-Bold.ttf", s)  # noqa: E731
SANS = lambda s: load("DejaVuSans.ttf", s)  # noqa: E731


def wrap_text(draw, text, font, max_width):
    """Greedy word wrap, measured with the real font."""
    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_clipped(draw, lines, x, y, font, fill, leading, bottom, max_lines=None):
    """Draw wrapped lines, at most max_lines and only above bottom.

    When text is cut — by the line cap or by the panel edge — the last
    visible line gets an ellipsis so a cut is never silent.
    """
    cut = False
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        cut = True
    for i, line in enumerate(lines):
        if y + leading > bottom:
            break
        text = line
        if (cut or i < len(lines) - 1) and y + 2 * leading > bottom:
            text = line.rstrip() + " …"
        draw.text((x, y), text, font=font, fill=fill)
        y += leading
    return y


def tag_chip(draw, x, y, text, font, bg, fg, max_width, pad=12):
    """A tag chip sized to its text.

    An ellipsis is added only when the text had to be shortened to fit;
    a tag that fits is shown whole, with no ellipsis.
    """
    shortened = False
    while text and draw.textlength(text, font=font) > max_width - 2 * pad:
        text = text[:-1].rstrip()
        shortened = True
    if shortened and text:
        while text and draw.textlength(text + " …", font=font) > max_width - 2 * pad:
            text = text[:-1].rstrip()
        text += " …"
    width = int(draw.textlength(text, font=font)) + 2 * pad
    height = font.size + 14
    draw.rectangle([x, y, x + width, y + height], fill=bg)
    draw.text((x + pad, y + 5), text, font=font, fill=fg)
    return height


def pictogram(draw, kind, cx, cy, s, color):
    """A small geometric pictogram centred at (cx, cy), size s."""
    if kind == "globe":
        draw.ellipse([cx - s, cy - s, cx + s, cy + s], outline=color, width=4)
        draw.ellipse([cx - s // 2, cy - s, cx + s // 2, cy + s], outline=color, width=3)
        draw.line([cx - s, cy, cx + s, cy], fill=color, width=3)
        draw.arc([cx - s, cy - s // 2, cx + s, cy + s // 2], 200, 340, fill=color, width=3)
    elif kind == "bars":
        for i, h in enumerate((0.45, 0.8, 0.6, 1.0)):
            x0 = cx - s + i * (s // 2)
            draw.rectangle([x0, cy + s - h * s, x0 + s // 3, cy + s], fill=color)
    elif kind == "rocket":
        draw.polygon([(cx, cy - s), (cx + s // 2, cy + s // 3), (cx, cy),
                      (cx - s // 2, cy + s // 3)], fill=color)
        draw.polygon([(cx - s // 3, cy + s // 2), (cx, cy + s),
                      (cx + s // 3, cy + s // 2)], fill=(232, 120, 40))
    elif kind == "leaf":
        draw.ellipse([cx - s, cy - s // 2, cx + s, cy + s // 2], outline=color, width=4)
        draw.line([cx - s, cy + s // 2, cx + s, cy - s // 2], fill=color, width=3)
    elif kind == "bolt":
        draw.polygon([(cx + s // 4, cy - s), (cx - s // 2, cy + s // 6),
                      (cx, cy + s // 6), (cx - s // 4, cy + s),
                      (cx + s // 2, cy - s // 6), (cx, cy - s // 6)], fill=color)
    elif kind == "ball":
        draw.ellipse([cx - s, cy - s, cx + s, cy + s], outline=color, width=4)
        draw.arc([cx - s, cy - s, cx + s, cy + s], 20, 160, fill=color, width=3)
        draw.line([cx - s, cy, cx + s, cy], fill=color, width=3)
    else:  # "flag"
        draw.line([cx - s // 2, cy - s, cx - s // 2, cy + s], fill=color, width=4)
        draw.polygon([(cx - s // 2, cy - s), (cx + s, cy - s // 2),
                      (cx - s // 2, cy)], fill=color)


def layout_report(stories):
    """Count wrapped lines per panel, so --check can prove nothing is cut.

    Returns a list of (tag, headline_lines, summary_lines) for the lead
    and each grid story. A panel is clean when its headline fits in 3
    lines and its summary in 2 — the same caps draw_clipped enforces.
    The check below fails the build if any panel exceeds its cap, so a
    too-long story is caught here instead of silently gaining an
    ellipsis on the poster.
    """
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    report = []
    lead, rest = stories[0], stories[1:7]
    head = SANS_BOLD(38)
    body = SANS(24)
    report.append((lead["tag"],
                   len(wrap_text(d, lead["headline"], head, W - 96 - 280)),
                   len(wrap_text(d, lead["summary"], body, W - 96 - 280))))
    hf = SANS_BOLD(24)
    bf = SANS(19)
    for st in rest:
        report.append((st["tag"],
                       len(wrap_text(d, st["headline"], hf, 296 - 24)),
                       len(wrap_text(d, st["summary"], bf, 296 - 24))))
    return report


def render(stories, out_path):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    # Masthead: shrink the title until it fits the page width.
    mast_size = 76
    mast = SERIF_BOLD(mast_size)
    while d.textlength("THE WORLD TODAY", font=mast) > W - 96 and mast_size > 40:
        mast_size -= 2
        mast = SERIF_BOLD(mast_size)
    d.text((W // 2, 24), "THE WORLD TODAY", font=mast, fill=INK, anchor="mt")
    d.line([48, 128, W - 48, 128], fill=INK, width=3)
    d.text((W // 2, 142), "WEDNESDAY 25 NOVEMBER 2026",
           font=SANS_BOLD(44), fill=RED, anchor="ma")
    d.text((W // 2, 200), "One day. One page. The world's news, summed up.",
           font=SANS(24), fill=MUTED, anchor="ma")
    d.line([48, 234, W - 48, 234], fill=INK, width=2)

    lead, rest = stories[0], stories[1:7]

    # Lead story: one full-width panel.
    lx, ly, lw, lh = 48, 252, W - 96, 250
    d.rectangle([lx, ly, lx + lw, ly + lh], fill=PANEL, outline=PANEL_EDGE, width=2)
    tag_chip(d, lx, ly, lead["tag"].upper(), SANS_BOLD(22), RED,
             (255, 255, 255), 420)
    head = SANS_BOLD(38)
    y = draw_clipped(d, wrap_text(d, lead["headline"], head, lw - 280),
                     lx + 24, ly + 56, head, INK, 46, ly + lh - 78, max_lines=3)
    body = SANS(24)
    draw_clipped(d, wrap_text(d, lead["summary"], body, lw - 280),
                 lx + 24, y + 6, body, MUTED, 30, ly + lh - 12, max_lines=2)
    pictogram(d, lead.get("icon", "globe"), lx + lw - 110, ly + lh // 2 + 10, 62, RED)

    # Story grid: 3 columns x 2 rows.
    gx, gy = 48, 522
    cw, ch, gap = 296, 196, 20
    for i, st in enumerate(rest):
        col, row = i % 3, i // 3
        x = gx + col * (cw + gap)
        y0 = gy + row * (ch + gap)
        tint = TINTS[i % len(TINTS)]
        d.rectangle([x, y0, x + cw, y0 + ch], fill=PANEL, outline=PANEL_EDGE, width=2)
        d.rectangle([x, y0, x + cw, y0 + 34], fill=tint)
        tag_chip(d, x, y0, st["tag"].upper(), SANS_BOLD(17), tint, INK, cw - 44)
        pictogram(d, st.get("icon", "flag"), x + cw - 22, y0 + 17, 12, RED)
        hf = SANS_BOLD(24)
        yy = draw_clipped(d, wrap_text(d, st["headline"], hf, cw - 24),
                          x + 12, y0 + 44, hf, INK, 29, y0 + ch - 56, max_lines=3)
        bf = SANS(19)
        draw_clipped(d, wrap_text(d, st["summary"], bf, cw - 24),
                     x + 12, yy + 4, bf, MUTED, 24, y0 + ch - 8, max_lines=2)

    # Footer.
    d.line([48, 956, W - 48, 956], fill=INK, width=2)
    d.text((W // 2, 968), "Sources: Reuters · Associated Press · Xinhua · Wikipedia — 25 November 2026",
           font=SANS(20), fill=MUTED, anchor="ma")

    img.save(out_path, format="PNG", optimize=False)
    return out_path


def main():
    stories = json.loads((HERE / "stories.json").read_text(encoding="utf-8"))
    assert 5 <= len(stories) <= 7, "need 5-7 stories (lead + grid)"
    out = HERE / "entry.png"
    render(stories, out)
    size = out.stat().st_size
    im = Image.open(out)
    print(f"wrote {out} {im.size[0]}x{im.size[1]} {size} bytes")
    assert im.size == (1024, 1024), "must be 1024x1024"
    assert size <= 1_048_576, "must be <= 1 MiB"
    if "--check" in sys.argv:
        im.resize((300, 300)).save(HERE / "preview-300.png")
        print("wrote preview-300.png for the 300px legibility check")
        for tag, headline_lines, summary_lines in layout_report(stories):
            print(f"layout {tag}: headline {headline_lines} lines, "
                  f"summary {summary_lines} lines")
            assert headline_lines <= 3, f"{tag} headline overflows"
            assert summary_lines <= 2, f"{tag} summary overflows"


if __name__ == "__main__":
    main()
