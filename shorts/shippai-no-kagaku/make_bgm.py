"""柔らかめのオリジナルBGM（ピアノ風 + パッド）を合成して WAV に書き出す。
著作権フリー：すべて numpy で一から生成している。
"""
import sys
import wave
import numpy as np

SR = 44100
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else 62.0
OUT = sys.argv[1] if len(sys.argv) > 1 else "bgm.wav"
BPM = 72
BEAT = 60.0 / BPM
BAR = BEAT * 4

rng = np.random.default_rng(7)
n = int(SR * DUR)
L = np.zeros(n)
R = np.zeros(n)


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def piano(freq, dur, vel):
    t = np.arange(int(SR * dur)) / SR
    env = np.exp(-t * 2.2) * (1 - np.exp(-t * 300))
    tone = (np.sin(2 * np.pi * freq * t)
            + 0.35 * np.sin(2 * np.pi * 2 * freq * t) * np.exp(-t * 3)
            + 0.12 * np.sin(2 * np.pi * 3 * freq * t) * np.exp(-t * 5))
    return tone * env * vel


def pad(freqs, dur, vel):
    t = np.arange(int(SR * dur)) / SR
    att = np.minimum(t / 1.2, 1.0)
    rel = np.minimum((dur - t) / 1.2, 1.0)
    env = att * rel
    s = np.zeros_like(t)
    for f in freqs:
        for det in (-0.12, 0.0, 0.12):  # 軽いデチューンで柔らかく
            s += np.sin(2 * np.pi * (f + det) * t + rng.uniform(0, 6.28))
    return s * env * vel / (len(freqs) * 3)


def add(_buf, sig, start, pan=0.0):
    i = int(start * SR)
    j = min(n, i + len(sig))
    if i >= n:
        return
    seg = sig[: j - i]
    L[i:j] += seg * (1 - pan) * 0.5
    R[i:j] += seg * (1 + pan) * 0.5


# Fmaj7 - Em7 - Dm7 - Cmaj7 / Fmaj7 - G - Em7 - Am7 （穏やかな進行）
chords = [
    [53, 57, 60, 64],  # Fmaj7
    [52, 55, 59, 62],  # Em7
    [50, 53, 57, 60],  # Dm7
    [48, 52, 55, 59],  # Cmaj7
    [53, 57, 60, 64],  # Fmaj7
    [55, 59, 62, 65],  # G7
    [52, 55, 59, 62],  # Em7
    [57, 60, 64, 67],  # Am7
]
# メロディ風アルペジオ（各小節8分音符）
arp_pat = [0, 2, 3, 1, 2, 3, 2, 1]

t = 0.0
bar_i = 0
while t < DUR:
    ch = chords[bar_i % len(chords)]
    # ベース
    add(L, piano(midi(ch[0] - 12), BAR, 0.32), t, -0.1)
    # パッド
    add(L, pad([midi(m) for m in ch], BAR + 0.6, 0.20), t, 0.0)
    # アルペジオ（最初の2小節は休み → 静かに始まる）
    if bar_i >= 1:
        for k, idx in enumerate(arp_pat):
            note = ch[idx] + 12
            vel = 0.16 + 0.04 * rng.random()
            pan = (idx - 1.5) * 0.25
            add(L, piano(midi(note), BEAT * 2.5, vel), t + k * BEAT / 2, pan)
    # 時々高音のきらめき
    if bar_i >= 2 and bar_i % 2 == 0:
        add(L, piano(midi(ch[3] + 24), BEAT * 3, 0.06), t + BEAT * 2.5, 0.4)
    t += BAR
    bar_i += 1


# 簡易リバーブ（指数減衰ノイズとの畳み込み）
def reverb(x, secs=2.2, wet=0.28):
    ir_n = int(SR * secs)
    ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / SR * 3.0)
    ir /= np.sqrt(np.sum(ir ** 2))
    m = len(x) + ir_n - 1
    nfft = 1 << (m - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[: len(x)]
    return x * (1 - wet) + y * wet


L = reverb(L)
R = reverb(R)

# ソフトなローパス（1極）で角を取る
try:
    from scipy.signal import lfilter
    a = np.exp(-2 * np.pi * 5000 / SR)
    L = lfilter([1 - a], [1, -a], L)
    R = lfilter([1 - a], [1, -a], R)
except ImportError:
    pass

# フェードイン/アウト
tt = np.arange(n) / SR
fade = np.minimum(tt / 2.0, 1.0) * np.minimum((DUR - tt) / 3.5, 1.0)
fade = np.clip(fade, 0, 1)
L *= fade
R *= fade

peak = max(np.abs(L).max(), np.abs(R).max())
gain = 0.6 / peak  # ピーク -4.4dBFS 程度
stereo = np.stack([L * gain, R * gain], axis=1)
pcm = (stereo * 32767).astype(np.int16)

with wave.open(OUT, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", OUT, DUR, "s")
