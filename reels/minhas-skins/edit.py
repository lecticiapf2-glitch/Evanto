# Reels "Minhas skins": voice-over (ElevenLabs, voz clonada) over the Drive takes.
# Same visual language as the previous Reels: baby-yellow brush highlights on top, full captions
# at the bottom, synced SFX. New here: skin-select grid, split screen, picture-in-picture card.
# usage: python3 edit.py PROXY_DIR WORKDIR OUT.mp4   (env PREVIEW=t1,t2 renders stills at output times)
import json, os, re, subprocess, sys, wave
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

PX, WD, OUT = sys.argv[1:4]
FPS, OW, OH, SR = 30, 1080, 1920, 48000
LEAD = 0.30                 # silence before the voice starts
VO_LEN = 104.96
TAIL = 1.2
DUR = LEAD + VO_LEN + TAIL
FONT_KW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../amigo-secreto/fonts/kaushan-script-latin-400-normal.ttf")
FONT_SUB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
YELLOW = (244, 218, 146)
KW_Y, SUB_Y = 300, 1430

# ---------------- edit decision list (times = voice-over seconds) ----------------
# single clips: (start, end, take, src_in, focus_y)
CLIPS = [
    (-LEAD, 1.75, "0997", 0.6, .40),
    # 1.75-5.6 grid A
    (5.6, 8.5, "0973", 3.0, .45), (8.5, 10.6, "0975", 1.0, .45), (10.6, 12.2, "0996", 0.2, .50),
    (12.2, 13.6, "1004", 0.5, .50), (13.6, 15.2, "0985", 1.0, .50),
    # 15.2-18.6 split x3
    (18.6, 21.3, "1002", 3.0, .45), (21.3, 23.1, "1002", 13.0, .45), (23.1, 25.0, "1003", 4.0, .40),
    (25.0, 26.6, "1003", 18.0, .40), (26.6, 28.1, "1004", 2.0, .50),
    (28.1, 29.5, "0976", 2.8, .50), (29.5, 30.9, "0979", 1.0, .50), (30.9, 31.9, "0978", 0.2, .50),
    (31.9, 32.9, "0980", 0.0, .50), (32.9, 35.3, "0981", 8.0, .50),
    (35.3, 36.9, "0995", 2.0, .50), (36.9, 40.5, "0973", 3.6, .45), (40.5, 42.0, "0997", 2.5, .40),
    (42.0, 43.0, "0999", 0.2, .50), (43.0, 44.3, "1001", 0.0, .50), (44.3, 45.7, "0998", 0.5, .50),
    (45.7, 47.7, "0997", 8.0, .45), (47.7, 50.0, "0996", 4.0, .50),
    (50.0, 51.5, "0985", 4.0, .50), (51.5, 53.5, "0974", 5.0, .50), (53.5, 55.1, "0975", 3.0, .45),
    # 55.1-59.9 split x2
    (59.9, 62.9, "0984", 9.0, .45), (62.9, 64.0, "0990", 30.0, .40), (64.0, 65.1, "0988", 5.0, .40),
    (65.1, 66.3, "0990", 60.0, .40), (66.3, 67.2, "0986", 3.0, .35), (67.2, 68.4, "0986", 10.0, .35),
    (68.4, 70.4, "0989", 10.0, .50),
    (70.4, 72.0, "0990", 116.0, .30), (72.0, 74.6, "0986", 0.0, .35),
    # 74.6-76.9 grid B
    (76.9, 78.4, "0984", 20.0, .45),
    (78.4, 79.1, "1003", 9.0, .40), (79.1, 79.8, "0973", 5.0, .45), (79.8, 80.5, "0975", 14.0, .45),
    (80.5, 84.4, "0990", 115.5, .30), (84.4, 88.4, "0986", 18.0, .35),
    (88.4, 91.0, "0982", 3.0, .50), (91.0, 93.3, "0982", 5.4, .50), (93.3, 96.7, "0983", 0.0, .50),
    # 96.7-102.2 grid C (CTA)
    (102.2, VO_LEN + TAIL, "0989", 0.0, .50),
]
SKINS = [("1003", 4.0, "Mãe"), ("0981", 8.0, "Brasileira"), ("0973", 3.6, "Dona de casa"),
         ("0975", 12.0, "Home office"), ("0984", 22.0, "Empreendedora")]
GRIDS = [(1.75, 5.6, "intro"), (74.6, 76.9, "cinco"), (96.7, 102.2, "cta")]
SPLITS = [(15.2, 18.6, [("1003", 6.0, .40), ("0973", 4.5, .45), ("0975", 14.0, .45)], None),
          (44.3, 50.0, [("0998", 0.5, .50), ("0997", 8.0, .45), ("0996", 4.0, .50)], None),       # casa inteira
          (55.1, 59.9, [("0975", 12.0, .45), ("0973", 4.0, .45)], ["Home office", "Dona de casa"]),
          (65.1, 68.4, [("0988", 6.0, .35), ("0990", 30.0, .35), ("0986", 10.0, .30)], None),     # mensagem/ideia/ligação
          (78.4, 80.5, [("1003", 9.0, .40), ("0973", 5.0, .45), ("0975", 14.0, .45)], ["Mãe", "Dona de casa", "Home office"])]
# splits take precedence over CLIPS in frame_at(), so the clips listed under them are only fallbacks
PIP = (61.4, 65.1, [("1003", 18.0), ("0981", 8.5), ("0973", 4.5)])     # "enquanto isso" card

# top highlights: (start, end, text, sfx)
KEYWORDS = [
    (1.75, 5.5, "Quantas skins você usa por dia?", "whoosh"),
    (8.8, 10.5, "Ninguém vê a troca", None),
    (19.86, 28.0, "Skin nº 1: Mãe", "pop"),
    (29.3, 35.2, "Skin nº 2: Brasileira", "pop"),
    (36.5, 49.9, "Skin nº 3: Dona de casa", "pop"),
    (51.1, 54.9, "Skin nº 4: Home office", "pop"),
    (61.0, 70.3, "Skin nº 5: Empreendedora", "pop"),
    (72.0, 74.5, "“Você fica o dia todo em casa, né?”", None),
    (74.6, 76.8, "Fico. Com 5 de mim.", "whoosh"),
    (84.6, 88.3, "Não é multitarefa. É multiversão.", "shimmer"),
    (89.2, 92.1, "Uma skin só sua", None),
    (92.2, 96.6, "10 minutos. Café quente. Sentada.", None),
    (96.7, 102.1, "Quantas você usou hoje?", "whoosh"),
    (102.5, VO_LEN + TAIL, "Segue @lecticia.scott", "pen"),
]
CAPTION_FIX = {"à": "a", "que_56.04": "aqui"}

# ---------------- video readers ----------------
class Reader:
    def __init__(self, take, src_in, t0):
        self.cap = cv2.VideoCapture(f"{PX}/IMG_{take}.mp4")
        self.n = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.base = int(round(src_in * FPS)); self.t0 = t0
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.base)
        self.pos, self.frame = self.base - 1, None

    def get(self, t):
        want = min(self.base + int((t - self.t0) * FPS), self.n - 1)
        while self.pos < want:
            ok, f = self.cap.read()
            if not ok:
                break
            self.pos += 1; self.frame = f
        if self.frame is None:
            ok, self.frame = self.cap.read()
        return self.frame


readers = {}


def src(key, take, src_in, t0, t):
    if key not in readers:
        readers[key] = Reader(take, src_in, t0)
    return readers[key].get(t)


def cover(img, w, h, fy=.5, zoom=1.0):
    ih, iw = img.shape[:2]
    s = max(w / iw, h / ih) * zoom
    rw, rh = int(iw * s + .5), int(ih * s + .5)
    r = cv2.resize(img, (rw, rh), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR)
    x = (rw - w) // 2; y = int(np.clip(rh * fy - h / 2, 0, rh - h))
    return r[y:y + h, x:x + w]


def rounded_mask(w, h, r):
    m = np.zeros((h, w), np.uint8)
    cv2.rectangle(m, (r, 0), (w - r, h), 255, -1); cv2.rectangle(m, (0, r), (w, h - r), 255, -1)
    for cx, cy in ((r, r), (w - r, r), (r, h - r), (w - r, h - r)):
        cv2.circle(m, (cx, cy), r, 255, -1, cv2.LINE_AA)
    return m


def paste(o, tile, x, y, mask=None, border=0, alpha=1.0):
    h, w = tile.shape[:2]
    if border:
        bm = rounded_mask(w + 2 * border, h + 2 * border, 30 + border)
        roi = o[y - border:y + h + border, x - border:x + w + border].astype(np.float32)
        a = bm[..., None] / 255 * alpha
        o[y - border:y + h + border, x - border:x + w + border] = (roi * (1 - a) + np.array(YELLOW[::-1]) * a).astype(np.uint8)
    a = (mask[..., None] / 255 if mask is not None else 1) * alpha
    roi = o[y:y + h, x:x + w].astype(np.float32)
    o[y:y + h, x:x + w] = (roi * (1 - a) + tile * a).astype(np.uint8)


def ease(u):
    u = min(max(u, 0.0), 1.0); return 1 - (1 - u) ** 3


def back_out(u):
    u = min(max(u, 0), 1); c = 1.6
    return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2


# ---------------- text ----------------
def halo(img, layers):
    a = img.split()[-1]
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    for blur, k, col in layers:
        l = Image.new("RGBA", img.size, col + (255,))
        l.putalpha(a.filter(ImageFilter.GaussianBlur(blur)).point(lambda v, k=k: int(v * k)))
        out = Image.alpha_composite(out, l)
    return Image.alpha_composite(out, img)


def text_sprite(text, font, size, maxw, color, stroke=2, halo_layers=((10, .6, (45, 30, 20)), (2, .55, (45, 30, 20)))):
    f = ImageFont.truetype(font, size)
    while f.getlength(text) > maxw:
        size -= 2; f = ImageFont.truetype(font, size)
    pad = 40
    img = Image.new("RGBA", (int(f.getlength(text)) + 2 * pad, int(size * 1.45) + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((img.width / 2, pad + size), text, font=f, fill=color + (255,), anchor="ms",
                             stroke_width=stroke, stroke_fill=color + (255,) if stroke <= 2 else (0, 0, 0, 255))
    letters = np.array(img)[..., 3].copy()
    return np.array(halo(img, halo_layers)), letters, pad + size - img.height / 2 + 16, f.getlength(text)


def over(o, spr, cx, cy, scale=1.0, alpha=1.0):
    if scale != 1.0:
        spr = cv2.resize(spr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
    h, w = spr.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, OW), min(y0 + h, OH)
    s = spr[ya - y0:yb - y0, xa - x0:xb - x0].astype(np.float32)
    a = s[..., 3:4] / 255 * alpha
    o[ya:yb, xa:xb] = (o[ya:yb, xa:xb] * (1 - a) + s[..., 2::-1] * a).astype(np.uint8)


KW = [(a, b, text_sprite(t, FONT_KW, 92, 900, YELLOW), t, s) for a, b, t, s in KEYWORDS]
TILE_LABEL = {name: text_sprite(name, FONT_KW, 50, 300, YELLOW)[0] for *_, name in SKINS}
NUM_LABEL = {i: text_sprite(str(i), FONT_KW, 120, 200, YELLOW)[0] for i in range(1, 6)}
SPLIT_LABEL = {n: text_sprite(n, FONT_KW, 64, 600, YELLOW)[0] for n in ["Home office", "Dona de casa", "Mãe"]}
PIP_LABEL = text_sprite("enquanto isso…", FONT_KW, 46, 300, YELLOW)[0]
SIX = {"intro": "?", "cinco": "= 1 só", "cta": "e você?"}
SIX_LABEL = {k: text_sprite(v, FONT_KW, 80, 300, YELLOW)[0] for k, v in SIX.items()}


def draw_keywords(o, t):
    for a, b, (spr, letters, ul_dy, wm), text, sfx in KW:
        if not (a <= t <= b + 0.15):
            continue
        sc = 0.82 + 0.18 * back_out((t - a) / 0.16)
        al = min(1, (t - a) / 0.08) * (1 if t <= b else 1 - (t - b) / 0.15)
        s = spr
        if sfx == "shimmer" and 86.66 <= t <= 87.3:
            v = (t - 86.66) / 0.64
            hh, ww = letters.shape
            ys, xs = np.mgrid[0:hh, 0:ww].astype(np.float32)
            band = np.exp(-(((xs - (-80 + (ww + 160) * v)) + (ys - hh / 2) * 0.5) / 45) ** 2)
            ga = np.clip(cv2.GaussianBlur(letters.astype(np.float32), (0, 0), 10) * band * 1.4 / 255, 0, 1)[..., None]
            s = spr.copy(); a0 = s[..., 3:4].astype(np.float32) / 255; na = a0 + ga * (1 - a0)
            s[..., :3] = ((s[..., :3] * a0 + np.array([255, 246, 222], np.float32) * ga * (1 - a0)) / np.maximum(na, 1e-3)).astype(np.uint8)
            s[..., 3] = (na[..., 0] * 255).astype(np.uint8)
        over(o, s, OW / 2, KW_Y, sc, al)
        if sfx == "pen" and t >= a:
            pr = ease((t - a) / 0.35)
            y = int(KW_Y + ul_dy); x0 = int(OW / 2 - wm / 2); x1 = int(x0 + wm * pr)
            cv2.line(o, (x0, y + 3), (x1, y + 3), (20, 30, 45), 7, cv2.LINE_AA)
            cv2.line(o, (x0, y), (x1, y), YELLOW[::-1], 6, cv2.LINE_AA)


# ---------------- captions ----------------
def captions():
    ws = [w for w in json.load(open(f"{WD}/words.json"))["words"] if w.get("type", "word") == "word"]
    for w in ws:
        w["text"] = CAPTION_FIX.get(f'{w["text"]}_{w["start"]}', CAPTION_FIX.get(w["text"], w["text"]))
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
        res.append((s - 0.03, min(max(e + 0.12, s + 0.45), nxt),
                    text_sprite(text, FONT_SUB, 64, 900, (255, 255, 255), stroke=5, halo_layers=((8, .45, (0, 0, 0)),))[0]))
    return res


SUBS = captions()


def draw_subs(o, t):
    for a, b, spr in SUBS:
        if a <= t < b:
            over(o, spr, OW / 2, SUB_Y, 0.94 + 0.06 * ease((t - a) / 0.10), min(1, (t - a) / 0.06))
            break


# ---------------- layouts ----------------
TW, TH, GAP, GX, GY = 330, 470, 15, 30, 420
TILE_MASK = rounded_mask(TW, TH, 30)


def blurred_bg(t, take, src_in, t0):
    f = src(("bg", t0), take, src_in, t0, t)
    b = cv2.GaussianBlur(cover(f, OW // 4, OH // 4), (0, 0), 6)
    return (cv2.resize(b, (OW, OH)) * 0.45).astype(np.uint8)


def draw_grid(t, a, b, kind):
    o = blurred_bg(t, "0996", 0.2, a)
    for i in range(6):
        col, row = i % 3, i // 3
        x, y = GX + col * (TW + GAP), GY + row * (TH + GAP)
        delay = 0.12 * i if kind != "cta" else 0.08 * i
        u = (t - a - delay) / 0.22
        if u <= 0:
            continue
        al = ease(u)
        if i < 5:
            take, si, name = SKINS[i]
            tile = cover(src(("grid", a, i), take, si, a, t), TW, TH, .42)
            paste(o, tile, x, y, TILE_MASK, border=4, alpha=al)
            over(o, TILE_LABEL[name], x + TW / 2, y + TH - 48, 1.0, al)
            if kind == "cta":
                over(o, NUM_LABEL[i + 1], x + 60, y + 70, 0.8 + 0.2 * back_out(u), al)
        else:
            card = np.full((TH, TW, 3), (40, 30, 25), np.uint8)
            paste(o, card, x, y, TILE_MASK, border=4, alpha=al * 0.9)
            over(o, SIX_LABEL[kind], x + TW / 2, y + TH / 2, 0.8 + 0.2 * back_out(u), al)
    return o


def draw_split(t, a, b, parts, labels):
    o = np.zeros((OH, OW, 3), np.uint8)
    n = len(parts); h = OH // n
    for i, (take, si, fy) in enumerate(parts):
        u = ease((t - a - 0.1 * i) / 0.25)
        tile = cover(src(("split", a, i), take, si, a, t), OW, h, fy)
        dx = int((1 - u) * (OW if i % 2 == 0 else -OW))      # halves slide in from alternate sides
        xs, xe = max(0, dx), min(OW, OW + dx)
        if xe > xs:
            o[i * h:(i + 1) * h, xs:xe] = tile[:, xs - dx:xe - dx]
        if i:
            cv2.line(o, (0, i * h), (OW, i * h), YELLOW[::-1], 6)
        if labels and u > 0.5:
            over(o, SPLIT_LABEL[labels[i]], OW / 2, (520 if i == 0 else i * h + (30 if i == 2 else 70)), 1.0, ease((u - .5) * 2))
    return o


def draw_pip(o, t):
    a, b, parts = PIP
    if not (a <= t < b):
        return
    k = min(int((t - a) / ((b - a) / len(parts))), len(parts) - 1)
    take, si = parts[k]
    seg0 = a + k * (b - a) / len(parts)
    w, h = 300, 470
    u = ease((t - a) / 0.25) * (1 if t < b - 0.25 else ease((b - t) / 0.25))
    x = int(OW - 40 - w + (1 - u) * (w + 60)); y = 860
    tile = cover(src(("pip", seg0), take, si, seg0, t), w, h, .42)
    paste(o, tile, x, y, rounded_mask(w, h, 28), border=4)
    over(o, PIP_LABEL, x + w / 2, y - 40, 1.0, u)


def frame_at(t):
    for a, b, kind in GRIDS:
        if a <= t < b:
            return draw_grid(t, a, b, kind)
    for a, b, parts, labels in SPLITS:
        if a <= t < b:
            return draw_split(t, a, b, parts, labels)
    for k, (a, b, take, si, fy) in enumerate(CLIPS):
        if a <= t < b:
            z = (1.0 if k % 2 == 0 else 1.06) + 0.04 * (t - a) / max(b - a, 0.1)   # gentle push, alternating punch
            return cover(src(("clip", k), take, si, a, t), OW, OH, fy, z).copy()
    return np.zeros((OH, OW, 3), np.uint8)


# ---------------- audio ----------------
rng = np.random.default_rng(11)


def db(x): return 10 ** (x / 20)


def bandpass(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def norm(x, pk): return x / (np.abs(x).max() + 1e-9) * db(pk)


def whoosh():
    n = int(0.3 * SR); noise = rng.standard_normal(n); out = np.zeros(n); hop = 512
    for k in range(0, n, hop):
        fc = 600 * (3000 / 600) ** (k / n); seg = noise[max(0, k - hop):k + 2 * hop]
        y = bandpass(seg, fc * .6, fc * 1.6); out[k:k + hop] = y[min(k, hop):min(k, hop) + len(out[k:k + hop])]
    u = np.arange(n) / n
    return norm(out * np.where(u < .6, (u / .6) ** 2, ((1 - u) / .4) ** 1.5), -23)


def pop():
    tt = np.arange(int(0.09 * SR)) / SR; f = 900 * np.exp(-tt / 0.02) + 320
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.025), -23)


def tick():
    tt = np.arange(int(0.05 * SR)) / SR
    return norm(np.sin(2 * np.pi * 2100 * tt) * np.exp(-tt / 0.008), -30)


def shimmer(length=0.64):
    n = int(length * SR); out = np.zeros(n)
    for _ in range(26):
        st = rng.uniform(0, length * .85); f = rng.uniform(3200, 8200); tm = np.arange(int(.12 * SR)) / SR
        g = np.sin(2 * np.pi * f * tm) * np.exp(-tm / .03) * rng.uniform(.4, 1)
        s = int(st * SR); e = min(n, s + len(g)); out[s:e] += g[:e - s]
    return norm(out * np.sin(np.pi * np.arange(n) / n) ** .7, -26)


def pen(length=0.4):
    n = int(length * SR); tt = np.arange(n) / SR
    x = bandpass(rng.standard_normal(n), 2200, 7000) * (0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 38 * tt)))
    u = tt / length
    return norm(x * np.minimum(u / .08, 1) * (1 - u) ** .8, -28)


def read_wav(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2)


def build_audio():
    n = int(DUR * SR)
    mix = np.zeros((n, 2), np.float32)
    vo = read_wav(f"{WD}/vo.wav")
    s = int(LEAD * SR); mix[s:s + len(vo)] += vo[:n - s]

    def place(sig, t):
        sig = np.stack([sig, sig], 1) if sig.ndim == 1 else sig
        i = int(round((t + LEAD) * SR)); e = min(n, i + len(sig)); mix[i:e] += sig[:e - i]

    # natural sound of each single clip, well under the voice (coffee pour a bit louder)
    for a, b, take, si, fy in CLIPS:
        amb = read_wav(f"{PX}/../audio48/IMG_{take}.wav")
        seg = amb[int(si * SR):int((si + b - a) * SR)].copy()
        if len(seg) < 64:
            continue
        f = min(int(0.03 * SR), len(seg) // 2); r = np.linspace(0, 1, f)[:, None]
        seg[:f] *= r; seg[-f:] *= r[::-1]
        place(seg * db(-6 if take in ("0981", "0982") else -14), a)
    for a, b, text, sfx in KEYWORDS:
        if sfx == "pop": place(pop(), a)
        elif sfx == "whoosh": place(whoosh(), a - 0.18)
        elif sfx == "shimmer": place(shimmer(), 86.66)
        elif sfx == "pen": place(pen(), a)
    for a, b, kind in GRIDS:            # each tile landing
        for i in range(6):
            place(tick(), a + (0.12 if kind != "cta" else 0.08) * i + 0.05)
    for a, b, parts, labels in SPLITS:
        place(whoosh(), a - 0.12)
    place(pop(), PIP[0])
    tail = int(0.6 * SR); mix[-tail:] *= np.linspace(1, 0, tail)[:, None]
    with wave.open(f"{WD}/mix.wav", "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())


# ---------------- render ----------------
PREVIEW = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
if not PREVIEW:
    build_audio()
enc = None if PREVIEW else subprocess.Popen(
    ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
     "-i", f"{WD}/mix.wav", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
     "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
     "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
frames = [int(round((p + LEAD) * FPS)) for p in PREVIEW] if PREVIEW else range(int(DUR * FPS))
for fi in frames:
    t = fi / FPS - LEAD
    if PREVIEW:
        readers.clear()
    o = frame_at(t)
    draw_pip(o, t)
    draw_keywords(o, t)
    draw_subs(o, t)
    if t > VO_LEN + TAIL - 0.5:
        o = (o * max((VO_LEN + TAIL - t) / 0.5, 0)).astype(np.uint8)
    if PREVIEW:
        cv2.imwrite(f"{OUT}_{t:06.2f}.jpg", o)
    else:
        enc.stdin.write(o.tobytes())
if enc:
    enc.stdin.close(); enc.wait()
print("done", len(frames), "frames")
