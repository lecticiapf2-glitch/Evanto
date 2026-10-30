# Edit decision list (source times, seconds). Shared by render.py and sfx.py.
FPS = 30
DUR = 79.266

# Punch-in scale per segment. Segments start at the source's own jump cuts,
# so scale changes land on existing cuts (jump cut / punch-in, no sound).
# ("hold", start, end, z) | ("push", start, end, z0, z1) | ("snap", start, end, z_from, z_to)
ZOOM = [
    ("hold", 0.00, 1.63, 1.00),
    ("hold", 1.63, 5.23, 1.08),
    ("hold", 5.23, 8.67, 1.00),
    ("hold", 8.67, 10.73, 1.05),
    ("snap", 10.73, 12.53, 1.05, 1.18),   # reaction "A FAMILIA FICOU" -> short whoosh
    ("push", 12.53, 22.43, 1.00, 1.06),
    ("snap", 22.43, 22.97, 1.06, 1.16),   # "E AGORA?" -> soft tick
    ("hold", 22.97, 26.03, 1.00),
    ("hold", 26.03, 27.27, 1.08),
    ("push", 27.27, 37.13, 1.00, 1.06),
    ("hold", 37.13, 42.27, 1.00),         # shine sweep on "O NATAL TA CHEGANDO"
    ("hold", 42.27, 48.10, 1.08),
    ("hold", 48.10, 49.17, 1.00),
    ("push", 49.17, 53.37, 1.00, 1.05),
    ("hold", 53.37, 55.30, 1.00),
    ("snap", 55.30, 56.57, 1.00, 1.16),   # "ERREI, FUI BABACA" -> short whoosh
    ("hold", 56.57, 59.53, 1.00),
    ("push", 59.53, 70.67, 1.00, 1.07),
    ("hold", 70.67, 72.10, 1.08),
    ("hold", 72.10, 74.87, 1.00),         # underline on "SEGUE @lecticia.scott"
    ("hold", 74.87, 99.00, 1.05),
]
SNAP_LEN = 0.10      # snap zoom ease duration
ANCHOR_Y = 0.55      # zoom anchor: keeps face in upper third and captions above the Reels UI

# Typewriter title "Amigo secreto": frames where new letters appear (measured)
TYPE_TIMES = [0.167, 0.267, 0.400, 0.500, 0.600, 0.833, 0.933, 1.033, 1.133, 1.267, 1.433]

SHINE = dict(t0=37.33, t1=37.93, box=(115, 734, 460, 767))   # source px
UNDERLINE = dict(t0=73.15, t1=73.50, off=75.30, x0=136, x1=441, y=774)
FADE_OUT = 0.5
