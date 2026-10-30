import subprocess, sys, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, sys.argv[3])
from plan_v2 import *
from clean import text_bbox, fill
from captions import chunks
from render import zoom_at, ease   # same zoom schedule as v1

SRC, OUT, WORDS = sys.argv[1], sys.argv[2], sys.argv[4]
W, H = 576, 1024
OW, OH = 1080, 1920
BASE = OW / W
N = int(DUR * FPS)


def decode(start=0):
    return subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(start), "-i", SRC, "-f", "rawvideo",
                             "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)


def read(p):
    b = p.stdout.read(W * H * 3)
    return None if len(b) < W * H * 3 else np.frombuffer(b, np.uint8).reshape(H, W, 3).copy()


# ---------- pass 1: label boxes and clean reference frames ----------
need = {}
for a, b in OLD_LABELS:
    need[a - LABEL_MARGIN - REF_GAP] = None
    need[b + LABEL_MARGIN + REF_GAP] = None
boxes = [[] for _ in OLD_LABELS]
p = decode(); i = 0
while True:
    f = read(p)
    if f is None:
        break
    if i in need:
        need[i] = f
    for k, (a, b) in enumerate(OLD_LABELS):
        if a <= i <= b:
            bb = text_bbox(f)
            if bb:
                boxes[k].append(bb)
    i += 1
# median per label (hands crossing the label would inflate a union), plus a small margin
boxes = [tuple(int(v) for v in np.median(np.array(b), 0) + np.array([-3, -2, 3, 2])) for b in boxes]
print("boxes", boxes)


def clean_frame(f, i):
    for k, (a, b) in enumerate(OLD_LABELS):
        if a - LABEL_MARGIN <= i <= b + LABEL_MARGIN:
            before = need[a - LABEL_MARGIN - REF_GAP]
            after = need[b + LABEL_MARGIN + REF_GAP]
            ref = before if i < (a + b) / 2 else after
            return fill(f, ref, boxes[k])
    return f


# ---------- text sprites ----------
def shadowed(img_text, blur, alpha):
    a = img_text.split()[-1]
    sh = Image.new("RGBA", img_text.size, (0, 0, 0, 0))
    sh.putalpha(a.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * alpha)))
    return Image.alpha_composite(sh, img_text)


def keyword_sprite(text):
    size = 96
    while True:
        font = ImageFont.truetype(KW_FONT, size)
        lines = [text]
        if font.getlength(text) > KW_MAXW and " " in text and size <= 84:
            words = text.split(); best = None
            for j in range(1, len(words)):           # split near the middle
                l1, l2 = " ".join(words[:j]), " ".join(words[j:])
                wmax = max(font.getlength(l1), font.getlength(l2))
                best = min(best, (wmax, [l1, l2])) if best else (wmax, [l1, l2])
            lines = best[1]
        if max(font.getlength(l) for l in lines) <= KW_MAXW or size <= 60:
            break
        size -= 4
    lh = int(size * 1.05)
    pad = 40
    wpx = int(max(font.getlength(l) for l in lines)) + 2 * pad
    img = Image.new("RGBA", (wpx, lh * len(lines) + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for j, l in enumerate(lines):
        d.text((wpx / 2, pad + lh * j + lh / 2), l, font=font, fill=(255, 255, 255, 255), anchor="mm")
    letters = np.array(img)[..., 3].copy()
    return np.array(shadowed(img, 12, 0.75)), letters, pad, lh, lines, font


def sub_sprite(text):
    font = ImageFont.truetype(SUB_FONT, SUB_SIZE)
    while font.getlength(text) > SUB_MAXW:
        font = ImageFont.truetype(SUB_FONT, font.size - 2)
    pad = 30
    wpx = int(font.getlength(text)) + 2 * pad
    img = Image.new("RGBA", (wpx, int(SUB_SIZE * 1.3) + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((wpx / 2, img.height / 2), text, font=font, fill=(255, 255, 255, 255),
                             anchor="mm", stroke_width=5, stroke_fill=(0, 0, 0, 255))
    return np.array(shadowed(img, 8, 0.45))


def over(o, spr, cx, cy, scale=1.0, alpha=1.0):
    if scale != 1.0:
        spr = cv2.resize(spr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
    h, w = spr.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, OW), min(y0 + h, OH)
    s = spr[ya - y0:yb - y0, xa - x0:xb - x0].astype(np.float32)
    a = s[..., 3:4] / 255 * alpha
    rgb = s[..., 2::-1]                        # RGBA -> BGR
    roi = o[ya:yb, xa:xb].astype(np.float32)
    o[ya:yb, xa:xb] = (roi * (1 - a) + rgb * a).astype(np.uint8)


def back_out(u):                               # ease-out with a small overshoot (pop)
    u = min(max(u, 0), 1); c = 1.6
    return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2


KW = [(a, b, keyword_sprite(t), t) for a, b, t in KEYWORDS]
SUBS = [(a, b, sub_sprite(t)) for a, b, t in chunks(WORDS)]


def draw_keywords(o, t):
    for a, b, (spr, letters, pad, lh, lines, font), text in KW:
        if not (a <= t <= b + 0.15):
            continue
        u = (t - a) / 0.16
        sc = 0.82 + 0.18 * back_out(u)
        al = min(1, (t - a) / 0.08) * (1 if t <= b else 1 - (t - b) / 0.15)
        s = spr.copy()
        if text.startswith("O NATAL") and SHINE["t0"] <= t <= SHINE["t1"]:
            v = (t - SHINE["t0"]) / (SHINE["t1"] - SHINE["t0"])
            hh, ww = letters.shape
            ys, xs = np.mgrid[0:hh, 0:ww].astype(np.float32)
            band = np.exp(-(((xs - (-80 + (ww + 160) * v)) + (ys - hh / 2) * 0.5) / 45) ** 2)
            glow = cv2.GaussianBlur(letters.astype(np.float32), (0, 0), 10) * band * 1.4
            gold = np.array([255, 236, 190], np.float32)
            a0 = s[..., 3:4].astype(np.float32) / 255
            ga = np.clip(glow / 255, 0, 1)[..., None]
            na = a0 + ga * (1 - a0)
            s[..., :3] = ((s[..., :3] * a0 + gold * ga * (1 - a0)) / np.maximum(na, 1e-3)).astype(np.uint8)
            s[..., 3] = (na[..., 0] * 255).astype(np.uint8)
        over(o, s, OW / 2, KW_Y, sc, al)
        if text.startswith("SEGUE"):
            U = UNDERLINE
            pr = ease((t - U["t0"]) / (U["t1"] - U["t0"])) if t >= U["t0"] else 0
            if pr > 0:
                half = max(font.getlength(l) for l in lines) / 2
                y = int(KW_Y + (spr.shape[0] / 2 - pad) + 14)
                x0, x1 = int(OW / 2 - half), int(OW / 2 - half + 2 * half * pr)
                layer = o.copy()
                cv2.line(layer, (x0, y + 3), (x1, y + 3), (0, 0, 0), 8, cv2.LINE_AA)
                cv2.line(layer, (x0, y), (x1, y), (255, 255, 255), 7, cv2.LINE_AA)
                cv2.addWeighted(layer, al, o, 1 - al, 0, dst=o)


def draw_subs(o, t):
    for a, b, spr in SUBS:
        if a <= t < b:
            sc = 0.94 + 0.06 * ease((t - a) / 0.10)
            over(o, spr, OW / 2, SUB_Y, sc, min(1, (t - a) / 0.06))
            break


# ---------- pass 2: render ----------
import os
PREVIEW = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
p = decode()
enc = subprocess.Popen(["cat"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL) if os.environ.get("PREVIEW") else subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                        "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", OUT],
                       stdin=subprocess.PIPE)
i = 0
while True:
    f = read(p)
    if f is None:
        break
    t = i / FPS
    f = clean_frame(f, i)
    s = BASE * zoom_at(t)
    M = np.array([[s, 0, OW / 2 - W / 2 * s], [0, s, OH * ANCHOR_Y - H * ANCHOR_Y * s]], np.float32)
    o = cv2.warpAffine(f, M, (OW, OH), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
    draw_keywords(o, t)
    draw_subs(o, t)
    rem = DUR - t
    if rem < FADE_OUT:
        o = (o.astype(np.float32) * max(rem / FADE_OUT, 0)).astype(np.uint8)
    if PREVIEW:
        if any(abs(t - x) < 0.5 / FPS for x in PREVIEW):
            cv2.imwrite(f"{OUT}_{t:.2f}.jpg", o)
        if t > max(PREVIEW):
            break
    else:
        enc.stdin.write(o.tobytes())
    i += 1
enc.stdin.close(); enc.wait()
print("frames", i)
