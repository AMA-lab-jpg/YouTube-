"""『失敗の科学』紹介ショート v2（1080x1920, 30fps, 40秒）
- 航空業界のブラックボックスの話だけを、自分の言葉で言い換えて紹介
- 新卒1年目の目線での具体的な場面と提案
- 外部の画像素材は使わず、イラストはすべてこのスクリプト内で図形として描画
- フォント: Noto Sans CJK JP（SIL Open Font License 1.1）

使い方: python3 make_video_v2.py build/v2_noaudio.mp4
"""
import math
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 30
OUT = sys.argv[1] if len(sys.argv) > 1 else "v2_noaudio.mp4"

FONT_DIR = "/usr/share/fonts/opentype/noto/"
SANS_B = FONT_DIR + "NotoSansCJK-Bold.ttc"
SANS_R = FONT_DIR + "NotoSansCJK-Regular.ttc"

INK = (245, 241, 232)
MUTED = (178, 186, 204)
ACCENT = (255, 168, 92)
ACCENT2 = (120, 196, 255)
RED = (255, 120, 120)
GREEN = (140, 220, 170)
BG_TOP = (16, 22, 40)
BG_BOT = (30, 24, 44)

_fc = {}


def font(path, size):
    if (path, size) not in _fc:
        _fc[(path, size)] = ImageFont.truetype(path, size, index=0)  # index 0 = JP
    return _fc[(path, size)]


def el(img, y, delay, x=None, fade=0.5):
    return {"img": img, "y": y, "delay": delay, "x": x, "fade": fade}


def text_img(text, size, color=INK, path=SANS_B, box=None, spacing=None):
    f = font(path, size)
    spacing = int(size * 0.35) if spacing is None else spacing
    bb = ImageDraw.Draw(Image.new("RGBA", (1, 1))).multiline_textbbox(
        (0, 0), text, font=f, spacing=spacing, align="center")
    tw, th = int(math.ceil(bb[2] - bb[0])), int(math.ceil(bb[3] - bb[1]))
    pad = box[1] if box else 0
    m = 12
    img = Image.new("RGBA", (tw + pad * 2 + m * 2, th + pad * 2 + m * 2), (0, 0, 0, 0))
    ox, oy = m + pad - bb[0], m + pad - bb[1]
    if box:
        ImageDraw.Draw(img).rounded_rectangle((m, m, m + tw + pad * 2, m + th + pad * 2),
                                              radius=int(pad * 0.9), fill=box[0])
    else:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).multiline_text((ox, oy + 4), text, font=f, fill=(0, 0, 0, 150),
                                          spacing=spacing, align="center")
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(6)))
    ImageDraw.Draw(img).multiline_text((ox, oy), text, font=f, fill=color,
                                       spacing=spacing, align="center")
    return img


def T(text, size, y, delay, color=INK, path=SANS_B, box=None, x=None):
    return el(text_img(text, size, color, path, box), y, delay, x)


# ---------- 自作イラスト（2倍で描いて縮小 → なめらかに） ----------
def ss(w, h, draw_fn):
    big = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(big), 2)
    return big.resize((w, h), Image.LANCZOS)


def airplane_img(w=520, h=300):
    def d(g, k):
        c = (230, 236, 248, 255)
        # 胴体
        g.rounded_rectangle((40 * k, 125 * k, 470 * k, 175 * k), radius=25 * k, fill=c)
        g.polygon([(470 * k, 128 * k), (510 * k, 150 * k), (470 * k, 172 * k)], fill=c)
        # 主翼
        g.polygon([(230 * k, 150 * k), (330 * k, 150 * k), (210 * k, 270 * k), (170 * k, 270 * k)], fill=c)
        g.polygon([(230 * k, 150 * k), (330 * k, 150 * k), (210 * k, 30 * k), (170 * k, 30 * k)],
                  fill=(200, 210, 230, 255))
        # 尾翼
        g.polygon([(40 * k, 150 * k), (100 * k, 150 * k), (60 * k, 60 * k), (30 * k, 60 * k)], fill=c)
        # 窓
        for i in range(8):
            x = 300 * k + i * 20 * k
            g.ellipse((x, 140 * k, x + 10 * k, 150 * k), fill=(60, 90, 140, 255))
    return ss(w, h, d)


def blackbox_img(w=360, h=300):
    def d(g, k):
        # 実物のフライトレコーダーは見つけやすいオレンジ色
        g.rounded_rectangle((20 * k, 60 * k, 340 * k, 280 * k), radius=22 * k, fill=(255, 140, 40, 255))
        for i in range(5):  # 反射ストライプ
            x = 40 * k + i * 64 * k
            g.polygon([(x, 230 * k), (x + 30 * k, 230 * k), (x + 50 * k, 265 * k), (x + 20 * k, 265 * k)],
                      fill=(255, 255, 255, 220))
        g.rounded_rectangle((60 * k, 20 * k, 300 * k, 70 * k), radius=12 * k, fill=(60, 60, 70, 255))
        f = font(SANS_B, 34 * k)
        g.text((180 * k, 150 * k), "FLIGHT\nRECORDER", font=f, fill=(40, 30, 20, 255),
               anchor="mm", align="center", spacing=6 * k)
    return ss(w, h, d)


def doc_img(w=440, h=520, wrong=True):
    def d(g, k):
        g.rounded_rectangle((20 * k, 20 * k, 420 * k, 500 * k), radius=20 * k, fill=(250, 248, 242, 255))
        g.rectangle((60 * k, 70 * k, 300 * k, 95 * k), fill=(70, 80, 110, 255))  # 見出し
        for i, bw in enumerate([200, 260, 150, 230]):  # 棒グラフ
            y = 140 * k + i * 50 * k
            g.rounded_rectangle((60 * k, y, (60 + bw) * k, y + 30 * k), radius=6 * k,
                                fill=(120, 170, 230, 255))
        f = font(SANS_B, 46 * k)
        g.text((70 * k, 370 * k), "売上", font=f, fill=(50, 50, 60, 255))
        num = "1,200万" if wrong else "120万"
        g.text((200 * k, 370 * k), num, font=f, fill=(200, 40, 40, 255) if wrong else (40, 140, 80, 255))
        if wrong:
            g.ellipse((180 * k, 345 * k, 410 * k, 450 * k), outline=(230, 50, 50, 255), width=8 * k)
    return ss(w, h, d)


def memo_img(w=900, h=700):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    g = ImageDraw.Draw(img)
    g.rounded_rectangle((10, 10, w - 10, h - 10), radius=36, fill=(255, 250, 235, 245))
    g.rectangle((10, 10, w - 10, 100), fill=(255, 196, 120, 255))
    g.rounded_rectangle((10, 10, w - 10, 100), radius=36, fill=(255, 196, 120, 255))
    g.rectangle((10, 60, w - 10, 100), fill=(255, 196, 120, 255))
    g.text((w // 2, 56), "一言メモ", font=font(SANS_B, 50), fill=(60, 40, 20), anchor="mm")
    rows = [("何が起きた？", "売上を1ケタ多く書いていた"),
            ("なぜ？", "元データを貼って見直さなかった"),
            ("次から", "出す前に合計だけ検算する")]
    for i, (lab, body) in enumerate(rows):
        y = 150 + i * 180
        g.text((60, y), lab, font=font(SANS_B, 42), fill=(220, 110, 40))
        g.text((60, y + 62), body, font=font(SANS_B, 50), fill=(40, 40, 55))
        if i < 2:
            g.line((60, y + 150, w - 60, y + 150), fill=(220, 210, 190), width=3)
    return img


def arrow_down_img(w=120, h=120, color=ACCENT):
    def d(g, k):
        g.polygon([(20 * k, 40 * k), (100 * k, 40 * k), (60 * k, 105 * k)], fill=color + (255,))
        g.rectangle((48 * k, 0, 72 * k, 45 * k), fill=color + (255,))
    return ss(w, h, d)


def globe_share_img(w=640, h=170):
    """「共有される」を表す、小さな飛行機が並ぶアイコン列"""
    def d(g, k):
        for i in range(5):
            cx = (64 + i * 128) * k
            cy = 85 * k
            g.ellipse((cx - 50 * k, cy - 50 * k, cx + 50 * k, cy + 50 * k), fill=(120, 196, 255, 60),
                      outline=(120, 196, 255, 255), width=4 * k)
            c = (230, 236, 248, 255)
            g.rounded_rectangle((cx - 32 * k, cy - 6 * k, cx + 32 * k, cy + 6 * k), radius=6 * k, fill=c)
            g.polygon([(cx - 4 * k, cy), (cx + 10 * k, cy), (cx - 8 * k, cy + 28 * k), (cx - 16 * k, cy + 28 * k)], fill=c)
            g.polygon([(cx - 4 * k, cy), (cx + 10 * k, cy), (cx - 8 * k, cy - 28 * k), (cx - 16 * k, cy - 28 * k)], fill=c)
            g.polygon([(cx - 32 * k, cy), (cx - 22 * k, cy), (cx - 28 * k, cy - 16 * k), (cx - 34 * k, cy - 16 * k)], fill=c)
    return ss(w, h, d)


# ---------- シーン ----------
def build_scenes():
    S = []
    # 1. 冒頭2秒：問いかけ（即表示）
    S.append((0.0, 2.0, [
        el(text_img("新卒1年目、", 84, MUTED), 640, 0.0, fade=0.15),
        el(text_img("ミスを\n隠したくなったこと", 104, INK), 770, 0.0, fade=0.15),
        el(text_img("ありませんか？", 104, ACCENT), 1080, 0.15, fade=0.2),
    ]))
    # 2a. 航空業界（前半）
    S.append((2.0, 7.5, [
        T("『失敗の科学』で知った話", 46, 380, 0.0, ACCENT2, box=((120, 196, 255, 40), 22)),
        el(airplane_img(), 500, 0.3),
        T("飛行機には\n「ブラックボックス」がある", 76, 860, 0.8),
        el(blackbox_img(), 1120, 1.6),
        T("事故のときの操作や会話を\n記録している装置", 48, 1450, 2.4, MUTED),
    ]))
    # 2b. 航空業界（後半）
    S.append((7.5, 13.0, [
        T("事故が起きたら回収して", 64, 470, 0.0),
        T("何が起きたか\nなぜ起きたかを調べる", 76, 580, 0.5, ACCENT),
        el(globe_share_img(), 900, 1.6),
        T("わかったことは業界中に共有され\n手順や機体の改善につながる", 52, 1110, 2.0),
        T("責める材料じゃなく\n次を防ぐ材料にしてる", 64, 1360, 3.3, ACCENT2),
    ]))
    # 3. 新卒1年目の場面
    S.append((13.0, 21.0, [
        T("で、自分に置きかえると…", 56, 380, 0.0, MUTED),
        T("先輩に頼まれた資料", 72, 490, 0.6),
        el(doc_img(wrong=True), 640, 1.2),
        T("提出したあとで\n数字のミスに気づいた", 72, 1210, 2.2, RED),
        T("正直「こっそり直せばバレないかも」\nって思っちゃう", 50, 1460, 4.4, INK),
    ]))
    # 4. 提案
    S.append((21.0, 34.0, [
        T("自分なりの\n「ブラックボックス」を\n作ってみるのはどうだろう", 64, 330, 0.0, ACCENT),
        el(memo_img(), 690, 1.8),
        T("これを添えて先輩に報告", 62, 1430, 5.2),
        T("同じミスを防ぎやすくなるし\n黙ってるより、気持ちもラクだと思う", 50, 1560, 7.5, ACCENT2),
    ]))
    # 5. 締め
    S.append((34.0, 40.0, [
        T("ほかの業界の話は", 70, 640, 0.1),
        T("本で。", 120, 760, 0.5, ACCENT),
        T("失敗の科学 ／ マシュー・サイド 著", 48, 960, 1.0, MUTED, path=SANS_R),
        el(arrow_down_img(), 1110, 1.6),
        T("プロフィールの楽天ROOMから", 60, 1260, 1.8, INK, box=((255, 168, 92, 70), 30)),
    ]))
    return S


# ---------- 背景・合成 ----------
def make_gradient():
    g = Image.new("RGB", (1, H))
    for yy in range(H):
        t = yy / (H - 1)
        g.putpixel((0, yy), tuple(int(BG_TOP[i] * (1 - t) + BG_BOT[i] * t) for i in range(3)))
    return g.resize((W, H)).convert("RGBA")


def make_blob(r, color, alpha):
    s = r * 2 + 200
    b = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(b).ellipse((100, 100, 100 + 2 * r, 100 + 2 * r), fill=color + (alpha,))
    return b.filter(ImageFilter.GaussianBlur(90))


BLOBS = [
    (make_blob(360, (255, 150, 80), 70), 120, 300, 80, 60, 23.0),
    (make_blob(420, (90, 150, 255), 60), 820, 1500, 90, 70, 29.0),
    (make_blob(280, (190, 120, 255), 45), 900, 500, 60, 90, 19.0),
]


def background(t, base):
    img = base.copy()
    for blob, bx, by, ax, ay, p in BLOBS:
        x = bx + ax * math.sin(2 * math.pi * t / p)
        y = by + ay * math.cos(2 * math.pi * t / p)
        img.alpha_composite(blob, (int(x - blob.width / 2), int(y - blob.height / 2)))
    return img


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def with_alpha(img, a):
    if a >= 0.999:
        return img
    r, g, b, al = img.split()
    return Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))


def render_frame(t, scenes, base, total):
    frame = background(t, base)
    for s0, s1, els in scenes:
        if not (s0 <= t < s1):
            continue
        local = t - s0
        fade_len = 0.8 if s1 == total else 0.35
        out_a = min(1.0, (s1 - t) / fade_len)
        for e in els:
            p = ease_out((local - e["delay"]) / e["fade"])
            if p <= 0:
                continue
            img = with_alpha(e["img"], p * out_a)
            cx = e["x"] if e["x"] is not None else W // 2
            frame.alpha_composite(img, (int(cx - img.width / 2), int(e["y"] - 12 + (1 - p) * 40)))
    d = ImageDraw.Draw(frame)
    d.rectangle((0, 0, W, 10), fill=(255, 255, 255, 30))
    d.rectangle((0, 0, int(W * t / total), 10), fill=ACCENT + (230,))
    return frame


def main():
    scenes = build_scenes()
    total = scenes[-1][1]
    base = make_gradient()
    n = int(round(total * FPS))
    proc = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT,
    ], stdin=subprocess.PIPE)
    for fi in range(n):
        proc.stdin.write(render_frame(fi / FPS, scenes, base, total).convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    print("wrote", OUT, f"{total}s")


if __name__ == "__main__":
    main()
