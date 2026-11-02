# Same format as the "Amigo secreto" final: jump cuts on long pauses with alternating punch-in,
# snap zooms with whoosh on reactions, brush-script highlights on top (baby yellow), full captions at the bottom.
# usage: python3 edit.py SRC.mp4 OUT.mp4 WORKDIR   (env PREVIEW=t1,t2 renders stills at OUTPUT times)
import json, os, re, subprocess, sys, wave
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
SRC, OUT, WD = sys.argv[1:4]
sys.path.insert(0, WD)
from plan import *

W, H, OW, OH = 576, 1024, 1080, 1920
BASE = OW / W
SR = 48000
words = json.load(open(f"{WD}/words.json"))["words"]
words = [w for w in words if w.get("type", "word") == "word"]

# ---------------- timeline: source segments kept ----------------
segs, cur0 = [], START
for a, b in zip(words, words[1:]):
    gap = b["start"] - a["end"]
    keep = KEEP_GAPS.get(round(a["end"], 2))
    if keep is None and gap > MAX_GAP:
        keep = (HEAD, TAIL)
    if keep and gap > keep[0] + keep[1]:
        segs.append((cur0, a["end"] + keep[0]))
        cur0 = b["start"] - keep[1]
segs.append((cur0, END))
fr = lambda t: int(round(t * FPS))
segs = [(fr(a), fr(b)) for a, b in segs]                 # frame-aligned so audio and video cut together
src_frames = [f for a, b in segs for f in range(a, b)]
NOUT = len(src_frames)
seg_start_out = np.cumsum([0] + [b - a for a, b in segs])[:-1]


def to_out(t):                                           # source seconds -> output seconds
    f = t * FPS
    for (a, b), o in zip(segs, seg_start_out):
        if f < b:
            return (o + max(f - a, 0)) / FPS
    return NOUT / FPS


print(f"segments {len(segs)}  {START:.1f}-{END:.1f}s source -> {NOUT / FPS:.1f}s output")

# ---------------- zoom plan (output time) ----------------
cuts = [o / FPS for o in seg_start_out]
snaps = [(to_out(t), z, to_out(e)) for t, z, e in SNAPS]


def ease(u):
    u = min(max(u, 0.0), 1.0); return 1 - (1 - u) ** 3


def zoom_at(t):
    for s, z, e in snaps:
        if s <= t < e:
            base = zoom_base(s - 1e-3)
            return base + (z - base) * ease((t - s) / 0.10)
    return zoom_base(t)


def zoom_base(t):
    k = max(i for i, c in enumerate(cuts) if c <= t + 1e-6)
    return ZOOM_ALT[k % 2]


# ---------------- text sprites ----------------
def halo(img, layers):
    a = img.split()[-1]
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    for blur, k, col in layers:
        l = Image.new("RGBA", img.size, col + (255,))
        l.putalpha(a.filter(ImageFilter.GaussianBlur(blur)).point(lambda v, k=k: int(v * k)))
        out = Image.alpha_composite(out, l)
    return Image.alpha_composite(out, img)


def kw_sprite(text):
    size = KW_SIZE
    f = ImageFont.truetype(KW_FONT, size)
    while f.getlength(text) > KW_MAXW:
        size -= 2; f = ImageFont.truetype(KW_FONT, size)
    pad, wm = 40, f.getlength(text)
    img = Image.new("RGBA", (int(wm) + 2 * pad, int(size * 1.45) + 2 * pad), (0, 0, 0, 0))
    base = pad + size
    ImageDraw.Draw(img).text((img.width / 2, base), text, font=f, fill=KW_COLOR + (255,), anchor="ms",
                             stroke_width=2, stroke_fill=KW_COLOR + (255,))
    letters = np.array(img)[..., 3].copy()
    out = halo(img, [(10, 0.6, (45, 30, 20)), (2, 0.55, (45, 30, 20))])
    return np.array(out), letters, base - img.height / 2 + 16, wm


def sub_sprite(text):
    f = ImageFont.truetype(SUB_FONT, SUB_SIZE)
    while f.getlength(text) > SUB_MAXW:
        f = ImageFont.truetype(SUB_FONT, f.size - 2)
    pad = 30
    img = Image.new("RGBA", (int(f.getlength(text)) + 2 * pad, int(SUB_SIZE * 1.3) + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((img.width / 2, img.height / 2), text, font=f, fill=(255, 255, 255, 255),
                             anchor="mm", stroke_width=5, stroke_fill=(0, 0, 0, 255))
    return np.array(halo(img, [(8, 0.45, (0, 0, 0))]))


def over(o, spr, cx, cy, scale=1.0, alpha=1.0):
    if scale != 1.0:
        spr = cv2.resize(spr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
    h, w = spr.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, OW), min(y0 + h, OH)
    s = spr[ya - y0:yb - y0, xa - x0:xb - x0].astype(np.float32)
    a = s[..., 3:4] / 255 * alpha
    o[ya:yb, xa:xb] = (o[ya:yb, xa:xb] * (1 - a) + s[..., 2::-1] * a).astype(np.uint8)


def back_out(u):
    u = min(max(u, 0), 1); c = 1.6
    return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2


KW = [(to_out(a), to_out(b), kw_sprite(t), t, sfx) for a, b, t, sfx in KEYWORDS]


def captions():
    ws = [dict(w, text=REPLACE.get(w["text"], w["text"])) for w in words if round(w["start"], 2) not in DROP_AT]
    ws = [dict(w, start=to_out(w["start"]), end=to_out(w["end"])) for w in ws]
    out, cur = [], []
    for i, w in enumerate(ws):
        cur.append(w)
        nxt = ws[i + 1] if i + 1 < len(ws) else None
        txt = " ".join(x["text"] for x in cur)
        if (nxt is None or re.search(r"[.,?!:]\"?$", w["text"]) or len(cur) >= 4
                or len(txt) + 1 + len(nxt["text"]) > 22 or nxt["start"] - w["end"] > 0.35):
            out.append(cur); cur = []
    res = []
    for k, c in enumerate(out):
        text = re.sub(r"[\"“”]", "", " ".join(x["text"] for x in c))
        text = re.sub(r"[.,:;]+(?=\s|$)", "", text).strip()
        s, e = c[0]["start"], c[-1]["end"]
        nxt = out[k + 1][0]["start"] if k + 1 < len(out) else e + 0.6
        e = max(e + 0.12, s + 0.45)
        res.append((s - 0.03, min(e, nxt), sub_sprite(text)))
    return res


SUBS = captions()


def draw_keywords(o, t):
    for a, b, (spr, letters, ul_dy, wm), text, sfx in KW:
        if not (a <= t <= b + 0.15):
            continue
        sc = 0.82 + 0.18 * back_out((t - a) / 0.16)
        al = min(1, (t - a) / 0.08) * (1 if t <= b else 1 - (t - b) / 0.15)
        s = spr
        if sfx == "shimmer" and t - a <= SHINE_LEN:
            v = (t - a) / SHINE_LEN
            hh, ww = letters.shape
            ys, xs = np.mgrid[0:hh, 0:ww].astype(np.float32)
            band = np.exp(-(((xs - (-80 + (ww + 160) * v)) + (ys - hh / 2) * 0.5) / 45) ** 2)
            ga = np.clip(cv2.GaussianBlur(letters.astype(np.float32), (0, 0), 10) * band * 1.4 / 255, 0, 1)[..., None]
            s = spr.copy()
            a0 = s[..., 3:4].astype(np.float32) / 255
            na = a0 + ga * (1 - a0)
            light = np.array([255, 246, 222], np.float32)
            s[..., :3] = ((s[..., :3] * a0 + light * ga * (1 - a0)) / np.maximum(na, 1e-3)).astype(np.uint8)
            s[..., 3] = (na[..., 0] * 255).astype(np.uint8)
        over(o, s, OW / 2, KW_Y, sc, al)
        if sfx == "pen" and t >= a:
            pr = ease((t - a) / UNDERLINE_LEN)
            y = int(KW_Y + ul_dy); x0 = int(OW / 2 - wm / 2); x1 = int(x0 + wm * pr)
            layer = o.copy()
            cv2.line(layer, (x0, y + 3), (x1, y + 3), (20, 30, 45), 7, cv2.LINE_AA)
            cv2.line(layer, (x0, y), (x1, y), KW_COLOR[::-1], 6, cv2.LINE_AA)
            cv2.addWeighted(layer, al, o, 1 - al, 0, dst=o)


def draw_subs(o, t):
    for a, b, spr in SUBS:
        if a <= t < b:
            over(o, spr, OW / 2, SUB_Y, 0.94 + 0.06 * ease((t - a) / 0.10), min(1, (t - a) / 0.06))
            break


# ---------------- SFX (original, synthesized) ----------------
rng = np.random.default_rng(7)


def db(x): return 10 ** (x / 20)


def bandpass(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def norm(x, pk): return x / (np.abs(x).max() + 1e-9) * db(pk)


def whoosh(length, f0, f1, peak_at, pk):
    n = int(length * SR); noise = rng.standard_normal(n); out = np.zeros(n); hop = 512
    for k in range(0, n, hop):
        fc = f0 * (f1 / f0) ** (k / n)
        seg = noise[max(0, k - hop):k + 2 * hop]
        y = bandpass(seg, fc * 0.6, fc * 1.6)
        out[k:k + hop] = y[min(k, hop):min(k, hop) + len(out[k:k + hop])]
    u = np.arange(n) / n
    env = np.where(u < peak_at, (u / peak_at) ** 2, ((1 - u) / (1 - peak_at)) ** 1.5)
    return norm(out * env, pk)


def tick():
    tt = np.arange(int(0.06 * SR)) / SR
    return norm(np.sin(2 * np.pi * 1900 * tt) * np.exp(-tt / 0.010) + 0.4 * np.sin(2 * np.pi * 3800 * tt) * np.exp(-tt / 0.005), -22)


def pop():
    tt = np.arange(int(0.09 * SR)) / SR
    f = 900 * np.exp(-tt / 0.02) + 320
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.025), -21)


def shimmer(length):
    n = int(length * SR); out = np.zeros((n, 2))
    for _ in range(26):
        st = rng.uniform(0, length * 0.85); f = rng.uniform(3200, 8200)
        tm = np.arange(int(0.12 * SR)) / SR
        g = np.sin(2 * np.pi * f * tm) * np.exp(-tm / 0.03) * rng.uniform(0.4, 1)
        pan = (st / length) * 1.2 - 0.6; s = int(st * SR); e = min(n, s + len(g))
        out[s:e, 0] += g[:e - s] * (1 - max(pan, 0)); out[s:e, 1] += g[:e - s] * (1 + min(pan, 0))
    out *= (np.sin(np.pi * np.arange(n) / n) ** 0.7)[:, None]
    return out / np.abs(out).max() * db(-25)


def pen(length):
    n = int(length * SR); tt = np.arange(n) / SR
    x = bandpass(rng.standard_normal(n), 2200, 7000) * (0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 38 * tt)))
    u = tt / length
    return norm(x * np.minimum(u / 0.08, 1) * (1 - u) ** 0.8, -27)


def build_audio():
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", SRC, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True).stdout
    src = np.frombuffer(raw, np.float32).reshape(-1, 2)
    parts, fade = [], int(0.008 * SR)
    for a, b in segs:                                    # same frame-aligned cuts, tiny fades = no clicks
        p = src[int(a / FPS * SR):int(b / FPS * SR)].copy()
        ramp = np.linspace(0, 1, fade)[:, None]
        p[:fade] *= ramp; p[-fade:] *= ramp[::-1]
        parts.append(p)
    voice = np.concatenate(parts)
    fx = np.zeros_like(voice)

    def place(sig, t):
        if sig.ndim == 1: sig = np.stack([sig, sig], 1)
        s = int(round(t * SR)); e = min(len(fx), s + len(sig)); fx[s:e] += sig[:e - s]
    for t, z, e in snaps:
        place(whoosh(0.22, 700, 2600, 0.7, -21), t - 0.15)
    for a, b, _, text, sfx in KW:
        if sfx == "shimmer": place(shimmer(SHINE_LEN), a)
        elif sfx == "tick": place(tick(), a)
        elif sfx == "pop": place(pop(), a)
        elif sfx == "pen": place(pen(UNDERLINE_LEN + 0.05), a)
    mix = voice + fx
    n = len(mix); tail = int(FADE_OUT * SR)
    mix[n - tail:] *= np.linspace(1, 0, tail)[:, None]
    peak = np.abs(mix).max()
    if peak > 0.97: mix *= 0.97 / peak
    with wave.open(f"{WD}/mix.wav", "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())


# ---------------- render ----------------
PREVIEW = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
if not PREVIEW:
    build_audio()
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
enc = None if PREVIEW else subprocess.Popen(
    ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
     "-i", f"{WD}/mix.wav", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
     "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
keep = set(src_frames)
si, oi = 0, 0
while oi < NOUT:
    b = dec.stdout.read(W * H * 3)
    if len(b) < W * H * 3:
        break
    if si in keep:
        t = oi / FPS
        if not PREVIEW or any(abs(t - x) < 0.5 / FPS for x in PREVIEW):
            f = np.frombuffer(b, np.uint8).reshape(H, W, 3)
            s = BASE * zoom_at(t)
            M = np.array([[s, 0, OW / 2 - W / 2 * s], [0, s, OH * ANCHOR_Y - H * ANCHOR_Y * s]], np.float32)
            o = cv2.warpAffine(f, M, (OW, OH), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
            draw_keywords(o, t)
            draw_subs(o, t)
            rem = NOUT / FPS - t
            if rem < FADE_OUT:
                o = (o.astype(np.float32) * max(rem / FADE_OUT, 0)).astype(np.uint8)
            if PREVIEW:
                cv2.imwrite(f"{OUT}_{t:.2f}.jpg", o)
            else:
                enc.stdin.write(o.tobytes())
        oi += 1
        if PREVIEW and t > max(PREVIEW):
            break
    si += 1
dec.kill()
if enc:
    enc.stdin.close(); enc.wait()
print("frames", oi, "keywords at (output s):", [(round(a, 2), t) for a, b, _, t, _ in KW])
