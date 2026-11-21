"""『サイコロジー・オブ・マネー』（モーガン・ハウセル著／ダイヤモンド社）紹介ショート
縦型 1080x1920 / 30fps / 56秒 / H.264 + AAC（自作BGM）

使い方:
  python3 make_video.py --stills   # 各シーンの静止画を stills/ に保存（レイアウト確認）
  python3 make_video.py            # BGMを合成して動画を書き出す

外部素材なし: 図形・グラフ・アイコン・BGMはすべてこのファイル内のコードで生成。
フォント: Noto Sans CJK JP Bold（SIL Open Font License 1.1）
"""
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

# =====================================================================
# 設定（テキスト・秒数・色はここを編集）
# =====================================================================
OUTPUT = os.path.join(HERE, "..", "..", "output", "psychology-of-money_short.mp4")
W, H, FPS = 1080, 1920, 30
SAFE_TOP, SAFE_BOTTOM = 150, 150      # 上下この範囲に文字を置かない
SAFE_MARGIN = 30
MAX_TEXT_W = 940                      # 1行の最大幅（超えたら自動縮小）
MAX_STATIC = 6.0                      # 同じ画面が続いてよい上限（秒）→超えたら警告

BG = (0x0E, 0x2A, 0x1F)               # 濃い緑 #0E2A1F
WHITE = (255, 255, 255)
GOLD = (0xFF, 0xC9, 0x4D)             # 強調色 #FFC94D
SUB = (186, 214, 198)                 # 補足用

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"  # index 0 = JP

SCENE_FADE = 0.4
ITEM_FADE = 0.45
EMPH_POP_DELAY = 0.25
EMPH_SCALE = 1.12
EMPH_RESERVE = 1.16

# 行: ("テキスト", サイズ, 表示開始秒[シーン内], 色) ／ {…} が金色＋拡大
# アイコン/図: ("@名前", 高さ, 表示開始秒) ／ 余白: ("_", 高さ)
# 注記: ("!テキスト", サイズ, 表示開始秒) → 画面下部（安全領域内）に小さく固定表示
SCENES = [
    # 1. フック 0〜4秒
    (0.0, 4.0, [
        ("@coin", 170, 0.0),
        ("_", 50),
        ("「月1万円しか", 84, 0.1),
        ("投資できないなら、", 84, 0.5),
        ("{意味ない}」", 104, 0.9),
        ("_", 40),
        ("…そう思ってない？", 76, 2.0),
    ]),
    # 2. 問いかけ 4〜10秒
    (4.0, 7.0, [
        ("世界一有名な投資家、", 76, 0.0),
        ("_", 20),
        ("{ウォーレン・バフェット}", 92, 0.6),
    ]),
    (7.0, 10.0, [
        ("その資産、", 84, 0.0),
        ("{いつ}増えたと思う？", 96, 0.6),
    ]),
    # 3. 具体例 10〜24秒
    (10.0, 15.5, [
        ("バフェットの資産（イメージ）", 52, 0.0, SUB),
        ("_", 20),
        ("@chart", 900, 0.2),
    ]),
    (15.5, 20.0, [
        ("@chart_static", 560, 0.0),
        ("_", 40),
        ("資産の{約96%}は、", 84, 0.3),
        ("{65歳}を過ぎてから増えた", 80, 1.1),
    ]),
    (20.0, 24.0, [
        ("@hourglass", 240, 0.0),
        ("_", 40),
        ("秘密は投資の腕より", 80, 0.3),
        ("「{時間}」", 130, 1.0),
    ]),
    # 4. 1年目への置きかえ 24〜40秒
    (24.0, 29.0, [
        ("@wallet", 220, 0.0),
        ("_", 40),
        ("新卒1年目は、", 84, 0.3),
        ("お金は{少ない}", 96, 1.0),
    ]),
    (29.0, 34.0, [
        ("@hourglass", 240, 0.0),
        ("_", 40),
        ("でも「{時間}」は、", 96, 0.3),
        ("{いちばん}持っている", 96, 1.2),
    ]),
    (34.0, 40.0, [
        ("@timeline", 360, 0.0),
        ("_", 40),
        ("22歳で始める1万円は、", 76, 0.6),
        ("35歳で始める1万円より", 76, 1.6),
        ("{長く育つ}", 120, 2.6),
    ]),
    # 5. 自分の一言 40〜48秒
    (40.0, 48.0, [
        ("@sprout", 240, 0.0),
        ("_", 40),
        ("読んで、", 84, 0.4),
        ("少額でも「{今}」", 104, 1.6),
        ("始めることにした", 96, 3.0),
    ]),
    # 6. 締め 48〜56秒
    (48.0, 52.0, [
        ("@book", 230, 0.0),
        ("_", 50),
        ("{『サイコロジー・オブ・マネー』}", 88, 0.2),
        ("_", 20),
        ("モーガン・ハウセル", 64, 0.8, SUB),
    ]),
    (52.0, 56.0, [
        ("詳しくは", 76, 0.0),
        ("プロフィールの", 84, 0.4),
        ("{楽天ROOM}から", 104, 0.8),
        ("@pointdown", 100, 1.4),
        ("!※投資をすすめる動画ではありません", 38, 0.0),
    ]),
]

# 棒グラフ（バフェットの年齢と資産のイメージ。値は最大を1とした概算比）
# 著書の数値（純資産845億ドルのうち815億ドルが65歳以降）をもとにした模式図
CHART = [
    ("30歳", 0.002), ("40歳", 0.005), ("50歳", 0.01), ("60歳", 0.03),
    ("65歳", 0.036), ("70歳", 0.33), ("80歳", 0.56), ("89歳", 1.0),
]
CHART_SPLIT = 4          # この番号以降（65歳の次から）を金色で強調
CHART_NOTE = "※概算のイメージ"

# BGM（自作・落ち着いた明るめ）
BGM_BPM = 84
BGM_GAIN_DB = -18        # 動画全体の目標ラウドネス（LUFS）

# =====================================================================
# 描画
# =====================================================================
_fc = {}


def font(size):
    if size not in _fc:
        _fc[size] = ImageFont.truetype(FONT_PATH, size, index=0)
    return _fc[size]


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def with_alpha(img, a):
    if a >= 0.999:
        return img
    r, g, b, al = img.split()
    return Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))


def parse_markup(text):
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
    asc, desc = f.getmetrics()
    w = int(math.ceil(f.getlength(text)))
    pad = 16
    img = Image.new("RGBA", (w + pad * 2, asc + desc + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((pad, pad + 5), text, font=f, fill=(0, 0, 0, 160))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(7)))
    ImageDraw.Draw(img).text((pad, pad), text, font=f, fill=color)
    return img, w


def emph_curve(t):
    peak = EMPH_SCALE + 0.08
    if t < 0.22:
        return 1.0 + (peak - 1.0) * ease_out(t / 0.22)
    if t < 0.5:
        return peak + (EMPH_SCALE - peak) * ease_out((t - 0.22) / 0.28)
    return EMPH_SCALE


class TextLine:
    def __init__(self, text, size, delay, color=WHITE):
        self.delay = delay
        segs = parse_markup(text)

        def line_w(ff):
            return sum(ff.getlength(s) * (EMPH_RESERVE if e else 1.0) for s, e in segs)
        f = font(size)
        while line_w(f) > MAX_TEXT_W and size > 30:
            size -= 2
            f = font(size)
        asc, desc = f.getmetrics()
        self.h = int((asc + desc) * 1.12)
        self.parts, x = [], 0
        for s, e in segs:
            img, w = seg_image(s, f, GOLD if e else color)
            slot = w * EMPH_RESERVE if e else w
            self.parts.append((img, x, e, slot))
            x += slot
        self.w = x
        self.has_emph = any(p[2] for p in self.parts)

    def change_times(self):
        t = [self.delay, self.delay + ITEM_FADE]
        if self.has_emph:
            t.append(self.delay + EMPH_POP_DELAY + 0.5)
        return t

    def draw(self, frame, cy, lt):
        p = ease_out((lt - self.delay) / ITEM_FADE)
        if p <= 0:
            return
        x0 = (W - self.w) / 2
        top = cy - self.h / 2 + (1 - p) * 36
        et = lt - self.delay - EMPH_POP_DELAY
        scale = 1.0 if et <= 0 else emph_curve(et)
        for img, xo, e, slot in self.parts:
            im = img
            if e and scale != 1.0:
                im = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
            im = with_alpha(im, p)
            cx = x0 + xo + slot / 2
            frame.alpha_composite(im, (int(cx - im.width / 2), int(top + self.h / 2 - im.height / 2)))


class Note:
    """画面下部に小さく固定表示する注記"""
    h = 0

    def __init__(self, text, size, delay):
        self.img, _ = seg_image(text, font(size), SUB)
        self.delay = delay

    def change_times(self):
        return [self.delay, self.delay + ITEM_FADE]

    def draw(self, frame, _cy, lt):
        p = ease_out((lt - self.delay) / ITEM_FADE)
        if p <= 0:
            return
        y = H - SAFE_BOTTOM - SAFE_MARGIN - self.img.height
        frame.alpha_composite(with_alpha(self.img, p), (int(W / 2 - self.img.width / 2), int(y)))


# ---------- 自作アイコン ----------
def ss(w, h, fn, k=3):
    big = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
    fn(ImageDraw.Draw(big), k)
    return big.resize((w, h), Image.LANCZOS)


def icon_coin(h):
    w = int(h * 1.6)

    def d(g, k):
        for i, (dx, dy) in enumerate([(0.22, 0.18), (0.5, 0.05), (0.78, 0.22)]):
            r = h * 0.38
            cx, cy = w * dx, h * dy + r + 4
            g.ellipse(((cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k), fill=GOLD + (255,),
                      outline=(200, 140, 30, 255), width=int(6 * k))
            g.ellipse(((cx - r * 0.7) * k, (cy - r * 0.7) * k, (cx + r * 0.7) * k, (cy + r * 0.7) * k),
                      outline=(220, 160, 40, 255), width=int(4 * k))
            g.text((cx * k, cy * k), "¥", font=font(int(r * 1.0 * k)), fill=(150, 100, 20, 255), anchor="mm")
    return ss(w, h, d)


def icon_hourglass(h):
    w = int(h * 0.75)

    def d(g, k):
        c = (240, 236, 220, 255)
        g.rounded_rectangle((0, 0, w * k, h * 0.09 * k), radius=8 * k, fill=c)
        g.rounded_rectangle((0, h * 0.91 * k, w * k, h * k), radius=8 * k, fill=c)
        top, mid, bot = h * 0.09, h * 0.5, h * 0.91
        g.polygon([(w * 0.1 * k, top * k), (w * 0.9 * k, top * k), (w * 0.55 * k, mid * k), (w * 0.45 * k, mid * k)],
                  outline=c, fill=(255, 255, 255, 30), width=int(5 * k))
        g.polygon([(w * 0.45 * k, mid * k), (w * 0.55 * k, mid * k), (w * 0.9 * k, bot * k), (w * 0.1 * k, bot * k)],
                  outline=c, fill=(255, 255, 255, 30), width=int(5 * k))
        # 砂
        g.polygon([(w * 0.3 * k, h * 0.3 * k), (w * 0.7 * k, h * 0.3 * k), (w * 0.52 * k, h * 0.48 * k),
                   (w * 0.48 * k, h * 0.48 * k)], fill=GOLD + (255,))
        g.polygon([(w * 0.5 * k, h * 0.72 * k), (w * 0.82 * k, h * 0.88 * k), (w * 0.18 * k, h * 0.88 * k)],
                  fill=GOLD + (255,))
        g.line((w * 0.5 * k, h * 0.5 * k, w * 0.5 * k, h * 0.72 * k), fill=GOLD + (255,), width=int(4 * k))
    return ss(w, h, d)


def icon_wallet(h):
    w = int(h * 1.4)

    def d(g, k):
        g.rounded_rectangle((10 * k, h * 0.18 * k, (w - 10) * k, (h - 6) * k), radius=26 * k,
                            fill=(120, 170, 140, 255))
        g.rounded_rectangle((w * 0.55 * k, h * 0.45 * k, (w - 10) * k, h * 0.75 * k), radius=18 * k,
                            fill=(90, 140, 110, 255))
        g.ellipse((w * 0.66 * k, h * 0.53 * k, w * 0.74 * k, h * 0.67 * k), fill=GOLD + (255,))
        # 小さなコイン1枚（少ない）
        r = h * 0.12
        g.ellipse(((w * 0.3 - r) * k, (h * 0.12 - r) * k, (w * 0.3 + r) * k, (h * 0.12 + r) * k), fill=GOLD + (255,))
    return ss(w, h, d)


def icon_sprout(h):
    w = int(h * 1.1)

    def d(g, k):
        g.ellipse((w * 0.15 * k, (h - 60) * k, w * 0.85 * k, (h - 4) * k), fill=(110, 80, 60, 255))
        g.line((w * 0.5 * k, (h - 34) * k, w * 0.5 * k, h * 0.35 * k), fill=(150, 225, 150, 255), width=int(14 * k))
        g.ellipse((w * 0.5 * k, h * 0.18 * k, w * 0.86 * k, h * 0.44 * k), fill=(150, 225, 150, 255))
        g.ellipse((w * 0.14 * k, h * 0.3 * k, w * 0.5 * k, h * 0.54 * k), fill=(120, 205, 130, 255))
        r = h * 0.07
        g.ellipse(((w * 0.88 - r) * k, (h * 0.1 - r) * k, (w * 0.88 + r) * k, (h * 0.1 + r) * k), fill=GOLD + (255,))
    return ss(w, h, d)


def icon_pointdown(h):
    w = h

    def d(g, k):
        for i in range(2):
            y0 = i * h * 0.42
            g.line([(w * 0.2 * k, y0 * k), (w * 0.5 * k, (y0 + h * 0.4) * k), (w * 0.8 * k, y0 * k)],
                   fill=GOLD + (255 - i * 90,), width=int(12 * k), joint="curve")
    return ss(w, h, d)


class Icon:
    def __init__(self, img, delay):
        self.img, self.h, self.delay = img, img.height, delay

    def change_times(self):
        return [self.delay, self.delay + ITEM_FADE]

    def draw(self, frame, cy, lt):
        p = ease_out((lt - self.delay) / ITEM_FADE)
        if p <= 0:
            return
        s = 0.9 + 0.1 * p
        im = self.img if s > 0.999 else self.img.resize((int(self.img.width * s), int(self.img.height * s)), Image.LANCZOS)
        frame.alpha_composite(with_alpha(im, p), (int(W / 2 - im.width / 2), int(cy - im.height / 2)))


class BarChart:
    """年齢ごとの資産の棒グラフ（棒が左から順に伸びる）"""

    def __init__(self, h, delay, animate=True):
        self.h, self.delay, self.animate = h, delay, animate
        self.w = 900
        self.grow = 0.45           # 1本が伸びる時間
        self.step = 0.42           # 次の棒が伸び始めるまで

    def change_times(self):
        if not self.animate:
            return [self.delay, self.delay + ITEM_FADE]
        end = self.delay + self.step * (len(CHART) - 1) + self.grow + 0.6
        return list(np.arange(self.delay, end, 0.5)) + [end]

    def draw(self, frame, cy, lt):
        a = ease_out((lt - self.delay) / ITEM_FADE)
        if a <= 0:
            return
        k = 2
        w, h = self.w, self.h
        img = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
        g = ImageDraw.Draw(img)
        lab_h = 70
        note_h = 50 if self.animate else 0
        base_y = h - lab_h - note_h
        top_y = 60
        n = len(CHART)
        slot = (w - 40) / n
        bw = slot * 0.64
        # 65歳ライン
        sx = 20 + slot * (CHART_SPLIT + 0.5) + slot * 0.5
        for yy in range(int(top_y), int(base_y), 24):
            g.line((sx * k, yy * k, sx * k, (yy + 12) * k), fill=GOLD + (170,), width=3 * k)
        g.text(((sx + 12) * k, (top_y - 6) * k), "65歳→", font=font(44 * k), fill=GOLD + (255,), anchor="lt")
        g.line((10 * k, base_y * k, (w - 10) * k, base_y * k), fill=(255, 255, 255, 140), width=3 * k)
        for i, (lab, v) in enumerate(CHART):
            t = 1.0 if not self.animate else ease_out((lt - self.delay - 0.2 - i * self.step) / self.grow)
            x = 20 + i * slot + (slot - bw) / 2
            bh = max(6, (base_y - top_y - 50) * v) * t
            col = GOLD if i > CHART_SPLIT else (200, 225, 210)
            if t > 0:
                g.rounded_rectangle((x * k, (base_y - bh) * k, (x + bw) * k, base_y * k), radius=8 * k,
                                    fill=col + (255,))
            g.text(((x + bw / 2) * k, (base_y + 14) * k), lab, font=font(36 * k),
                   fill=(230, 240, 235, 255), anchor="mt")
        if self.animate:
            g.text((w / 2 * k, (h - 34) * k), CHART_NOTE, font=font(30 * k), fill=SUB + (255,), anchor="mm")
        im = img.resize((w, h), Image.LANCZOS)
        frame.alpha_composite(with_alpha(im, a), (int(W / 2 - w / 2), int(cy - h / 2)))


class Timeline:
    """22歳スタートと35歳スタートの「育つ期間」の比較バー（65歳まで）"""

    def __init__(self, h, delay):
        self.h, self.delay, self.w = h, delay, 900

    def change_times(self):
        return [self.delay, self.delay + 0.4, self.delay + 1.6, self.delay + 2.2]

    def draw(self, frame, cy, lt):
        a = ease_out((lt - self.delay) / ITEM_FADE)
        if a <= 0:
            return
        k = 2
        w, h = self.w, self.h
        img = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
        g = ImageDraw.Draw(img)
        x0, x1 = 170, w - 30           # 22歳 〜 65歳
        age2x = lambda age: x0 + (x1 - x0) * (age - 22) / (65 - 22)
        rows = [("22歳", 22, GOLD, 0.2), ("35歳", 35, (200, 225, 210), 0.8)]
        for i, (lab, age, col, d) in enumerate(rows):
            y = 40 + i * 150
            t = ease_out((lt - self.delay - d) / 1.0)
            g.text((0, (y + 6) * k), lab, font=font(48 * k), fill=(255, 255, 255, 255))
            g.rounded_rectangle((x0 * k, y * k, x1 * k, (y + 70) * k), radius=35 * k, fill=(255, 255, 255, 28))
            xs, xe = age2x(age), age2x(age) + (x1 - age2x(age)) * t
            if t > 0:
                g.rounded_rectangle((xs * k, y * k, max(xe, xs + 70) * k, (y + 70) * k), radius=35 * k,
                                    fill=col + (255,))
        g.text(((x1) * k, (h - 40) * k), "65歳", font=font(34 * k), fill=SUB + (255,), anchor="rm")
        im = img.resize((w, h), Image.LANCZOS)
        frame.alpha_composite(with_alpha(im, a), (int(W / 2 - w / 2), int(cy - h / 2)))


def icon_book(h):
    """開いた本の汎用アイコン（実際の書影ではない）"""
    w = int(h * 1.5)

    def d(g, k):
        c1, c2 = (240, 236, 220, 255), (215, 210, 190, 255)
        g.polygon([(w * 0.5 * k, h * 0.12 * k), (w * 0.04 * k, 0), (w * 0.04 * k, h * 0.86 * k),
                   (w * 0.5 * k, h * k)], fill=c1)
        g.polygon([(w * 0.5 * k, h * 0.12 * k), (w * 0.96 * k, 0), (w * 0.96 * k, h * 0.86 * k),
                   (w * 0.5 * k, h * k)], fill=c2)
        for i in range(4):
            y = h * (0.25 + i * 0.15)
            g.line((w * 0.12 * k, y * k, w * 0.42 * k, (y + h * 0.05) * k), fill=(150, 160, 150, 255), width=int(5 * k))
            g.line((w * 0.58 * k, (y + h * 0.05) * k, w * 0.88 * k, y * k), fill=(150, 160, 150, 255), width=int(5 * k))
        g.line((w * 0.5 * k, h * 0.12 * k, w * 0.5 * k, h * k), fill=GOLD + (255,), width=int(6 * k))
    return ss(w, h, d)


ICONS = {"book": icon_book, "coin": icon_coin, "hourglass": icon_hourglass, "wallet": icon_wallet,
         "sprout": icon_sprout, "pointdown": icon_pointdown}


class Spacer:
    def __init__(self, h):
        self.h = h

    def change_times(self):
        return []

    def draw(self, *a):
        pass


def make_item(it):
    tag = it[0]
    if tag == "_":
        return Spacer(it[1])
    if tag.startswith("!"):
        return Note(tag[1:], it[1], it[2])
    if tag == "@chart":
        return BarChart(it[1], it[2], animate=True)
    if tag == "@chart_static":
        return BarChart(it[1], it[2], animate=False)
    if tag == "@timeline":
        return Timeline(it[1], it[2])
    if tag.startswith("@"):
        return Icon(ICONS[tag[1:]](it[1]), it[2])
    return TextLine(*it)


def build_scene(spec):
    items = [make_item(it) for it in spec]
    flow = [i for i in items if not isinstance(i, Note)]
    total_h = sum(i.h for i in flow)
    top = (SAFE_TOP + H - SAFE_BOTTOM) / 2 - total_h / 2
    y, placed = top, []
    for i in items:
        if isinstance(i, Note):
            placed.append((i, 0))
            continue
        placed.append((i, y + i.h / 2))
        y += i.h
    return placed, top, y


# ---------- 背景（コード描画） ----------
def make_glow(r, color, alpha):
    s = r * 2 + 240
    b = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(b).ellipse((120, 120, 120 + 2 * r, 120 + 2 * r), fill=color + (alpha,))
    return b.filter(ImageFilter.GaussianBlur(110))


BASE = Image.new("RGBA", (W, H), BG + (255,))
GLOWS = [
    (make_glow(380, (40, 110, 80), 90), 140, 360, 70, 50, 22.0),
    (make_glow(420, (30, 95, 70), 85), 920, 1560, 80, 60, 28.0),
    (make_glow(220, (255, 201, 77), 20), 880, 420, 50, 70, 17.0),
]


def background(t):
    img = BASE.copy()
    for g, bx, by, ax, ay, per in GLOWS:
        x = bx + ax * math.sin(2 * math.pi * t / per)
        y = by + ay * math.cos(2 * math.pi * t / per)
        img.alpha_composite(g, (int(x - g.width / 2), int(y - g.height / 2)))
    return img


def prepare():
    scenes = []
    for s0, s1, spec in SCENES:
        placed, top, bottom = build_scene(spec)
        if top < SAFE_TOP + SAFE_MARGIN - 1 or bottom > H - SAFE_BOTTOM - SAFE_MARGIN + 1:
            print(f"[warn] {s0}-{s1}s: 安全領域を超えています top={top:.0f} bottom={bottom:.0f}")
        # 同じ画面が MAX_STATIC 秒以上続かないかチェック
        changes = sorted({0.0, s1 - s0} | {c for it, _ in placed for c in it.change_times() if 0 <= c <= s1 - s0})
        longest = max(b - a for a, b in zip(changes, changes[1:]))
        if longest >= MAX_STATIC:
            print(f"[warn] {s0}-{s1}s: 画面が {longest:.1f} 秒変化しません")
        scenes.append((s0, s1, placed, longest))
    return scenes


def render(t, scenes):
    bg = background(t)
    for s0, s1, placed, _ in scenes:
        if not (s0 <= t < s1):
            continue
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        lt = t - s0
        for item, cy in placed:
            item.draw(layer, cy, lt)
        a = min(1.0, lt / SCENE_FADE if s0 > 0 else 1.0, (s1 - t) / SCENE_FADE)
        bg.alpha_composite(with_alpha(layer, max(0.0, a)))
    return bg


# =====================================================================
# BGM（自作・既存曲をもとにしていない）
# Dメジャー、BPM84。和音: D - Bm7 - Gmaj7 - A / D - F#m7 - Em7 - A7sus4→A7
# メロディはDメジャー・ペンタトニックで手書きした短いモチーフ
# =====================================================================
SR = 44100


def make_bgm(path, dur):
    rng = np.random.default_rng(21)
    n = int(SR * dur)
    L, R = np.zeros(n), np.zeros(n)
    beat = 60.0 / BGM_BPM
    bar = beat * 4
    midi = lambda m: 440.0 * 2 ** ((m - 69) / 12)

    def pluck(f, d, v, bright=1.0):
        t = np.arange(int(SR * d)) / SR
        env = np.exp(-t * 2.6) * (1 - np.exp(-t * 250))
        s = np.sin(2 * np.pi * f * t) + 0.3 * bright * np.sin(4 * np.pi * f * t) * np.exp(-t * 4) \
            + 0.08 * bright * np.sin(6 * np.pi * f * t) * np.exp(-t * 7)
        return s * env * v

    def pad(fs, d, v):
        t = np.arange(int(SR * d)) / SR
        env = np.minimum(t / 0.9, 1) * np.minimum((d - t) / 0.9, 1)
        s = sum(np.sin(2 * np.pi * (f + det) * t + rng.uniform(0, 6.3)) for f in fs for det in (-0.15, 0, 0.15))
        return s * env * v / (len(fs) * 3)

    def add(sig, start, pan=0.0):
        i = int(start * SR)
        if i >= n:
            return
        j = min(n, i + len(sig))
        L[i:j] += sig[:j - i] * (1 - pan) * 0.5
        R[i:j] += sig[:j - i] * (1 + pan) * 0.5

    chords = [
        [50, 54, 57, 62],  # D
        [47, 50, 54, 57],  # Bm7
        [43, 47, 50, 54],  # Gmaj7
        [45, 49, 52, 57],  # A
        [50, 54, 57, 62],  # D
        [42, 45, 49, 52],  # F#m7
        [40, 43, 47, 50],  # Em7
        [45, 50, 52, 55],  # A7sus4
    ]
    # 手書きメロディ（拍位置, 音, 長さ[拍]）。Dメジャー・ペンタトニック中心
    motif_a = [(0, 74, 1.5), (1.5, 76, 0.5), (2, 78, 1), (3, 76, 1)]
    motif_b = [(0, 81, 1), (1, 78, 1), (2, 76, 1.5), (3.5, 74, 0.5)]
    motif_c = [(0, 76, 1), (1, 78, 0.5), (1.5, 76, 0.5), (2, 74, 2)]
    motif_d = [(0, 71, 1), (1, 74, 1), (2, 76, 2)]
    melody = [motif_a, motif_b, motif_c, motif_d, motif_a, motif_b, motif_d, motif_c]

    bar_i, t = 0, 0.0
    while t < dur:
        ch = chords[bar_i % 8]
        add(pluck(midi(ch[0] - 12), bar, 0.30, 0.5), t, -0.1)
        add(pluck(midi(ch[0] - 12), beat * 2, 0.18, 0.5), t + beat * 2.5, -0.1)
        add(pad([midi(m) for m in ch], bar + 0.5, 0.16), t)
        # 軽いコード刻み（2・4拍目の裏）
        for b in (1.5, 3.5):
            for m in ch[1:]:
                add(pluck(midi(m + 12), beat * 1.2, 0.045), t + b * beat, 0.25)
        # メロディ（3小節目から）
        if bar_i >= 2:
            for pos, m, ln in melody[bar_i % 8]:
                add(pluck(midi(m), ln * beat + 0.6, 0.13, 0.8), t + pos * beat, -0.15)
        # やわらかいシェイカー（8分）
        if bar_i >= 4:
            for e in range(8):
                ns = rng.standard_normal(int(SR * 0.05)) * np.exp(-np.arange(int(SR * 0.05)) / SR * 90)
                add(ns * (0.025 if e % 2 else 0.012), t + e * beat / 2, 0.35)
        t += bar
        bar_i += 1

    def reverb(x, secs=1.8, wet=0.22):
        ir_n = int(SR * secs)
        ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / SR * 3.5)
        ir /= np.sqrt(np.sum(ir ** 2))
        m = len(x) + ir_n - 1
        nf = 1 << (m - 1).bit_length()
        y = np.fft.irfft(np.fft.rfft(x, nf) * np.fft.rfft(ir, nf), nf)[:len(x)]
        return x * (1 - wet) + y * wet

    L, R = reverb(L), reverb(R)
    tt = np.arange(n) / SR
    fade = np.clip(np.minimum(tt / 1.5, 1) * np.minimum((dur - tt) / 3.0, 1), 0, 1)
    L, R = L * fade, R * fade
    peak = max(np.abs(L).max(), np.abs(R).max())
    pcm = (np.stack([L, R], 1) / peak * 0.7 * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# =====================================================================
def main():
    scenes = prepare()
    total = SCENES[-1][1]
    stills = os.path.join(HERE, "stills")
    if "--stills" in sys.argv:
        os.makedirs(stills, exist_ok=True)
        thumbs = []
        for i, (s0, s1, _, longest) in enumerate(scenes, 1):
            im = render(s1 - SCENE_FADE - 0.05, scenes).convert("RGB")
            im.save(os.path.join(stills, f"scene_{i:02d}.png"))
            guide = im.copy()
            gd = ImageDraw.Draw(guide)
            for y in (SAFE_TOP, H - SAFE_BOTTOM):
                gd.line((0, y, W, y), fill=(255, 60, 60), width=4)
            thumbs.append(guide.resize((270, 480)))
            print(f"scene {i:02d}: {s0:>5.1f}-{s1:>5.1f}s  最長の静止 {longest:.1f}s")
        cols = 6
        sheet = Image.new("RGB", (270 * cols, 480 * math.ceil(len(thumbs) / cols)), BG)
        for i, th in enumerate(thumbs):
            sheet.paste(th, ((i % cols) * 270, (i // cols) * 480))
        sheet.save(os.path.join(stills, "contact_sheet.png"))
        return

    build = os.path.join(HERE, "build")
    os.makedirs(build, exist_ok=True)
    bgm = os.path.join(build, "bgm.wav")
    make_bgm(bgm, total)
    out = os.path.abspath(OUTPUT)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    proc = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", bgm,
        "-filter_complex", f"[1:a]lowpass=f=7000,loudnorm=I={BGM_GAIN_DB}:TP=-2:LRA=11[a]",
        "-map", "0:v", "-map", "[a]", "-shortest",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out,
    ], stdin=subprocess.PIPE)
    for fi in range(int(round(total * FPS))):
        proc.stdin.write(render(fi / FPS, scenes).convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    print("wrote", out)


if __name__ == "__main__":
    main()
