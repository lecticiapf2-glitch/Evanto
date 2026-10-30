# Removes burned-in caption boxes by filling them from the nearest clean frame,
# motion-compensated with optical flow and blended seamlessly.
import numpy as np, cv2
BAND = (715, 800, 60, 516)          # y0,y1,x0,x1 (source px) where the old captions live
PADX, PADT, PADB = 11, 12, 16


def text_bbox(f):
    y0, y1, x0, x1 = BAND
    g = cv2.cvtColor(f[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
    ys, xs = np.nonzero(g > 200)
    if len(xs) < 120:
        return None
    return xs.min() + x0 - PADX, ys.min() + y0 - PADT, xs.max() + x0 + PADX, ys.max() + y0 + PADB


def fill(cur, ref, box):
    bx0, by0, bx1, by1 = box
    m = 60
    X0, Y0, X1, Y1 = max(bx0 - m, 0), max(by0 - m, 0), min(bx1 + m, cur.shape[1]), min(by1 + m, cur.shape[0])
    c = cv2.cvtColor(cur[Y0:Y1, X0:X1], cv2.COLOR_BGR2GRAY)
    r = cv2.cvtColor(ref[Y0:Y1, X0:X1], cv2.COLOR_BGR2GRAY)
    flow = cv2.calcOpticalFlowFarneback(c, r, None, 0.5, 3, 25, 3, 7, 1.5, 0)
    hole = np.zeros(c.shape, np.uint8)
    hole[by0 - Y0 - 4:by1 - Y0 + 4, bx0 - X0 - 4:bx1 - X0 + 4] = 1
    for k in range(2):                       # flow inside the box is unreliable: rebuild it from the ring
        ch = flow[..., k]
        lo, hi = ch.min(), ch.max()
        u8 = ((ch - lo) / (hi - lo + 1e-6) * 255).astype(np.uint8)
        u8 = cv2.inpaint(u8, hole, 9, cv2.INPAINT_TELEA)
        flow[..., k] = u8.astype(np.float32) / 255 * (hi - lo) + lo
    gx, gy = np.meshgrid(np.arange(X1 - X0, dtype=np.float32), np.arange(Y1 - Y0, dtype=np.float32))
    warped = cv2.remap(ref[Y0:Y1, X0:X1], gx + flow[..., 0], gy + flow[..., 1], cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_REFLECT)
    patch = warped[by0 - Y0 - 3:by1 - Y0 + 3, bx0 - X0 - 3:bx1 - X0 + 3]
    mask = np.full(patch.shape[:2], 255, np.uint8)
    center = ((bx0 + bx1) // 2, (by0 + by1) // 2)
    try:
        return cv2.seamlessClone(patch, cur, mask, center, cv2.NORMAL_CLONE)
    except cv2.error:
        out = cur.copy(); out[by0 - 3:by1 + 3, bx0 - 3:bx1 + 3] = patch
        return out
