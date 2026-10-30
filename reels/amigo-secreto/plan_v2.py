# Version 2: keywords move to the top (no box), full Reels captions at the bottom.
from plan import *

# Highlighted words: (on, off, text). "on" = frame the old label appeared, so the SFX from v1 still land.
KEYWORDS = [
    (11.03, 13.97, "A FAMÍLIA FICOU"),
    (22.43, 23.40, "E AGORA?"),
    (37.30, 38.60, "O NATAL TÁ CHEGANDO"),
    (39.70, 42.20, "AMIGO SECRETO"),
    (43.10, 45.43, "PRESENTE DE NATAL"),
    (51.17, 53.27, "FAZER AS PAZES"),
    (55.30, 56.60, "ERREI, FUI BABACA"),
    (62.47, 66.30, "FESTAS EM FAMÍLIA"),
    (73.10, 75.30, "SEGUE @lecticia.scott"),
]
KW_FONT = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
KW_Y = 330            # centre of the keyword block (output px, 1080x1920) - below the Reels top bar
KW_MAXW = 940

SUB_FONT = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
SUB_SIZE = 64
SUB_Y = 1430          # centre of the caption line - above the Reels bottom UI
SUB_MAXW = 900

# Old burned-in labels, in source frames (fade included). Filled from clean neighbour frames.
OLD_LABELS = [(328, 420), (671, 690), (1118, 1141), (1190, 1267), (1293, 1363),
              (1534, 1599), (1658, 1698), (1873, 1991), (2193, 2260)]
LABEL_MARGIN = 3      # extra frames for the fade in/out
REF_GAP = 6           # distance of the clean reference frame from the label

# Word fixes for captions (transcription quirks / false starts)
DROP = {"polica-", "fi--"}
DROP_AT = {28.80, 29.34, 44.84, 53.42, 53.66}     # false starts: "relatar, ou", "de", "com as"
REPLACE = {"blá-blá-blá-blá-blá-blá-blá-blá.": "blá-blá-blá-blá."}

# Version 3: script pairing for the top words (lead in Mr De Haviland, key word in a bold brush script)
KEYWORDS_V3 = [("só que a", "Família ficou"), ("e", "Agora?"), ("o Natal tá", "Chegando"), ("época de", "Amigo secreto"),
               ("presente de", "Natal"), ("fazer as", "Pazes"), ("errei,", "Fui babaca"), ("festas em", "Família"),
               ("segue", "@lecticia.scott")]
LEAD_FONT = __import__("os").path.dirname(__file__) + "/fonts/mr-de-haviland-latin-400-normal.ttf"
MAIN_FONT = __import__("os").path.dirname(__file__) + "/fonts/kaushan-script-latin-400-normal.ttf"
KW3_Y = 440
