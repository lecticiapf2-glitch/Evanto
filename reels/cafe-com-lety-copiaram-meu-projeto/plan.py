# Reels "Café com Lety - copiaram meu projeto": edit decisions. Times are SOURCE seconds.
FPS = 30
START, END = 1.20, 142.90

# Pause trimming (jump cuts, no SFX): gaps longer than MAX_GAP keep only HEAD after the word and TAIL before the next.
MAX_GAP, HEAD, TAIL = 0.80, 0.30, 0.25
KEEP_GAPS = {64.12: (0.95, 0.95),      # sip of coffee after "fazendo o quê?" - comic beat
             82.86: (0.60, 0.40),      # reaction after "desse projeto"
             112.18: (0.50, 0.30)}     # let the punchline land

ANCHOR_Y = 0.33                         # zoom around the face
ZOOM_ALT = (1.00, 1.08)                 # alternated on each jump cut (punch-in, no sound)

# Snap punch-ins with a short whoosh, on reactions (source time, scale, hold until)
SNAPS = [(11.14, 1.16, 12.4),           # "antes de mim"
         (110.88, 1.16, 112.6)]         # "quem eu sou"

# Top highlights: (on, off, text, sfx)  sfx in {None, "shimmer", "tick", "pop", "pen"}
KEYWORDS = [
    (9.96, 12.40, "Lançar antes de mim", None),        # snap whoosh already marks it
    (20.70, 22.40, "Café com Lety", "shimmer"),
    (25.72, 27.85, "Consultoria grátis", "tick"),
    (43.34, 45.90, "Boca de sacola", "pop"),
    (53.46, 55.10, "Reunião de planejamento", None),
    (68.44, 70.70, "Exatamente aquilo", None),
    (98.50, 100.70, "Só depois que estão prontos", None),
    (103.52, 106.80, "Podem até copiar", None),
    (108.08, 112.60, "Ninguém copia quem eu sou", None),  # snap whoosh at "quem eu sou"
    (115.56, 117.40, "Já se inspiraram em você?", "tick"),
    (133.72, 137.80, "Segue @lecticia.scott", "pen"),
]
SHINE_LEN = 0.60
UNDERLINE_LEN = 0.35

KW_FONT = "/tmp/claude-0/-home-user-Evanto/d9ba71db-c518-54e1-b3fb-f47227593385/scratchpad/fonts/kaushan-script-latin-400-normal.ttf"
KW_Y, KW_SIZE, KW_MAXW = 300, 96, 860
KW_COLOR = (244, 218, 146)              # baby yellow, almost beige
SUB_FONT = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
SUB_SIZE, SUB_Y, SUB_MAXW = 64, 1430, 900
FADE_OUT = 0.5

# Caption clean-up
DROP_AT = set()
REPLACE = {"maravideva.": "maravidiva.", "Ééé,": "Éé,"}
