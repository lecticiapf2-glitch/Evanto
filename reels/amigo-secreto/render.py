import subprocess, sys, numpy as np, cv2
sys.path.insert(0, sys.argv[3])
from plan import *

SRC, OUT = sys.argv[1], sys.argv[2]
W, H = 576, 1024
OW, OH = 1080, 1920
BASE = OW / W


def ease(u):
    u = min(max(u, 0.0), 1.0)
    return 1 - (1 - u) ** 3


def zoom_at(t):
    for seg in ZOOM:
        kind, a, b = seg[:3]
        if a <= t < b:
            if kind == "hold":
                return seg[3]
            if kind == "push":
                u = (t - a) / (b - a)
                return seg[3] + (seg[4] - seg[3]) * (u * u * (3 - 2 * u))
            if kind == "snap":
                return seg[3] + (seg[4] - seg[3]) * ease((t - a) / SNAP_LEN)
    return 1.0


def shine(f, t):
    if not (SHINE["t0"] <= t <= SHINE["t1"]):
        return f
    x0, y0, x1, y1 = SHINE["box"]
    u = (t - SHINE["t0"]) / (SHINE["t1"] - SHINE["t0"])
    cx = x0 - 40 + (x1 - x0 + 80) * u
    ys, xs = np.mgrid[y0 - 6:y1 + 7, x0 - 10:x1 + 11].astype(np.float32)
    d = (xs - cx) + (ys - (y0 + y1) / 2) * 0.6           # diagonal band
    a = np.exp(-(d / 14.0) ** 2) * 0.55 * np.sin(np.pi * u) ** 0.5
    roi = f[y0 - 6:y1 + 7, x0 - 10:x1 + 11].astype(np.float32)
    roi += (255 - roi) * a[..., None]
    f[y0 - 6:y1 + 7, x0 - 10:x1 + 11] = roi.astype(np.uint8)
    return f


def underline(o, t, M):
    U = UNDERLINE
    if not (U["t0"] <= t <= U["off"] + 0.2):
        return o
    p = ease((t - U["t0"]) / (U["t1"] - U["t0"]))
    alpha = 1.0 if t <= U["off"] else 1 - (t - U["off"]) / 0.2
    xe = U["x0"] + (U["x1"] - U["x0"]) * p
    pts = np.array([[U["x0"], U["y"], 1], [xe, U["y"], 1]], np.float32) @ M.T
    layer = o.copy()
    s = 16  # subpixel precision
    p1 = tuple(int(v * s) for v in pts[0]); p2 = tuple(int(v * s) for v in pts[1])
    cv2.line(layer, p1, p2, (255, 255, 255), 5, cv2.LINE_AA, shift=4)
    return cv2.addWeighted(layer, 0.9 * alpha, o, 1 - 0.9 * alpha, 0)


dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                       stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                        "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", OUT],
                       stdin=subprocess.PIPE)
n_total = int(DUR * FPS)
i = 0
while True:
    b = dec.stdout.read(W * H * 3)
    if len(b) < W * H * 3:
        break
    t = i / FPS
    f = np.frombuffer(b, np.uint8).reshape(H, W, 3).copy()
    f = shine(f, t)
    z = zoom_at(t)
    s = BASE * z
    ax, ay = W / 2, H * ANCHOR_Y
    M = np.array([[s, 0, OW / 2 - ax * s], [0, s, OH * ANCHOR_Y - ay * s]], np.float32)
    o = cv2.warpAffine(f, M, (OW, OH), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
    o = underline(o, t, M)
    rem = DUR - t
    if rem < FADE_OUT:
        o = (o.astype(np.float32) * max(rem / FADE_OUT, 0)).astype(np.uint8)
    enc.stdin.write(o.tobytes())
    i += 1
enc.stdin.close(); enc.wait()
print("frames", i)
