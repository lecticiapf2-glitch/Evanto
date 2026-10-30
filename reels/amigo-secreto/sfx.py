# Synthesizes original (license-free) SFX and places them on a timeline wav.
import sys, wave, numpy as np
sys.path.insert(0, sys.argv[2])
from plan import *

SR = 44100
rng = np.random.default_rng(7)
track = np.zeros((int((DUR + 1) * SR), 2), np.float32)


def db(x):
    return 10 ** (x / 20)


def bandpass(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def norm(x, peak_db):
    return x / (np.abs(x).max() + 1e-9) * db(peak_db)


def place(sig, t, pan=0.0):
    if sig.ndim == 1:
        sig = np.stack([sig * (1 - max(pan, 0)), sig * (1 + min(pan, 0))], 1)
    s = int(round(t * SR))
    track[s:s + len(sig)] += sig[:len(track) - s]


def key_click():
    n = int(0.035 * SR); tt = np.arange(n) / SR
    click = bandpass(rng.standard_normal(n), 1800, 6500) * np.exp(-tt / 0.004)
    body = np.sin(2 * np.pi * rng.uniform(170, 230) * tt) * np.exp(-tt / 0.012) * 0.5
    return norm(click + body, rng.uniform(-27, -24))


def whoosh(length, f0, f1, peak_at, peak_db):
    n = int(length * SR); tt = np.arange(n) / SR
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    hop = 512
    for k in range(0, n, hop):       # sweeping band, block-wise
        u = k / n
        fc = f0 * (f1 / f0) ** u
        seg = noise[max(0, k - hop):k + 2 * hop]
        y = bandpass(seg, fc * 0.6, fc * 1.6)
        out[k:k + hop] = y[min(k, hop):min(k, hop) + len(out[k:k + hop])]
    u = tt / length
    env = np.where(u < peak_at, (u / peak_at) ** 2, ((1 - u) / (1 - peak_at)) ** 1.5)
    return norm(out * env, peak_db)


def soft_tick():
    n = int(0.06 * SR); tt = np.arange(n) / SR
    s = np.sin(2 * np.pi * 1900 * tt) * np.exp(-tt / 0.010) + 0.4 * np.sin(2 * np.pi * 3800 * tt) * np.exp(-tt / 0.005)
    return norm(s, -22)


def shimmer(length):
    n = int(length * SR); tt = np.arange(n) / SR
    out = np.zeros((n, 2))
    for _ in range(26):                      # tiny glints spread along the sweep
        st = rng.uniform(0, length * 0.85); f = rng.uniform(3200, 8200)
        m = int(0.12 * SR); tm = np.arange(m) / SR
        g = np.sin(2 * np.pi * f * tm) * np.exp(-tm / 0.03) * rng.uniform(0.4, 1)
        pan = (st / length) * 1.2 - 0.6     # glints travel left -> right with the light
        s = int(st * SR); e = min(n, s + m)
        out[s:e, 0] += g[:e - s] * (1 - max(pan, 0)); out[s:e, 1] += g[:e - s] * (1 + min(pan, 0))
    env = np.sin(np.pi * np.clip(tt / length, 0, 1))[:, None] ** 0.7
    out *= env
    return out / np.abs(out).max() * db(-25)


def pen_swipe(length):
    n = int(length * SR); tt = np.arange(n) / SR
    x = bandpass(rng.standard_normal(n), 2200, 7000)
    grain = 0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 38 * tt + rng.uniform(0, 6)))
    u = tt / length
    env = np.minimum(u / 0.08, 1) * (1 - u) ** 0.8
    return norm(x * grain * env, -27)


# 1. Typewriter title: one key per letter group, exactly on the frame it appears
for t in TYPE_TIMES:
    place(key_click(), t - 0.005, pan=rng.uniform(-0.15, 0.15))
# 2. Snap zoom on the reaction "A FAMILIA FICOU" - whoosh lands with the zoom
place(whoosh(0.22, 700, 2600, 0.7, -21), 10.73 - 0.15)
# 3. "E AGORA?" punch-in - soft tick on the pop
place(soft_tick(), 22.43)
# 4. Shine sweep across "O NATAL TA CHEGANDO"
place(shimmer(SHINE["t1"] - SHINE["t0"]), SHINE["t0"])
# 5. Snap zoom on "ERREI, FUI BABACA"
place(whoosh(0.20, 800, 3000, 0.7, -22), 55.30 - 0.14)
# 6. Underline drawn under "SEGUE @lecticia.scott"
place(pen_swipe(UNDERLINE["t1"] - UNDERLINE["t0"] + 0.05), UNDERLINE["t0"])

out = np.clip(track, -1, 1)
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((out * 32767).astype(np.int16).tobytes())
print("sfx ok")
