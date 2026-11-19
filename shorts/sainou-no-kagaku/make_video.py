"""『才能の科学』（マシュー・サイド著／河出書房新社）紹介ショート
縦型 1080x1920 / 30fps / 60秒 / H.264 + 無音AACトラック

使い方:
  python3 make_video.py --stills   # 各シーンの静止画を stills/ に保存（レイアウト確認用）
  python3 make_video.py            # 動画を書き出す（OUTPUT のパス）

画像素材はすべてこのファイル内でコード描画（外部画像なし）。
フォント: Noto Sans JP（SIL Open Font License 1.1）
"""
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# =====================================================================
# 設定（ここを編集すればテキスト・秒数・色を変えられる）
# =====================================================================
OUTPUT = "/home/user/YouTube-/output/sainou-no-kagaku_short.mp4"
W, H, FPS = 1080, 1920, 30
SAFE_TOP, SAFE_BOTTOM = 150, 150      # 上下この範囲には文字を置かない
SAFE_MARGIN = 40                      # さらに内側に取る余白
MAX_TEXT_W = 940                      # 1行の最大幅（超えたら自動で縮小）

BG = (0x0F, 0x1B, 0x2D)               # 濃紺 #0F1B2D
WHITE = (255, 255, 255)
YELLOW = (0xFF, 0xD5, 0x4F)           # 強調色 #FFD54F
SUB = (190, 202, 222)                 # 補足用の淡い色

FONT_PATH = "/usr/local/share/fonts/noto-sans-jp/NotoSansJP-VF.ttf"
FONT_FALLBACK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_WEIGHT = "Bold"

SCENE_FADE = 0.4      # シーン切り替えのフェード（秒）
ITEM_FADE = 0.45      # 各行が出てくるフェード（秒）
EMPH_POP_DELAY = 0.25 # 行が出てから強調語が拡大し始めるまで（秒）
EMPH_SCALE = 1.12     # 強調語の最終拡大率（途中で少し大きく跳ねる）
EMPH_RESERVE = 1.16   # 強調語のために確保する横幅の倍率

# 行の書き方: ("テキスト", 文字サイズ, 表示開始秒[シーン内], 色) ／ {…} で囲んだ部分が黄色+拡大
# アイコン: ("@アイコン名", 高さ, 表示開始秒)
# 余白:     ("_", 高さ)
SCENES = [
    # 1. フック 0〜4秒
    (0.0, 4.0, [
        ("@question", 200, 0.0),
        ("_", 40),
        ("入社1年目、", 84, 0.1),
        ("「自分って{才能ないかも}」", 84, 0.4),
        ("と思ってない？", 84, 0.8),
    ]),
    # 2. 共感 4〜13秒
    (4.0, 8.5, [
        ("@race", 300, 0.0),
        ("_", 50),
        ("同期はすぐ仕事を覚えるのに、", 66, 0.4),
        ("自分だけ{遅い}気がする", 84, 1.4),
    ]),
    (8.5, 13.0, [
        ("「向いてないのかも」…", 80, 0.0),
        ("_", 60),
        ("その考え、", 84, 1.0),
        ("{ちょっと待って}", 112, 1.6),
    ]),
    # 3. 具体例：ほめ方の実験 13〜33秒
    (13.0, 18.5, [
        ("@test", 300, 0.0),
        ("_", 50),
        ("ある心理学の実験で、", 76, 0.4),
        ("子どもたちに", 76, 1.2),
        ("問題を解かせた", 84, 1.8),
    ]),
    (18.5, 27.0, [
        ("@arrow", 90, 0.0),
        ("半分は「{頭がいいね}」と", 76, 0.2),
        ("{能力}をほめる", 84, 0.8),
        ("_", 90),
        ("@arrow", 90, 3.4),
        ("半分は「{よくがんばったね}」と", 76, 3.6),
        ("{努力}をほめる", 84, 4.2),
    ]),
    (27.0, 33.0, [
        ("@down", 280, 0.0),
        ("_", 50),
        ("能力をほめられた子ほど、", 76, 0.4),
        ("難しい問題を避けて", 76, 1.4),
        ("{成績が下がった}", 104, 2.4),
    ]),
    # 4. 1年目への置き換え 33〜45秒
    (33.0, 39.0, [
        ("「センスあるね」と言われるより", 66, 0.0),
        ("_", 50),
        ("「{工夫したね}」と言われる", 84, 1.4),
        ("仕事のほうが、", 84, 2.2),
        ("人は{伸びる}", 104, 3.0),
    ]),
    (39.0, 45.0, [
        ("@stairs", 280, 0.0),
        ("_", 50),
        ("失敗は", 80, 0.4),
        ("才能がない証拠じゃない。", 80, 1.0),
        ("_", 30),
        ("{伸びている途中のサイン}", 92, 2.4),
    ]),
    # 5. 本のメッセージ 45〜54秒
    (45.0, 54.0, [
        ("@sprout", 300, 0.0),
        ("_", 50),
        ("才能は", 84, 0.5),
        ("{生まれつきで決まらない}", 92, 1.2),
        ("_", 60),
        ("正しい練習と環境で、", 76, 3.8),
        ("{あとから伸ばせる}", 104, 4.6),
    ]),
    # 6. 締め 54〜60秒
    (54.0, 60.0, [
        ("1年目の今こそ", 76, 0.0),
        ("読んでほしい一冊", 76, 0.4),
        ("_", 50),
        ("{『才能の科学』}", 112, 1.0),
        ("マシュー・サイド", 64, 1.5, SUB),
        ("_", 60),
        ("詳しくは概要欄へ", 72, 2.4),
        ("@pointdown", 110, 2.8),
    ]),
]

# =====================================================================
# ここから下は描画処理
# =====================================================================
_font_cache = {}


def font(size):
    if size not in _font_cache:
        if os.path.exists(FONT_PATH):
            f = ImageFont.truetype(FONT_PATH, size)
            try:
                f.set_variation_by_name(FONT_WEIGHT)
            except Exception:
                pass
        else:
            f = ImageFont.truetype(FONT_FALLBACK, size, index=0)
        _font_cache[size] = f
    return _font_cache[size]


def parse_markup(text):
    """'あ{い}う' -> [('あ',False),('い',True),('う',False)]"""
    segs, buf, emph = [], "", False
    for ch in text:
        if ch in "{}":
            if buf:
                segs.append((buf, emph))
            buf, emph = "", ch == "{"
        else:
            buf += ch
    if buf:
        segs.append((buf, emph))
    return segs


def seg_image(text, f, color):
    """影付きの文字画像（余白込み）"""
    asc, desc = f.getmetrics()
    w = int(math.ceil(f.getlength(text)))
    pad = 16
    img = Image.new("RGBA", (w + pad * 2, asc + desc + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((pad, pad + 5), text, font=f, fill=(0, 0, 0, 170))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(7)))
    ImageDraw.Draw(img).text((pad, pad), text, font=f, fill=color)
    return img, w, pad


class TextLine:
    def __init__(self, text, size, delay, color=WHITE):
        self.delay = delay
        segs = parse_markup(text)
        plain = "".join(s for s, _ in segs)
        f = font(size)
        # 強調語は拡大後の幅を確保して並べる（隣の文字と重ならないように）
        def line_w(ff):
            return sum(ff.getlength(s) * (EMPH_RESERVE if e else 1.0) for s, e in segs)
        # 幅が収まらなければ自動で縮小
        while line_w(f) > MAX_TEXT_W and size > 30:
            size -= 2
            f = font(size)
        self.size = size
        asc, desc = f.getmetrics()
        self.h = int((asc + desc) * 1.12)
        self.parts = []   # (img, x_offset, pad, emph)
        x = 0
        for s, emph in segs:
            img, w, pad = seg_image(s, f, YELLOW if emph else color)
            slot = w * EMPH_RESERVE if emph else w
            self.parts.append((img, x, pad, emph, slot))
            x += slot
        self.w = x
        self.has_emph = any(p[3] for p in self.parts)

    def draw(self, frame, cy, local_t):
        p = ease_out((local_t - self.delay) / ITEM_FADE)
        if p <= 0:
            return 0.0
        rise = (1 - p) * 36
        x0 = (W - self.w) / 2
        top = cy - self.h / 2 + rise
        # 強調語の拡大: 1.0 → (EMPH_SCALE+0.08) → EMPH_SCALE
        et = local_t - self.delay - EMPH_POP_DELAY
        scale = 1.0 if et <= 0 else emph_curve(et)
        for img, xo, pad, emph, w in self.parts:
            im = img
            if emph and scale != 1.0:
                nw, nh = int(img.width * scale), int(img.height * scale)
                im = img.resize((nw, nh), Image.LANCZOS)
            im = with_alpha(im, p)
            cx = x0 + xo + w / 2
            frame.alpha_composite(im, (int(cx - im.width / 2), int(top + self.h / 2 - im.height / 2)))
        return p


def emph_curve(t):
    peak = EMPH_SCALE + 0.08
    if t < 0.22:
        return 1.0 + (peak - 1.0) * ease_out(t / 0.22)
    if t < 0.5:
        return peak + (EMPH_SCALE - peak) * ease_out((t - 0.22) / 0.28)
    return EMPH_SCALE


# ---------- アイコン（すべて自作の図形） ----------
def supersample(w, h, fn):
    big = Image.new("RGBA", (w * 3, h * 3), (0, 0, 0, 0))
    fn(ImageDraw.Draw(big), 3, big)
    return big.resize((w, h), Image.LANCZOS)


def icon_question(h):
    w = int(h * 1.2)

    def d(g, k, _):
        g.rounded_rectangle((10 * k, 10 * k, (w - 10) * k, (h - 50) * k), radius=40 * k,
                            fill=(255, 255, 255, 30), outline=YELLOW + (255,), width=6 * k)
        g.polygon([(w * 0.3 * k, (h - 52) * k), (w * 0.45 * k, (h - 52) * k), (w * 0.28 * k, (h - 8) * k)],
                  fill=YELLOW + (255,))
        f = ImageFont.truetype(FONT_PATH, int(h * 0.55 * k)) if os.path.exists(FONT_PATH) else font(int(h * 0.55 * k))
        try:
            f.set_variation_by_name("Black")
        except Exception:
            pass
        g.text((w / 2 * k, (h - 50) / 2 * k), "?", font=f, fill=YELLOW + (255,), anchor="mm")
    return supersample(w, h, d)


def icon_race(h):
    """同期と自分の進み具合（バー）"""
    w = 760

    def d(g, k, _):
        f = font(int(44 * k))
        rows = [("同期", 0.88, (120, 196, 255)), ("自分", 0.32, YELLOW)]
        for i, (lab, ratio, col) in enumerate(rows):
            y = (40 + i * 130) * k
            g.text((0, y + 10 * k), lab, font=f, fill=(255, 255, 255, 255))
            g.rounded_rectangle((130 * k, y, (w - 10) * k, y + 70 * k), radius=35 * k, fill=(255, 255, 255, 30))
            g.rounded_rectangle((130 * k, y, (130 + (w - 140) * ratio) * k, y + 70 * k), radius=35 * k,
                                fill=col + (255,))
    return supersample(w, h, d)


def icon_test(h):
    """問題用紙とえんぴつ"""
    w = int(h * 1.1)

    def d(g, k, _):
        g.rounded_rectangle((40 * k, 10 * k, (w - 110) * k, (h - 10) * k), radius=18 * k, fill=(245, 245, 250, 255))
        for i in range(5):
            y = (50 + i * 48) * k
            g.ellipse((70 * k, y, 96 * k, y + 26 * k), outline=(90, 110, 150, 255), width=4 * k)
            g.rounded_rectangle((115 * k, y + 6 * k, (w - 150 - (i % 2) * 40) * k, y + 20 * k), radius=6 * k,
                                fill=(170, 180, 200, 255))
        # えんぴつ
        cx, cy = (w - 80) * k, (h - 70) * k
        L, Wd = 200 * k, 30 * k
        ang = math.radians(-55)
        dx, dy = math.cos(ang), math.sin(ang)
        nx, ny = -dy, dx
        tip = (cx, cy)
        base = (cx - dx * 50 * k, cy - dy * 50 * k)
        end = (cx - dx * L, cy - dy * L)
        poly = [(base[0] + nx * Wd / 2, base[1] + ny * Wd / 2), (end[0] + nx * Wd / 2, end[1] + ny * Wd / 2),
                (end[0] - nx * Wd / 2, end[1] - ny * Wd / 2), (base[0] - nx * Wd / 2, base[1] - ny * Wd / 2)]
        g.polygon(poly, fill=YELLOW + (255,))
        g.polygon([poly[0], poly[3], tip], fill=(240, 205, 160, 255))
    return supersample(w, h, d)


def icon_arrow(h):
    w = h

    def d(g, k, _):
        g.rectangle((w * 0.38 * k, 0, w * 0.62 * k, h * 0.5 * k), fill=YELLOW + (255,))
        g.polygon([(w * 0.12 * k, h * 0.45 * k), (w * 0.88 * k, h * 0.45 * k), (w * 0.5 * k, h * k)],
                  fill=YELLOW + (255,))
    return supersample(w, h, d)


def icon_down(h):
    """下がっていく棒グラフ"""
    w = int(h * 1.5)

    def d(g, k, _):
        g.line((30 * k, (h - 20) * k, (w - 20) * k, (h - 20) * k), fill=(255, 255, 255, 120), width=4 * k)
        vals = [0.85, 0.65, 0.45, 0.25]
        bw = (w - 100) / len(vals)
        for i, v in enumerate(vals):
            x = 50 + i * bw
            g.rounded_rectangle((x * k, (h - 20 - (h - 50) * v) * k, (x + bw * 0.62) * k, (h - 22) * k),
                                radius=10 * k, fill=(255, 255, 255, 200 - i * 30))
        # 下向きの矢印
        pts = [(60, 40), (w - 90, h - 110)]
        g.line([(p[0] * k, p[1] * k) for p in pts], fill=YELLOW + (255,), width=14 * k)
        ex, ey = (w - 90) * k, (h - 110) * k
        g.polygon([(ex + 30 * k, ey + 30 * k), (ex - 40 * k, ey + 10 * k), (ex + 10 * k, ey - 40 * k)],
                  fill=YELLOW + (255,))
    return supersample(w, h, d)


def icon_stairs(h):
    """階段を上る（伸びている途中）"""
    w = int(h * 1.5)

    def d(g, k, _):
        steps = 5
        sw, sh = (w - 40) / steps, (h - 30) / steps
        for i in range(steps):
            x = 20 + i * sw
            y = h - 10 - (i + 1) * sh
            g.rectangle((x * k, y * k, (x + sw) * k, (h - 10) * k), fill=(255, 255, 255, 40 + i * 25))
        # 途中の段にいる丸（自分）
        cx, cy = 20 + 2.5 * sw, h - 10 - 3 * sh - 34
        g.ellipse(((cx - 30) * k, (cy - 30) * k, (cx + 30) * k, (cy + 30) * k), fill=YELLOW + (255,))
    return supersample(w, h, d)


def icon_sprout(h):
    """芽（あとから伸びる）"""
    w = int(h * 1.1)

    def d(g, k, _):
        g.ellipse((w * 0.15 * k, (h - 70) * k, w * 0.85 * k, (h - 5) * k), fill=(120, 90, 70, 255))
        g.line((w * 0.5 * k, (h - 40) * k, w * 0.5 * k, h * 0.35 * k), fill=(140, 220, 140, 255), width=14 * k)
        g.ellipse((w * 0.5 * k, h * 0.2 * k, w * 0.86 * k, h * 0.45 * k), fill=(140, 220, 140, 255))
        g.ellipse((w * 0.14 * k, h * 0.32 * k, w * 0.5 * k, h * 0.55 * k), fill=(110, 200, 120, 255))
        g.ellipse((w * 0.82 * k, h * 0.02 * k, w * 0.94 * k, h * 0.14 * k), fill=YELLOW + (255,))
    return supersample(w, h, d)


def icon_pointdown(h):
    w = h

    def d(g, k, _):
        for i in range(2):
            y0 = i * h * 0.42
            g.line([(w * 0.2 * k, y0 * k), (w * 0.5 * k, (y0 + h * 0.4) * k), (w * 0.8 * k, y0 * k)],
                   fill=YELLOW + (255 - i * 90,), width=int(12 * k), joint="curve")
    return supersample(w, h, d)


ICONS = {
    "question": icon_question, "race": icon_race, "test": icon_test, "arrow": icon_arrow,
    "down": icon_down, "stairs": icon_stairs, "sprout": icon_sprout, "pointdown": icon_pointdown,
}


class IconItem:
    def __init__(self, name, h, delay):
        self.img = ICONS[name](h)
        self.h = self.img.height
        self.delay = delay

    def draw(self, frame, cy, local_t):
        p = ease_out((local_t - self.delay) / ITEM_FADE)
        if p <= 0:
            return 0.0
        s = 0.9 + 0.1 * p
        im = self.img.resize((int(self.img.width * s), int(self.img.height * s)), Image.LANCZOS) if s < 0.999 else self.img
        im = with_alpha(im, p)
        frame.alpha_composite(im, (int(W / 2 - im.width / 2), int(cy - im.height / 2)))
        return p


class Spacer:
    def __init__(self, h):
        self.h = h

    def draw(self, *a):
        return 0.0


def build_items(spec):
    items = []
    for it in spec:
        if it[0] == "_":
            items.append(Spacer(it[1]))
        elif it[0].startswith("@"):
            items.append(IconItem(it[0][1:], it[1], it[2]))
        else:
            items.append(TextLine(*it))
    total_h = sum(i.h for i in items)
    top = (SAFE_TOP + (H - SAFE_BOTTOM)) / 2 - total_h / 2
    y, placed = top, []
    for i in items:
        placed.append((i, y + i.h / 2))
        y += i.h
    return placed, top, y


# ---------- 背景（コード描画のやわらかい光） ----------
def make_glow(r, color, alpha):
    s = r * 2 + 240
    b = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(b).ellipse((120, 120, 120 + 2 * r, 120 + 2 * r), fill=color + (alpha,))
    return b.filter(ImageFilter.GaussianBlur(110))


BASE = Image.new("RGBA", (W, H), BG + (255,))
GLOWS = [
    (make_glow(380, (40, 80, 150), 90), 150, 380, 70, 50, 21.0),
    (make_glow(420, (40, 70, 140), 80), 900, 1550, 80, 60, 27.0),
    (make_glow(220, (255, 213, 79), 22), 880, 420, 50, 70, 17.0),
]


def background(t):
    img = BASE.copy()
    for g, bx, by, ax, ay, per in GLOWS:
        x = bx + ax * math.sin(2 * math.pi * t / per)
        y = by + ay * math.cos(2 * math.pi * t / per)
        img.alpha_composite(g, (int(x - g.width / 2), int(y - g.height / 2)))
    return img


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def with_alpha(img, a):
    if a >= 0.999:
        return img
    r, g, b, al = img.split()
    return Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))


# ---------- 合成 ----------
def prepare():
    scenes = []
    for s0, s1, spec in SCENES:
        placed, top, bottom = build_items(spec)
        if top < SAFE_TOP + SAFE_MARGIN - 1 or bottom > H - SAFE_BOTTOM - SAFE_MARGIN + 1:
            print(f"[warn] scene {s0}-{s1}: 内容が安全領域を超えています top={top:.0f} bottom={bottom:.0f}")
        scenes.append((s0, s1, placed))
    return scenes


def render(t, scenes, total):
    bg = background(t)
    for s0, s1, placed in scenes:
        if not (s0 <= t < s1):
            continue
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        local = t - s0
        for item, cy in placed:
            item.draw(layer, cy, local)
        # シーンのフェードイン／アウト
        a = min(1.0, local / SCENE_FADE if s0 > 0 else 1.0, (s1 - t) / SCENE_FADE)
        bg.alpha_composite(with_alpha(layer, max(0.0, a)))
    return bg


def main():
    scenes = prepare()
    total = SCENES[-1][1]
    if "--stills" in sys.argv:
        os.makedirs("stills", exist_ok=True)
        thumbs = []
        for i, (s0, s1, _) in enumerate(scenes, 1):
            im = render(s1 - SCENE_FADE - 0.05, scenes, total).convert("RGB")
            # 安全領域ガイド付きの確認用も保存
            guide = im.copy()
            gd = ImageDraw.Draw(guide)
            for y in (SAFE_TOP, H - SAFE_BOTTOM):
                gd.line((0, y, W, y), fill=(255, 60, 60), width=4)
            im.save(f"stills/scene_{i:02d}.png")
            thumbs.append(guide.resize((270, 480)))
        sheet = Image.new("RGB", (270 * 5, 480 * 2), BG)
        for i, th in enumerate(thumbs):
            sheet.paste(th, ((i % 5) * 270, (i // 5) * 480))
        sheet.save("stills/contact_sheet.png")
        print("saved stills/")
        return

    os.makedirs(os.path.dirname(OUTPUT) or ".", exist_ok=True)
    n = int(round(total * FPS))
    proc = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",          # 無音トラック
        "-map", "0:v", "-map", "1:a", "-shortest",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", OUTPUT,
    ], stdin=subprocess.PIPE)
    for fi in range(n):
        proc.stdin.write(render(fi / FPS, scenes, total).convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    print("wrote", OUTPUT)


if __name__ == "__main__":
    main()
