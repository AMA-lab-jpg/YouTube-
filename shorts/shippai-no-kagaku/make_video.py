"""『失敗の科学』紹介ショート動画（1080x1920, 30fps, 約61秒）のフレームを生成し、
ffmpeg にパイプして映像のみの MP4 を作る。ナレーションなし・テキストのみ。

使い方: python3 make_video.py build/video_noaudio.mp4
"""
import math
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 30
OUT = sys.argv[1] if len(sys.argv) > 1 else "video_noaudio.mp4"

FONT_DIR = "/usr/share/fonts/opentype/noto/"
SANS_B = FONT_DIR + "NotoSansCJK-Bold.ttc"
SANS_R = FONT_DIR + "NotoSansCJK-Regular.ttc"
SERIF_B = FONT_DIR + "NotoSerifCJK-Bold.ttc"

# 色
INK = (245, 241, 232)
MUTED = (178, 186, 204)
ACCENT = (255, 168, 92)      # 暖かいオレンジ
ACCENT2 = (120, 196, 255)    # 落ち着いた水色
RED = (255, 120, 120)
BG_TOP = (16, 22, 40)
BG_BOT = (30, 24, 44)

_font_cache = {}


def font(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size, index=0)
    return _font_cache[key]


# ---------- 要素の描画 ----------
def text_el(text, size, y, color=INK, path=SANS_B, delay=0.0, spacing=None,
            box=None, x=None):
    """テキスト要素。box=(fill_rgba, pad) を指定すると角丸の帯を背景に敷く。"""
    f = font(path, size)
    spacing = int(size * 0.35) if spacing is None else spacing
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = tmp.multiline_textbbox((0, 0), text, font=f, spacing=spacing, align="center")
    tw, th = int(math.ceil(bbox[2] - bbox[0])), int(math.ceil(bbox[3] - bbox[1]))
    pad = box[1] if box else 0
    shadow = 6
    img = Image.new("RGBA", (tw + pad * 2 + shadow * 4, th + pad * 2 + shadow * 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ox, oy = shadow * 2 + pad - bbox[0], shadow * 2 + pad - bbox[1]
    if box:
        d.rounded_rectangle(
            (shadow * 2, shadow * 2, shadow * 2 + tw + pad * 2, shadow * 2 + th + pad * 2),
            radius=int(pad * 0.9), fill=box[0])
    else:
        # 柔らかい影で可読性を確保
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).multiline_text((ox, oy + 4), text, font=f, fill=(0, 0, 0, 150),
                                          spacing=spacing, align="center")
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(6)))
        d = ImageDraw.Draw(img)
    d.multiline_text((ox, oy), text, font=f, fill=color, spacing=spacing, align="center")
    return {"img": img, "y": y, "delay": delay, "x": x}


def card_el(title, title_color, lines, y, delay, x_center=W // 2, w=900):
    """比較用のカード。"""
    h = 360
    img = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((20, 20, 20 + w, 20 + h), radius=36, fill=(255, 255, 255, 22),
                        outline=title_color + (200,), width=4)
    ft = font(SANS_B, 58)
    d.text((70, 60), title, font=ft, fill=title_color)
    fl = font(SANS_B, 46)
    for i, line in enumerate(lines):
        d.text((70, 160 + i * 78), line, font=fl, fill=INK)
    return {"img": img, "y": y, "delay": delay, "x": x_center}


def line_el(y, delay, w=140, color=ACCENT):
    img = Image.new("RGBA", (w, 8), color + (255,))
    return {"img": img, "y": y, "delay": delay, "x": None}


# ---------- シーン定義 ----------
# (開始秒, 終了秒, [要素...])
def build_scenes():
    S = []
    # 1. フック
    S.append((0.0, 6.0, [
        text_el("同じミスを", 76, 560, MUTED, delay=0.1),
        text_el("繰り返す組織", 112, 670, INK, delay=0.3),
        text_el("と", 60, 830, MUTED, delay=1.1),
        text_el("ミスから", 76, 940, MUTED, delay=1.6),
        text_el("成長する組織", 112, 1050, ACCENT, delay=1.8),
        text_el("何が違う？", 96, 1290, INK, delay=3.0,
                box=((255, 168, 92, 60), 34)),
    ]))
    # 2. 本の紹介
    S.append((6.0, 12.0, [
        text_el("今日の一冊", 54, 520, ACCENT, delay=0.1,
                box=((255, 168, 92, 40), 22)),
        text_el("失敗の科学", 150, 720, INK, path=SERIF_B, delay=0.5),
        line_el(900, 1.0),
        text_el("マシュー・サイド 著", 58, 980, MUTED, path=SANS_R, delay=1.3),
        text_el("ディスカヴァー・トゥエンティワン", 46, 1070, MUTED, path=SANS_R, delay=1.6),
        text_el("失敗から学べる人・組織と\n学べない人・組織の決定的な差", 54, 1260, INK, delay=2.6),
    ]))
    # 3. 具体例（エレイン・ブロミリーさんの事例）
    S.append((12.0, 24.0, [
        text_el("本に出てくる 実話", 50, 420, ACCENT2, delay=0.1,
                box=((120, 196, 255, 40), 22)),
        text_el("2005年 イギリス", 64, 560, MUTED, delay=0.5),
        text_el("簡単な鼻の手術の\nはずだった", 88, 700, INK, delay=1.0),
        text_el("麻酔の後、気道が確保できず\n酸素不足が続く", 58, 1000, INK, delay=3.2),
        text_el("看護師は打開策に気づき\n器具まで準備していた", 58, 1200, INK, delay=5.6),
        text_el("でも、その声は\n届かなかった", 92, 1420, RED, delay=8.0),
    ]))
    # 4. 夫はパイロット
    S.append((24.0, 32.0, [
        text_el("患者の夫は", 64, 520, MUTED, delay=0.1),
        text_el("航空機のパイロット", 92, 620, ACCENT2, delay=0.4),
        text_el("「航空業界なら\n事故は必ず調査され\n全員の教訓になる」", 70, 820, INK, delay=1.6),
        text_el("彼は報告書を公開し\n医療の安全改革を動かした", 58, 1220, INK, delay=4.4),
    ]))
    # 5. 比較
    S.append((32.0, 40.0, [
        text_el("失敗への向き合い方", 70, 440, INK, delay=0.1),
        card_el("航空業界", ACCENT2, ["失敗を記録して共有", "→ 同じ事故が減っていく"], 600, 0.6),
        card_el("当時の医療業界", RED, ["失敗は隠される", "→ 同じミスが繰り返される"], 1020, 2.2),
        text_el("差は「能力」ではなく「仕組み」", 56, 1470, ACCENT, delay=4.4),
    ]))
    # 6. 3つの教訓
    S.append((40.0, 50.0, [
        text_el("本書の教訓", 72, 420, ACCENT, delay=0.1),
        text_el("01", 64, 600, ACCENT2, delay=0.6),
        text_el("失敗は\"データ\"である", 72, 690, INK, delay=0.8),
        text_el("02", 64, 900, ACCENT2, delay=3.0),
        text_el("犯人探しより\n仕組みを直す", 72, 990, INK, delay=3.2),
        text_el("03", 64, 1270, ACCENT2, delay=5.6),
        text_el("小さく試して\n早く失敗する", 72, 1360, INK, delay=5.8),
    ]))
    # 7. メッセージ
    S.append((50.0, 56.0, [
        text_el("失敗を認めた人が", 80, 760, INK, delay=0.2),
        text_el("いちばん速く\n成長する。", 120, 900, ACCENT, path=SERIF_B, delay=1.0),
    ]))
    # 8. エンディング
    S.append((56.0, 61.0, [
        text_el("失敗が怖い人ほど\n読んでほしい一冊", 70, 600, INK, delay=0.1),
        text_el("失敗の科学", 130, 860, INK, path=SERIF_B, delay=0.7),
        text_el("マシュー・サイド 著", 54, 1040, MUTED, path=SANS_R, delay=1.0),
        text_el("保存して あとで読もう", 56, 1250, INK, delay=1.8,
                box=((255, 168, 92, 70), 28)),
    ]))
    return S


# ---------- 背景 ----------
def make_gradient():
    g = Image.new("RGB", (1, H))
    for yy in range(H):
        t = yy / (H - 1)
        g.putpixel((0, yy), tuple(int(BG_TOP[i] * (1 - t) + BG_BOT[i] * t) for i in range(3)))
    return g.resize((W, H)).convert("RGBA")


def make_blob(r, color, alpha):
    size = r * 2 + 200
    b = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(b).ellipse((100, 100, 100 + 2 * r, 100 + 2 * r), fill=color + (alpha,))
    return b.filter(ImageFilter.GaussianBlur(90))


BLOBS = [
    # (blob, 基準x, 基準y, 振幅x, 振幅y, 周期)
    (make_blob(360, (255, 150, 80), 70), 120, 300, 80, 60, 23.0),
    (make_blob(420, (90, 150, 255), 60), 820, 1500, 90, 70, 29.0),
    (make_blob(280, (190, 120, 255), 45), 900, 500, 60, 90, 19.0),
]


def background(t, base):
    img = base.copy()
    for blob, bx, by, ax, ay, period in BLOBS:
        x = bx + ax * math.sin(2 * math.pi * t / period)
        y = by + ay * math.cos(2 * math.pi * t / period)
        img.alpha_composite(blob, (int(x - blob.width / 2), int(y - blob.height / 2)))
    return img


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def with_alpha(img, a):
    if a >= 0.999:
        return img
    r, g, b, al = img.split()
    al = al.point(lambda v: int(v * a))
    return Image.merge("RGBA", (r, g, b, al))


def main():
    scenes = build_scenes()
    total = scenes[-1][1]
    nframes = int(round(total * FPS))
    base = make_gradient()

    proc = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", OUT,
    ], stdin=subprocess.PIPE)

    for fi in range(nframes):
        t = fi / FPS
        frame = background(t, base)
        for (s0, s1, els) in scenes:
            if not (s0 <= t < s1):
                continue
            local = t - s0
            out_a = 1.0 if t < total - 0.01 else 0.0
            # シーン終わり 0.45 秒でフェードアウト（最終シーンは 0.8 秒）
            fade_len = 0.8 if s1 == total else 0.45
            if s1 - t < fade_len:
                out_a = (s1 - t) / fade_len
            for el in els:
                p = ease_out((local - el["delay"]) / 0.6)
                if p <= 0:
                    continue
                a = p * out_a
                img = with_alpha(el["img"], a)
                dy = int((1 - p) * 40)
                cx = el["x"] if el["x"] is not None else W // 2
                frame.alpha_composite(img, (int(cx - img.width / 2), int(el["y"] - 12 + dy)))
        # 上部の進行バー
        d = ImageDraw.Draw(frame)
        d.rectangle((0, 0, W, 10), fill=(255, 255, 255, 30))
        d.rectangle((0, 0, int(W * t / total), 10), fill=ACCENT + (230,))
        proc.stdin.write(frame.convert("RGB").tobytes())
        if fi % 300 == 0:
            print(f"frame {fi}/{nframes}", flush=True)

    proc.stdin.close()
    proc.wait()
    print("wrote", OUT, f"{total}s")


if __name__ == "__main__":
    main()
